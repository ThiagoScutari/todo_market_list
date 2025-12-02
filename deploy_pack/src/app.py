import os
import re
import json
import datetime
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "uma_chave_super_secreta_e_segura")

# --- CONFIGURAÇÃO DE BANCO DE DADOS BLINDADA (LOCAL + DOCKER) ---
# 1. Identifica onde este arquivo (app.py) está
basedir = os.path.abspath(os.path.dirname(__file__)) # Pasta src/
project_root = os.path.dirname(basedir)              # Pasta do projeto/

# 2. Define onde os dados ficam (funciona no Windows e Linux)
data_dir = os.path.join(project_root, 'data')

# 3. Garante que a pasta existe (evita erro no primeiro uso local)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# 4. Define o caminho do arquivo padrão para uso local
default_db_path = os.path.join(data_dir, 'familyos.db')

# 5. Prioridade: Variável de Ambiente (Docker) > Arquivo Local (VSCode)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{default_db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ---------------------------------------------------------------

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash in ['2904', '1712']:
            return self.password_hash == password
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

class TipoLista(db.Model):
    __tablename__ = 'tipos_lista'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)

class ListaItem(db.Model):
    __tablename__ = 'lista_itens'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    tipo_lista_id = db.Column(db.Integer, db.ForeignKey('tipos_lista.id'), default=1)
    quantidade = db.Column(db.Float, nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades_medida.id'))
    usuario = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pendente')
    adicionado_em = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    origem_input = db.Column(db.String(100))

    produto = db.relationship('Produto', backref='itens_lista')
    unidade = db.relationship('UnidadeMedida')
    tipo_lista = db.relationship('TipoLista')

# --- HELPER: SANITIZAÇÃO DE DADOS ---
def sanitizar_texto(texto, tipo):
    """
    Remove espaços extras (começo, fim e meio).
    tipo='categoria': Retorna UPPERCASE.
    tipo='item': Retorna lowercase.
    """
    if not texto: return ""
    limpo = " ".join(texto.split()) # Remove espaços duplos internos
    if tipo == 'categoria':
        return limpo.upper()
    return limpo.lower()

# --- CONFIGURAÇÃO DE LOGIN ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- IA ---
# Tenta usar IA apenas se a chave estiver configurada para evitar crash local
try:
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.0)
    
    prompt_template = """
    Extraia os itens de compra. Retorne LISTA JSON.
    Converta nomes para singular e minúsculas.
    Retorne um campo 'emoji' visualmente correspondente ao item.
    Categorias Sugeridas: Hortifrúti, Padaria, Carnes, Limpeza, Bebidas, Churrasco, Laticínios, Outros.

    Exemplo: [{{"nome": "leite", "quantidade": 2, "unidade": "L", "categoria": "Laticínios", "emoji": "🥛"}}]
    Campos: nome, quantidade (float), unidade (símbolo: kg, g, L, ml, un), categoria, emoji.
    Texto: {texto}
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | model
except Exception as e:
    logging.warning(f"IA não configurada (falta API KEY?): {e}")
    chain = None

# --- ROTAS DE AUTH ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha inválidos')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROTAS DA APLICAÇÃO (PROTEGIDAS) ---

@app.route('/', methods=['GET'])
@login_required
def home():
    try:
        itens = ListaItem.query.options(
            joinedload(ListaItem.produto).joinedload(Produto.categoria),
            joinedload(ListaItem.unidade)
        ).filter(or_(ListaItem.status == 'pendente', ListaItem.status == 'comprado')).order_by(ListaItem.adicionado_em.desc()).all()
        
        categorias_view = {}
        for item in itens:
            if not item.produto: continue
            
            # Garante que a exibição respeite a normalização
            cat_nome = item.produto.categoria.nome if item.produto.categoria else "OUTROS"
            
            if cat_nome not in categorias_view: categorias_view[cat_nome] = []
            
            qtd = int(item.quantidade) if item.quantidade and item.quantidade % 1 == 0 else item.quantidade
            und = item.unidade.simbolo if item.unidade else ""
            
            categorias_view[cat_nome].append({
                'id': item.id,
                'nome': item.produto.nome.title(), # Title Case só pra visualização
                'emoji': item.produto.emoji or "🛒",
                'detalhes': f"{qtd}{und}" if und else str(qtd),
                'usuario': item.usuario,
                'status': item.status
            })
            
        return render_template('index.html', categorias=categorias_view)
    except Exception as e:
        # Se for erro de tabela inexistente, sugere rodar o reset_db
        return f"Erro ao carregar itens: {str(e)}. <br>Sugestão: Rode 'python src/reset_db.py' no terminal."

@app.route('/toggle_item/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(item_id):
    try:
        item = ListaItem.query.get(item_id)
        if not item: return jsonify({'status': 'error'}), 404
        item.status = 'comprado' if item.status == 'pendente' else 'pendente'
        db.session.commit()
        return jsonify({'status': 'success', 'novo_status': item.status})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    try:
        itens = ListaItem.query.filter_by(status='comprado').all()
        for item in itens: item.status = 'finalizado'
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- ROTA DE ATUALIZAÇÃO (NORMALIZADA) ---
@app.route('/update_item', methods=['POST'])
@login_required
def update_item():
    data = request.get_json()
    if not data or 'id' not in data or 'nome' not in data or 'categoria' not in data:
        return jsonify({'error': 'Dados inválidos.'}), 400

    try:
        item_id = int(data.get('id'))
        
        # --- APLICAÇÃO DA REGRA DE SANITIZAÇÃO ---
        novo_nome_produto = sanitizar_texto(data.get('nome'), 'item')
        novo_nome_categoria = sanitizar_texto(data.get('categoria'), 'categoria')
        # -----------------------------------------

        item = ListaItem.query.get_or_404(item_id)
        
        # 1. Atualiza/Busca Categoria (NORMALIZADA)
        categoria = Categoria.query.filter_by(nome=novo_nome_categoria).first()
        if not categoria:
            categoria = Categoria(nome=novo_nome_categoria)
            db.session.add(categoria)
            db.session.flush()

        # 2. Atualiza/Busca Produto (NORMALIZADO)
        produto = Produto.query.filter_by(nome=novo_nome_produto).first()
        if not produto:
            produto = Produto(
                nome=novo_nome_produto, 
                categoria_id=categoria.id,
                emoji=item.produto.emoji, 
                unidade_padrao_id=item.produto.unidade_padrao_id
            )
            db.session.add(produto)
            db.session.flush()
        else:
            # Se o produto existe, atualizamos a categoria dele para refletir a edição
            if produto.categoria_id != categoria.id:
                produto.categoria_id = categoria.id

        # 3. Religa o item
        item.produto_id = produto.id
        
        db.session.commit()
        return jsonify({'message': 'Item atualizado com sucesso!'})

    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro ao atualizar item: {e}")
        return jsonify({'error': str(e)}), 500

# --- ROTA MAGIC (NORMALIZADA) ---
@app.route('/magic', methods=['POST'])
def magic_endpoint():
    if not chain:
        return jsonify({"erro": "IA não configurada. Verifique a API KEY."}), 500
        
    data = request.get_json()
    if not data or 'texto' not in data: return jsonify({"erro": "JSON inválido"}), 400

    texto = data['texto']
    usuario = data.get('usuario', 'Anônimo')
    
    try:
        res = chain.invoke({"texto": texto})
        clean_content = re.sub(r'```json|```', '', res.content).strip()
        
        try:
            dados = json.loads(clean_content)
        except:
            fixed = re.sub(r'}\s*{', '}, {', clean_content)
            dados = json.loads(f"[{fixed}]" if not fixed.startswith('[') else fixed)

        if isinstance(dados, dict): dados = [dados]

        itens_salvos = []
        itens_ignorados = []

        for item in dados:
            # --- APLICAÇÃO DA REGRA DE SANITIZAÇÃO (INPUT IA) ---
            cat_raw = item.get('categoria', 'OUTROS')
            nome_raw = item.get('nome', 'item desconhecido')
            
            nome_clean = sanitizar_texto(nome_raw, 'item')
            cat_clean = sanitizar_texto(cat_raw, 'categoria')
            # ----------------------------------------------------

            # Busca/Cria Categoria Normalizada
            cat = Categoria.query.filter(Categoria.nome == cat_clean).first()
            if not cat:
                cat = Categoria(nome=cat_clean)
                db.session.add(cat)
                db.session.flush()

            und = UnidadeMedida.query.filter(UnidadeMedida.simbolo.ilike(f"{item.get('unidade')}")).first()
            
            # Busca/Cria Produto Normalizado
            prod = Produto.query.filter(Produto.nome == nome_clean).first()
            if not prod:
                prod = Produto(
                    nome=nome_clean, 
                    emoji=item.get('emoji'),
                    categoria_id=cat.id, 
                    unidade_padrao_id=und.id if und else None
                )
                db.session.add(prod)
                db.session.flush()
            else:
                if not prod.emoji and item.get('emoji'):
                    prod.emoji = item.get('emoji')

            # Verifica duplicidade na lista (agora mais preciso)
            existe = ListaItem.query.filter(ListaItem.produto_id == prod.id, or_(ListaItem.status == 'pendente', ListaItem.status == 'comprado')).first()
            if existe:
                itens_ignorados.append(prod.nome)
                continue

            novo_item = ListaItem(
                produto_id=prod.id,
                quantidade=item.get('quantidade') or 1,
                unidade_id=und.id if und else None,
                usuario=usuario,
                origem_input="telegram_voice"
            )
            db.session.add(novo_item)
            itens_salvos.append(prod.nome)

        db.session.commit()
        
        msg_parts = []
        if itens_salvos: msg_parts.append(f"✅ Adicionados: {', '.join(itens_salvos)}")
        if itens_ignorados: msg_parts.append(f"⚠️ Já na lista: {', '.join(itens_ignorados)}")
        
        return jsonify({"message": " | ".join(msg_parts) if msg_parts else "Nenhum item novo."}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)