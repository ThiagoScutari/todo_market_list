import os
import re
import json
import datetime
import logging
import traceback
import requests
import random
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, event
from dateutil import parser 
from werkzeug.security import check_password_hash

# Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = datetime.timedelta(days=30)
app.secret_key = os.getenv("SECRET_KEY", "segredo")

# --- CONEXÃO BANCO (Postgres) ---
database_url = os.getenv('DATABASE_URL')
if not database_url:
    # Fallback local apenas para segurança, mas deve usar o .env
    db_path = os.path.join(os.path.dirname(base_dir), 'data', 'familyos.db')
    database_url = f'sqlite:///{db_path}'

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# --- MODELS (Tabelas) ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    def check_password(self, password):
        if self.password_hash in ['2904', '1712']: return self.password_hash == password
        return check_password_hash(self.password_hash, password)

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)

class UnidadeMedida(db.Model):
    __tablename__ = 'unidades_medida'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(20), unique=True, nullable=False)
    simbolo = db.Column(db.String(5), unique=True, nullable=False)

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    emoji = db.Column(db.String(10), nullable=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    unidade_padrao_id = db.Column(db.Integer, db.ForeignKey('unidades_medida.id'))
    categoria = db.relationship('Categoria', backref='produtos')
    unidade_padrao = db.relationship('UnidadeMedida', backref='produtos')

class ListaItem(db.Model):
    __tablename__ = 'lista_itens'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    quantidade = db.Column(db.Float, nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades_medida.id'))
    usuario = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pendente')
    adicionado_em = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    origem_input = db.Column(db.String(100))
    produto = db.relationship('Produto', backref='itens_lista')
    unidade = db.relationship('UnidadeMedida')

# --- NOVOS MODELS V2.0 ---

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    responsavel = db.Column(db.String(50)) # Thiago, Debora, Casal
    prioridade = db.Column(db.Integer, default=1) # 1=Baixa, 2=Media, 3=Alta
    status = db.Column(db.String(20), default='pendente')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class WeatherCache(db.Model):
    __tablename__ = 'weather_cache'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(50))
    data_json = db.Column(db.Text) # JSON string da API externa
    last_updated = db.Column(db.DateTime)

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True) # ID do Google para não duplicar
    calendar_id = db.Column(db.String(100), nullable=True) # <--- NOVO: Adicione esta linha
    parent_id = db.Column(db.String(100), nullable=True) # Para saber se é subtarefa
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, nullable=True) # Pode vir vazio
    due_date = db.Column(db.DateTime, nullable=True) # Pode não ter data
    status = db.Column(db.String(20)) # 'needsAction' ou 'completed'
    usuario = db.Column(db.String(50)) # Vamos receber do n8n
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# --- FUNÇÕES AUXILIARES (HELPER FUNCTIONS) ---

def get_weather_data():
    """
    Busca dados de clima com Cache no Banco de Dados (TTL 60 min).
    """
    cidade = "Itajai,SC" # Ajuste se necessário
    agora = datetime.datetime.utcnow()

    # 1. Tenta buscar no Cache
    cache = WeatherCache.query.first()

    # Verifica se o cache é válido (menos de 60 minutos)
    if cache and cache.last_updated and (agora - cache.last_updated).total_seconds() < 3600:
        logger.info("Usando Clima do Cache Local")
        try:
            return json.loads(cache.data_json)
        except:
            pass # Se der erro no JSON, busca de novo

    # 2. Se não tiver cache ou expirou, busca na API
    logger.info("Buscando Clima na API HG Brasil...")
    chave = os.getenv('HGBRASIL_KEY')
    if not chave:
        return None # Sem chave configurada

    try:
        url = f"https://api.hgbrasil.com/weather?key={chave}&city_name={cidade}"
        response = requests.get(url)
        dados = response.json()

        # Salva no Banco
        if not cache:
            cache = WeatherCache(city=cidade)
            db.session.add(cache)

        cache.data_json = json.dumps(dados)
        cache.last_updated = agora
        db.session.commit()

        return dados
    except Exception as e:
        logger.error(f"Erro API Clima: {e}")
        return None

def get_daily_quote():
    """Retorna uma frase inspiracional aleatória."""
    frases = [
        "O sucesso é a soma de pequenos esforços repetidos dia após dia.",
        "A organização é a chave para a liberdade.",
        "Não deixe para amanhã o que você pode automatizar hoje.",
        "Sua casa, suas regras, seu sistema.",
        "A disciplina é a ponte entre metas e realizações.",
        "Simplifique. Foque no que importa.",
        "Toda grande caminhada começa com um simples passo.",
        "Fé na vida, fé no homem, fé no que virá."
    ]
    return random.choice(frases)


