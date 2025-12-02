import os
import re
import json
import datetime
import logging
import traceback
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
from sqlalchemy.engine import Engine

# --- LOGS E CONFIG ---
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

db_path = '/app/data/familyos.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# --- MODELS ---
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

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('home'))
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter(User.username.ilike(u.strip())).first()
        if user and user.check_password(p):
            login_user(user, remember=True)
            return redirect(url_for('home'))
        flash('Erro login')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    itens = ListaItem.query.options(joinedload(ListaItem.produto).joinedload(Produto.categoria), joinedload(ListaItem.unidade)).filter(or_(ListaItem.status == 'pendente', ListaItem.status == 'comprado')).order_by(ListaItem.adicionado_em.desc()).all()
    view = {}
    for i in itens:
        c = i.produto.categoria.nome if i.produto.categoria else "OUTROS"
        if c not in view: view[c] = []
        qtd = int(i.quantidade) if i.quantidade % 1 == 0 else i.quantidade
        und = i.unidade.simbolo if i.unidade else ""
        view[c].append({'id': i.id, 'nome': i.produto.nome.title(), 'emoji': i.produto.emoji, 'detalhes': f"{qtd}{und}", 'usuario': i.usuario, 'status': i.status})
    return render_template('index.html', categorias=view)

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

        # --- PARSER JSON (INFALÍVEL) ---
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx+1]
            dados = json.loads(json_str)
        else:
            clean = re.sub(r'', '', content).strip()
            dados = json.loads(clean)

        if isinstance(dados, dict): dados = [dados]

        # --- LOGICA DE FEEDBACK DETALHADO ---
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

            # Verifica Duplicidade (Pendente ou Comprado)
            existe = ListaItem.query.filter(ListaItem.produto_id==prod.id, or_(ListaItem.status=='pendente', ListaItem.status=='comprado')).first()

            if existe:
                # Se ja existe, adiciona na lista de ignorados
                itens_ignorados.append(prod.nome.title())
            else:
                # Se nao existe, cria e salva
                db.session.add(ListaItem(produto_id=prod.id, quantidade=x.get('quantidade', 1), usuario=d.get('usuario','Anônimo'), origem_input="voice"))
                itens_salvos.append(prod.nome.title())

        db.session.commit()

        # MONTA A RESPOSTA PARA O TELEGRAM
        msg_parts = []
        if itens_salvos: msg_parts.append(f"✅ Adicionados: {', '.join(itens_salvos)}")
        if itens_ignorados: msg_parts.append(f"⚠️ Já na lista: {', '.join(itens_ignorados)}")

        final_msg = " | ".join(msg_parts) if msg_parts else "Nenhum item identificado."

        return jsonify({"message": final_msg}), 201

    except Exception as e:
        logger.error(f"ERRO MAGIC: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=5000)