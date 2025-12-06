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
from dateutil import parser # Pode precisar instalar: pip install python-dateutil

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
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter(User.username.ilike(u.strip())).first()
        if user and user.check_password(p):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        flash('Erro login')
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
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
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

# --- NOVO ENDPOINT DE TAREFAS (v2.1 - Multi-Tasks) ---
@app.route('/tasks/magic', methods=['POST'])
def tasks_magic():
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

# --- ROTA DE SINCRONIZAÇÃO DE LEMBRETES ---
@app.route('/reminders/sync', methods=['POST'])
def sync_reminders():
    dados = request.get_json()
    print(f"DEBUG PAYLOAD: {dados}") # Pode comentar se quiser limpar o log
    
    # Garante que seja uma lista para iterar
    if isinstance(dados, dict): dados = [dados]
    
    usuario_padrao = request.args.get('usuario', 'Google') 

    count_criado = 0
    count_atualizado = 0

    try:
        for item in dados:
            # CORREÇÃO AQUI: O n8n manda 'google_id', não 'id'
            gid = item.get('google_id') 
            
            if not gid: 
                print("Item sem ID ignorado")
                continue 

            lembrete = Reminder.query.filter_by(google_id=gid).first()

            # Tratamento de Data
            data_vencimento = None
            if item.get('due'):
                try:
                    # O Google manda formato ISO com Z no final
                    data_vencimento = datetime.datetime.fromisoformat(item.get('due').replace('Z', '+00:00'))
                except:
                    pass

            if not lembrete:
                lembrete = Reminder(google_id=gid)
                db.session.add(lembrete)
                count_criado += 1
            else:
                count_atualizado += 1

            # Atualiza campos
            lembrete.title = item.get('title', 'Sem Título')
            lembrete.notes = item.get('notes')
            lembrete.status = item.get('status')
            lembrete.parent_id = item.get('parent') # O n8n precisa mandar esse campo se quiser hierarquia
            lembrete.due_date = data_vencimento
            lembrete.usuario = usuario_padrao
            lembrete.last_updated = datetime.datetime.utcnow()

        db.session.commit()
        return jsonify({
            "status": "success", 
            "criados": count_criado, 
            "atualizados": count_atualizado
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
    
    # Atualiza campos locais
    reminder.title = d.get('title')
    reminder.notes = d.get('notes')
    
    # Reconstrói data/hora
    date_str = d.get('date') # YYYY-MM-DD
    time_str = d.get('time') # HH:MM
    
    if date_str:
        if time_str:
            iso_str = f"{date_str}T{time_str}:00"
        else:
            iso_str = f"{date_str}T00:00:00"
        
        try:
            reminder.due_date = datetime.datetime.fromisoformat(iso_str)
        except:
            pass # Mantém data antiga se falhar
    
    # Marca como pendente de sync (para o futuro n8n pegar)
    # Por enquanto apenas salva
    db.session.commit()
    
    # TODO: Disparar Webhook do n8n aqui para atualizar o Google Tasks
    # requests.post(N8N_WEBHOOK_UPDATE_GOOGLE, json=d)

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)