@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

# --- ROTAS DE NAVEGAÇÃO (VIEWS) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, manda para o dashboard
    if current_user.is_authenticated: 
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        
        # Busca o usuário no banco (case insensitive para evitar erros de digitação)
        user = User.query.filter(User.username.ilike(u.strip())).first()
        
        # --- VERIFICAÇÃO DE SEGURANÇA ---
        # 1. Verifica se o usuário existe
        # 2. Compara a senha digitada (p) com o Hash salvo no banco (user.password_hash)
        if user and check_password_hash(user.password_hash, p):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        
        # Se falhar
        flash('Usuário ou senha incorretos', 'error')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    # 1. Contadores (Badges)
    qtd_compras = ListaItem.query.filter_by(status='pendente').count()
    qtd_tarefas = Task.query.filter_by(status='pendente').count()
    # NOVO: Conta lembretes do Google (needsAction = pendente)
    qtd_lembretes = Reminder.query.filter_by(status='needsAction').count()

    # 2. Clima Real
    weather_data = get_weather_data()
    clima = {"temp": "--", "desc": "Indisponível", "img_id": "32", "city": "Itajaí"}
    forecast = []

    if weather_data and 'results' in weather_data:
        res = weather_data['results']
        clima = {
            "temp": res.get('temp'),
            "desc": res.get('description'),
            "img_id": res.get('img_id'),
            "city": res.get('city'),
            "time": res.get('time')
        }
        forecast = res.get('forecast', [])[:3]

    # 3. Mensagem do Dia
    mensagem = get_daily_quote()

    return render_template('dashboard.html',
                           active_page='dashboard',
                           qtd_compras=qtd_compras,
                           qtd_tarefas=qtd_tarefas,
                           qtd_lembretes=qtd_lembretes, # Passando a nova variável
                           clima=clima,
                           forecast=forecast,
                           mensagem=mensagem)

@app.route('/shopping')
@login_required
def shopping_list():
    itens = ListaItem.query.options(joinedload(ListaItem.produto).joinedload(Produto.categoria), joinedload(ListaItem.unidade)).filter(or_(ListaItem.status == 'pendente', ListaItem.status == 'comprado')).order_by(ListaItem.adicionado_em.desc()).all()
    view = {}
    for i in itens:
        c = i.produto.categoria.nome if i.produto.categoria else "OUTROS"
        if c not in view: view[c] = []
        qtd = int(i.quantidade) if i.quantidade % 1 == 0 else i.quantidade
        und = i.unidade.simbolo if i.unidade else ""
        view[c].append({'id': i.id, 'nome': i.produto.nome.title(), 'emoji': i.produto.emoji, 'detalhes': f"{qtd}{und}", 'usuario': i.usuario, 'status': i.status})
    return render_template('shopping.html', categorias=view, active_page='shopping')

@app.route('/tasks')
@login_required
def task_board():
    # ALTERAÇÃO: Busca pendentes E concluidas (para não sumir da tela)
    tasks = Task.query.filter(or_(Task.status=='pendente', Task.status=='concluido')).order_by(Task.prioridade.desc(), Task.created_at.asc()).all()

    view = {'Thiago': [], 'Debora': [], 'Casal': []}
    for t in tasks:
        resp = t.responsavel if t.responsavel in view else 'Thiago'
        view[resp].append(t)
    return render_template('tasks.html', tasks=view, active_page='tasks')

@app.route('/clear_tasks', methods=['POST'])
@login_required
def clear_tasks():
    # Nova rota para arquivar tarefas feitas
    db.session.query(Task).filter(Task.status=='concluido').update({'status': 'arquivado'})
    db.session.commit()
    return jsonify({'status': 'success'})

# --- API ENDPOINTS (MERCADO) ---
@app.route('/toggle_item/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    i = db.session.get(ListaItem, id)
    if i:
        i.status = 'comprado' if i.status == 'pendente' else 'pendente'
        db.session.commit()
        return jsonify({'status': 'success', 'novo_status': i.status})
    return jsonify({'status': 'error'}), 404

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear():
    db.session.query(ListaItem).filter(ListaItem.status=='comprado').update({'status': 'finalizado'})
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/update_item', methods=['POST'])
@login_required
def update():
    d = request.get_json()
    i = db.session.get(ListaItem, int(d.get('id')))
    if not i: return jsonify({'error': '404'}), 404
    cat_nome = d.get('categoria').upper().strip()
    prod_nome = d.get('nome').lower().strip()
    cat = Categoria.query.filter_by(nome=cat_nome).first()
    if not cat: cat = Categoria(nome=cat_nome); db.session.add(cat); db.session.flush()
    prod = Produto.query.filter_by(nome=prod_nome).first()
    if not prod:
        prod = Produto(nome=prod_nome, categoria_id=cat.id, emoji=i.produto.emoji, unidade_padrao_id=i.produto.unidade_padrao_id)
        db.session.add(prod); db.session.flush()
    else: prod.categoria_id = cat.id
    i.produto_id = prod.id
    db.session.commit()
    return jsonify({'message': 'OK'})

@app.route('/magic', methods=['POST'])
def magic():
    # --- MODELO GEMINI PRO ---
    try:
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", # correção comma
            temperature=0.0,
            max_retries=1,
            timeout=10
            )
        chain = ChatPromptTemplate.from_template("JSON Lista (nome, quantidade, unidade, categoria, emoji) do texto: {texto}") | model
    except Exception as e:
        logger.error(f"Erro Config IA: {e}")
        return jsonify({'erro': str(e)}), 503

    d = request.get_json()
    if not d or 'texto' not in d: return jsonify({'erro': 'JSON invalido'}), 400

    try:
        logger.info(f"Texto: {d.get('texto')}")
        res = chain.invoke({"texto": d.get('texto')})
        content = res.content
        logger.info(f"Raw IA: {content}")

        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx+1]
            dados = json.loads(json_str)
        else:
            clean = re.sub(r'```json|```', '', content).strip()
            dados = json.loads(clean)

        if isinstance(dados, dict): dados = [dados]

        itens_salvos = []
        itens_ignorados = []

        for x in dados:
            n = x.get('nome', 'item').lower().strip()
            c_nome = x.get('categoria', 'OUTROS').upper().strip()
            if not n: continue
            cat = Categoria.query.filter_by(nome=c_nome).first()
            if not cat: cat = Categoria(nome=c_nome); db.session.add(cat); db.session.flush()
            und = UnidadeMedida.query.filter_by(simbolo=x.get('unidade','un')).first()
            prod = Produto.query.filter_by(nome=n).first()
            if not prod:
                prod = Produto(nome=n, emoji=x.get('emoji'), categoria_id=cat.id, unidade_padrao_id=und.id if und else None)
                db.session.add(prod); db.session.flush()
            existe = ListaItem.query.filter(ListaItem.produto_id==prod.id, or_(ListaItem.status=='pendente', ListaItem.status=='comprado')).first()
            if existe:
                itens_ignorados.append(prod.nome.title())
            else:
                db.session.add(ListaItem(produto_id=prod.id, quantidade=x.get('quantidade', 1), usuario=d.get('usuario','Anônimo'), origem_input="voice"))
                itens_salvos.append(prod.nome.title())
        db.session.commit()

        msg_parts = []
        if itens_salvos: msg_parts.append(f"✅ Adicionados: {', '.join(itens_salvos)}")
        if itens_ignorados: msg_parts.append(f"⚠️ Já na lista: {', '.join(itens_ignorados)}")
        return jsonify({"message": " | ".join(msg_parts) if msg_parts else "Nenhum item identificado."}), 201

    except Exception as e:
        logger.error(f"ERRO MAGIC: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# --- ENDPOINTS DE TAREFAS (v2.0) ---
@app.route('/toggle_task/<int:id>', methods=['POST'])
@login_required
def toggle_task(id):
    t = db.session.get(Task, id)
    if t:
        t.status = 'concluido' if t.status == 'pendente' else 'pendente'
        db.session.commit()
        return jsonify({'status': 'success', 'novo_status': t.status})
    return jsonify({'status': 'error'}), 404

@app.route('/voice/process', methods=['POST'])
def voice_process():
    d = request.get_json()
    if not d: return jsonify({'erro': 'JSON invalido'}), 400
    
    texto_entrada = d.get('texto', '')
    # Garante que temos um nome válido, senão usa 'Casal' como fallback seguro
    usuario = d.get('usuario', 'Casal') 

    if not texto_entrada:
        return jsonify({'erro': 'Texto vazio'}), 400

    # Contexto Temporal
    agora = datetime.datetime.now()
    str_agora = agora.strftime("%Y-%m-%d %H:%M Semana: %A")
    data_hoje_iso = agora.strftime("%Y-%m-%d")

    # --- 1. Configuração da IA ---
    try:
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.0, # Zero criatividade para garantir obediência às regras
            max_retries=0,
            timeout=10
        )
        
        # MUDANÇA CRÍTICA AQUI: Injeção do Contexto de Usuário
        template_str = """
        Você é o FamilyOS, um assistente pessoal inteligente.
        
        CONTEXTO ATUAL:
        - Data/Hora: {data_atual}
        - Quem está falando (Remetente): {usuario}

        OBJETIVO:
        Analise o texto e extraia um JSON estruturado seguindo estritamente estas regras:

        1. SHOPPING (Compras):
           - Categorias: PADARIA, CARNES, LIMPEZA, HORTIFRÚTI, OUTROS.
           - Emoji: Escolha um emoji visualmente representativo.
        
        2. TASKS (Tarefas Domésticas):
           - Prioridade (prio): 1 (Baixa), 2 (Média), 3 (Alta).
           - Responsável (resp): 
             - Se a frase for no plural ("Temos que", "Nós", "Vamos"), use "Casal".
             - Se citar um nome explícito ("Débora precisa..."), use o nome citado.
             - Se o sujeito for oculto ou primeira pessoa ("Lavar o carro", "Eu preciso..."), atribua ao REMETENTE ({usuario}).
        
        3. REMINDERS (Lembretes com Data/Hora):
           - Se disser apenas a hora (ex: "às 14h"), assuma a data de HOJE.

        FORMATO DE SAÍDA (JSON PURO):
        {{
            "shopping": [ {{ "nome": "item", "qty": 1, "cat": "CATEGORIA", "emoji": "🍎" }} ],
            "tasks": [ {{ "desc": "ação", "resp": "Nome", "prio": 1-3 }} ],
            "reminders": [ {{ "title": "título", "date": "YYYY-MM-DD", "time": "HH:MM", "notes": "detalhes" }} ]
        }}
        
        TEXTO DO USUÁRIO: "{texto}"
        """
        
        prompt = ChatPromptTemplate.from_template(template_str)
        chain = prompt | model
        
        # Passamos 'usuario' para o template preencher o contexto
        res = chain.invoke({
            "data_atual": str_agora, 
            "texto": texto_entrada,
            "usuario": usuario 
        })
        
        clean_json = re.sub(r'```json|```', '', res.content).strip()
        if not clean_json.startswith('{') and not clean_json.startswith('['):
             raise ValueError("IA não retornou JSON válido")
             
        dados = json.loads(clean_json)
        logger.info(f"🤖 RAW JSON IA: {dados}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"⚠️ Erro IA: {error_msg}")
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return jsonify({"message": "🧠 Cota de IA excedida. Tente em 1 minuto.", "status": "error"}), 429
        return jsonify({'erro': 'Falha na interpretação da IA.'}), 500

    # --- 2. Processamento dos Dados (O resto do código permanece igual) ---
    logs_acao = []
    webhook_create_url = os.getenv('N8N_WEBHOOK_TASKS', '').strip()

    try:
        # --- A. SHOPPING ---
        shopping_add = []
        shopping_exist = []

        lista_compras = dados.get('shopping')
        if lista_compras and isinstance(lista_compras, list):
            for item in lista_compras:
                nome = item.get('nome', '').lower().strip()
                if not nome: continue 

                cat_nome = item.get('cat', 'OUTROS').upper()
                emoji_ia = item.get('emoji', '📦')

                cat = Categoria.query.filter_by(nome=cat_nome).first()
                if not cat: 
                    cat = Categoria(nome=cat_nome)
                    db.session.add(cat)
                    db.session.flush()
                
                prod = Produto.query.filter_by(nome=nome).first()
                if not prod:
                    prod = Produto(nome=nome, categoria_id=cat.id, emoji=emoji_ia)
                    db.session.add(prod)
                    db.session.flush()
                
                existe = ListaItem.query.filter(
                    ListaItem.produto_id == prod.id, 
                    ListaItem.status.in_(['pendente', 'comprado'])
                ).first()

                if not existe:
                    db.session.add(ListaItem(
                        produto_id=prod.id, 
                        quantidade=item.get('qty', 1), 
                        usuario=usuario, 
                        origem_input="omniscient"
                    ))
                    shopping_add.append(f"{emoji_ia} {nome.title()}")
                else:
                    shopping_exist.append(nome.title())

        msgs_shopping = []
        if shopping_add: msgs_shopping.append(f"🛒 Compra: {', '.join(shopping_add)}")
        if shopping_exist: msgs_shopping.append(f"⚠️ Já na lista: {', '.join(shopping_exist)}")
        if msgs_shopping: logs_acao.append(" | ".join(msgs_shopping))

        # --- B. TASKS ---
        tasks_add = []
        tasks_exist = []

        lista_tarefas = dados.get('tasks')
        if lista_tarefas and isinstance(lista_tarefas, list):
            for task in lista_tarefas:
                desc = task.get('desc', '').strip()
                if not desc: continue 

                # Fallback: Se a IA ainda falhar e mandar vazio, usa o usuario que enviou
                resp_raw = task.get('resp')
                if not resp_raw:
                    resp = usuario.capitalize()
                else:
                    resp = resp_raw.capitalize()

                try: prio = int(task.get('prio', 1))
                except: prio = 1

                existe_task = Task.query.filter(
                    Task.descricao.ilike(desc), 
                    Task.responsavel == resp,
                    Task.status == 'pendente'
                ).first()

                if not existe_task:
                    t = Task(descricao=desc, responsavel=resp, prioridade=prio, status='pendente')
                    db.session.add(t)
                    tasks_add.append(f"✅ Tarefa ({resp}): {desc}")
                else:
                    tasks_exist.append(f"{desc}")

        if tasks_add: logs_acao.extend(tasks_add)
        if tasks_exist: logs_acao.append(f"⚠️ Tarefas ignoradas: {len(tasks_exist)}")

        # --- C. REMINDERS (Mantido Igual) ---
        lista_reminders = dados.get('reminders')
        if lista_reminders and isinstance(lista_reminders, list):
            for rem in lista_reminders:
                title = rem.get('title', '').strip()
                date_str = rem.get('date')
                time_str = rem.get('time')
                
                if not title: continue 

                if not date_str: date_str = data_hoje_iso

                if date_str:
                    try:
                        due_date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        if time_str:
                            due_time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
                            full_dt = datetime.datetime.combine(due_date_obj, due_time_obj)
                            iso_google = full_dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')
                            title_for_google = f"{title} [{time_str}]" 
                            display_time = time_str
                        else:
                            full_dt = datetime.datetime.combine(due_date_obj, datetime.time.min)
                            iso_google = full_dt.strftime('%Y-%m-%dT00:00:00-03:00')
                            title_for_google = title
                            display_time = "Dia todo"

                        existe_rem = Reminder.query.filter(
                            Reminder.title.ilike(title),
                            Reminder.due_date == full_dt,
                            Reminder.status != 'completed'
                        ).first()

                        if existe_rem:
                            logs_acao.append(f"⚠️ Lembrete já existe: {title}")
                            continue 

                        novo_rem = Reminder(
                            title=title, 
                            notes=rem.get('notes', ''),
                            due_date=full_dt,
                            status='needsAction',
                            usuario=usuario
                        )
                        db.session.add(novo_rem)
                        db.session.flush()
                        local_id = novo_rem.id 
                        
                        display_date = full_dt.strftime('%d/%m')
                        logs_acao.append(f"🔔 Lembrete agendado: {title} ({display_date} às {display_time})")

                        if webhook_create_url:
                            try:
                                payload = {
                                    "action": "create",
                                    "local_id": local_id,
                                    "title": title_for_google,
                                    "notes": rem.get('notes', ''),
                                    "due": iso_google
                                }
                                requests.post(webhook_create_url, json=payload, timeout=2)
                            except Exception as e_webhook:
                                logger.warning(f"Falha webhook N8N: {e_webhook}")
                    
                    except Exception as e_rem:
                        logger.error(f"❌ Erro processando data reminder: {e_rem}")

        db.session.commit()
        
        msg_final = "\n".join(logs_acao) if logs_acao else "Nenhuma ação necessária identificada."
        return jsonify({'message': msg_final}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro Geral Omni: {traceback.format_exc()}")
        return jsonify({'erro': str(e)}), 500


def tasks_magic():
    current_context = f"Hoje é {datetime.now().strftime('%A, %d de %B de %Y, às %H:%M')}."
    # 1. Configura IA
    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

        # Prompt Atualizado: Pede uma LISTA de objetos JSON
        prompt = """
        Você é um assistente de gestão doméstica. Analise o pedido e extraia uma LISTA de tarefas.
        Se houver mais de uma ação na mesma frase, separe em itens diferentes.

        Retorne APENAS um JSON array neste formato:
        [
            {{
                "descricao": "Ação 1",
                "responsavel": "Quem?",
                "prioridade": 1, 2 ou 3
            }},
            {{
                "descricao": "Ação 2",
                ...
            }}
        ]

        REGRAS DE RESPONSÁVEL:
        - Se citar nome -> Usa o nome.
        - Se citar 'nós/temos' -> "Casal".
        - Se não citar -> "Outro".

        REGRAS DE PRIORIDADE:
        - 1 (Baixa/Verde): Rotina, sem data.
        - 2 (Média/Amarela): Importante.
        - 3 (Alta/Vermelha): Urgente, hoje, agora.

        ### IMPORTANTE
        Catharina e a neta do Casal, se escreve com 'h' Catharina.

        Texto: {texto}
        """
        chain = ChatPromptTemplate.from_template(prompt) | model
    except Exception as e: return jsonify({'erro': str(e)}), 503

    d = request.get_json()
    if not d: return jsonify({'erro': 'Sem dados'}), 400

    texto = d.get('texto')
    remetente = d.get('remetente') or d.get('usuario') or 'Alguém'

    try:
        # 2. Processa IA
        logger.info(f"Processando Tarefa: {texto}")
        res = chain.invoke({"texto": texto})
        content = res.content

        # Parser JSON de Lista (Blindado)
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1:
            dados = json.loads(content[start_idx:end_idx+1])
        else:
            # Tenta limpar markdown se não achar colchetes limpos
            clean = re.sub(r'```json|```', '', content).strip()
            # Se a IA devolveu um objeto único sem colchetes, envolve em lista
            if clean.startswith('{'): clean = f"[{clean}]"
            dados = json.loads(clean)

        # Garante que seja uma lista
        if isinstance(dados, dict): dados = [dados]

        # 3. Processamento em Lote
        msgs_telegram = []

        for item in dados:
            # Lógica de Atribuição
            resp_ia = item.get('responsavel', 'Outro')
            if resp_ia == 'Outro':
                responsavel_final = remetente
            else:
                responsavel_final = resp_ia.capitalize()

            # Salva no Banco
            nova_task = Task(
                descricao=item.get('descricao'),
                responsavel=responsavel_final,
                prioridade=int(item.get('prioridade', 1)),
                status='pendente'
            )
            db.session.add(nova_task)

            # Prepara mensagem de retorno
            icones = {1: "🟢", 2: "🟡", 3: "🔴"}
            p_icon = icones.get(nova_task.prioridade, "⚪")
            msgs_telegram.append(f"✅ {responsavel_final}: {p_icon} {nova_task.descricao}")

        db.session.commit()

        # 4. Resposta Agrupada
        return jsonify({
            "message": "\n".join(msgs_telegram)
        }), 201

    except Exception as e:
        logger.error(f"ERRO TASK: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500

@app.route('/reminders')
@login_required
def reminders_list():
    # Busca tarefas pendentes e ordena por data
    tasks = Reminder.query.filter(
        or_(Reminder.status == 'needsAction', Reminder.status.is_(None))
    ).order_by(Reminder.due_date.asc().nulls_last()).all()

    return render_template('reminders.html', tasks=tasks, active_page='reminders')

@app.route('/tasks/update', methods=['POST'])
@login_required
def update_task():
    d = request.get_json()
    task_id = int(d.get('id'))

    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Tarefa não encontrada'}), 404

    task.descricao = d.get('descricao')
    task.responsavel = d.get('responsavel')
    task.prioridade = int(d.get('prioridade'))

    db.session.commit()
    return jsonify({'status': 'success'})

# --- ROTA DE SINCRONIZAÇÃO DE LEMBRETES (v2.2 - Com Deletar) ---
@app.route('/reminders/sync', methods=['POST'])
def sync_reminders():
    raw_data = request.get_json()
    
    # Debug: Print the exact type to be sure
    # logger.info(f"📦 Type: {type(raw_data)} - Content: {str(raw_data)[:100]}")

    dados = []

    # --- LOGIC TO EXTRACT DATA ---
    # 1. If it's a list, check the first item
    if isinstance(raw_data, list):
        if len(raw_data) > 0:
            first_item = raw_data[0]
            # Case: The list contains the n8n wrapper object
            if isinstance(first_item, dict) and 'dados_agrupados' in first_item:
                dados = first_item['dados_agrupados']
            # Case: The list is ALREADY the tasks (e.g. sent individually without batching)
            else:
                dados = raw_data
        else:
            dados = [] # Empty list

    # 2. If it's a dict (single object or direct wrapper)
    elif isinstance(raw_data, dict):
        if 'dados_agrupados' in raw_data:
            dados = raw_data['dados_agrupados']
        else:
            dados = [raw_data] # Single task wrapped in list
    
    # 3. Final Safety Check: Ensure 'dados' is a list
    if not isinstance(dados, list):
        dados = []

    usuario_padrao = request.args.get('usuario', 'Google')
    count_criado = 0
    count_atualizado = 0
    count_deletado = 0
    count_ignorados = 0

    try:
        for item in dados:
            if not isinstance(item, dict): 
                continue

            # 2. HYBRID ID CHECK
            gid = item.get('google_id') or item.get('id')
            
            if not gid:
                # Debug log for ignored items to help diagnose
                # logger.warning(f"⚠️ Item ignorado (sem ID): {item.keys()}")
                count_ignorados += 1
                continue

            lembrete = Reminder.query.filter_by(google_id=gid).first()

            # --- DELETION LOGIC ---
            is_deleted = item.get('deleted')
            should_delete = (is_deleted is True) or (str(is_deleted).lower() == 'true')
            
            if should_delete:
                if lembrete:
                    db.session.delete(lembrete)
                    count_deletado += 1
                continue 

            # --- CREATE/UPDATE LOGIC ---
            data_vencimento = None
            due_str = item.get('due')
            if due_str:
                try:
                    iso_date = due_str.replace('Z', '')
                    data_vencimento = datetime.datetime.fromisoformat(iso_date)
                except:
                    pass

            if not lembrete:
                lembrete = Reminder(google_id=gid)
                db.session.add(lembrete)
                count_criado += 1
            else:
                count_atualizado += 1

            lembrete.title = item.get('title', 'Sem Título')
            lembrete.notes = item.get('notes')
            lembrete.status = item.get('status')
            lembrete.parent_id = item.get('parent')
            lembrete.due_date = data_vencimento
            lembrete.webViewLink = item.get('webViewLink')
            
            if count_criado > 0: 
                lembrete.usuario = usuario_padrao
            
            lembrete.last_updated = datetime.datetime.utcnow()

        db.session.commit()

        logger.info(f"🔄 Sync Resumo: +{count_criado}, ~{count_atualizado}, -{count_deletado}, ignorados: {count_ignorados}")

        return jsonify({
            "status": "success",
            "criados": count_criado,
            "atualizados": count_atualizado,
            "deletados": count_deletado,
            "ignorados": count_ignorados
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro Sync Lembretes: {traceback.format_exc()}")
        return jsonify({"erro": str(e)}), 500

@app.route('/reminders/update', methods=['POST'])
@login_required
def update_reminder():
    d = request.get_json()
    rem_id = int(d.get('id'))
    
    reminder = db.session.get(Reminder, rem_id)
    if not reminder:
        return jsonify({'error': 'Lembrete não encontrado'}), 404
    
    # 1. Atualiza campos locais
    reminder.title = d.get('title')
    reminder.notes = d.get('notes')
    
    # 2. Reconstrói data/hora
    date_str = d.get('date') # YYYY-MM-DD
    time_str = d.get('time') # HH:MM
    
    # Inicializa variável para o Google (Importante!)
    iso_date_for_google = None 
    
    if date_str:
        if time_str:
            iso_str = f"{date_str}T{time_str}:00"
            # Formato UTC com Z para o Google
            iso_date_for_google = f"{date_str}T{time_str}:00.000Z"
        else:
            iso_str = f"{date_str}T00:00:00"
            # Google Tasks requer T00:00:00Z para tarefas de dia inteiro
            iso_date_for_google = f"{date_str}T00:00:00.000Z"
        
        try:
            reminder.due_date = datetime.datetime.fromisoformat(iso_str)
        except:
            pass # Mantém data antiga se falhar

    db.session.commit()
    
    # 3. Dispara Sincronia com Google (Via n8n)
    try:
        webhook_url = os.getenv('N8N_WEBHOOK_TASKS') # Pega do .env
        
        if webhook_url and (reminder.google_id or reminder.calendar_id):
            payload = {
                "action": "update",
                "local_id": reminder.id, # Bom enviar sempre
                "google_id": reminder.google_id,
                "calendar_id": reminder.calendar_id, # <--- NOVO: Envia o ID do evento
                "title": reminder.title,
                "notes": reminder.notes
            }
            
            if iso_date_for_google:
                payload["due"] = iso_date_for_google
            
            logger.info(f"🚀 Enviando update para n8n: {payload}")
            requests.post(webhook_url, json=payload, timeout=2)
            
    except Exception as e:
        logger.error(f"❌ Erro no envio para n8n: {e}")

    return jsonify({'status': 'success'})

# --- NOVO: Rota para Criar Lembrete Manualmente ou via IA ---
@app.route('/reminders/create', methods=['POST'])
def create_reminder():
    d = request.get_json()
    if not d: return jsonify({'erro': 'JSON invalido'}), 400

    title = d.get('title')
    notes = d.get('notes', '')
    date_str = d.get('date') # Espera formato YYYY-MM-DD
    time_str = d.get('time') # Espera formato HH:MM
    
    # Tratamento da Data
    dt_final = None
    iso_google = None
    
    if date_str:
        try:
            if time_str:
                dt_final = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                # Formato RFC3339 para Google
                iso_google = f"{date_str}T{time_str}:00.000Z"
            else:
                dt_final = datetime.datetime.fromisoformat(f"{date_str}T00:00:00")
                iso_google = f"{date_str}T00:00:00.000Z"
        except ValueError:
            pass # Se falhar, cria sem data (apenas lista)

    try:
        # 1. Salva no Banco Local (sem Google ID ainda)
        novo_lembrete = Reminder(
            title=title,
            notes=notes,
            due_date=dt_final,
            status='needsAction',
            usuario=d.get('usuario', 'API')
        )
        db.session.add(novo_lembrete)
        db.session.commit()

        # 2. Dispara Webhook para o n8n criar no Google Tasks
        # O n8n deve criar lá e depois chamar /reminders/sync para atualizar o google_id aqui
        webhook_url = os.getenv('N8N_WEBHOOK_TASKS') 
        
        if webhook_url:
            payload = {
                "action": "create",
                "local_id": novo_lembrete.id, # Enviamos o ID local para rastreio
                "title": title,
                "notes": notes,
                "due": iso_google
            }
            # Fire and forget (não travamos a request esperando o Google)
            try:
                requests.post(webhook_url, json=payload, timeout=2)
            except Exception as e:
                logger.error(f"Erro ao disparar webhook n8n: {e}")

        return jsonify({'status': 'success', 'id': novo_lembrete.id, 'message': f'Lembrete "{title}" criado.'}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro Create Reminder: {traceback.format_exc()}")
        return jsonify({'erro': str(e)}), 500

# --- ROTA: GATILHO MANUAL (Acionada pelo Botão do Front) ---
@app.route('/reminders/trigger', methods=['POST'])
@login_required
def trigger_manual_sync():
    """
    Aciona o Webhook do N8N para buscar dados do Google Tasks.
    A URL é carregada do .env para segurança.
    """
    # 🔒 Carrega a URL do .env (Segurança)
    webhook_url = os.getenv('N8N_WEBHOOK_REMINDERS')
    
    if not webhook_url:
        logger.error("❌ Erro: Variável N8N_WEBHOOK_REMINDERS não definida no .env")
        return jsonify({"status": "error", "message": "Configuração de servidor ausente."}), 500

    try:
        # Payload informativo (quem solicitou)
        payload = {
            "trigger": "manual_button",
            "requested_by": current_user.username
        }
        
        # Fire and Forget com timeout curto
        try:
            requests.post(webhook_url, json=payload, timeout=2)
            logger.info(f"🚀 Trigger de sync disparado por {current_user.username}")
        except requests.exceptions.ReadTimeout:
            # Timeout é esperado e aceitável aqui (o N8N pode demorar para responder)
            pass 
        except Exception as request_error:
             logger.error(f"⚠️ Erro na conexão com N8N: {request_error}")
             # Não retornamos erro 500 aqui para não assustar o usuário se o N8N estiver apenas lento
            
        return jsonify({
            "status": "success", 
            "message": "Sincronização solicitada!"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro crítico no trigger: {e}")
        return jsonify({"status": "error", "message": "Erro interno."}), 500
    

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)