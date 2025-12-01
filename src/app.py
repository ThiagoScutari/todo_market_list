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
app.secret_key = os.getenv("SECRET_KEY", "uma_chave_super_secreta_e_segura") # Necessário para sessões

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todo_market.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redireciona para cá se não estiver logado

# --- MODELOS ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
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
    emoji = db.Column(db.String(10), nullable=True) # Novo campo Emoji
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

# --- CONFIGURAÇÃO DE LOGIN ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- IA ---
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
            cat_nome = item.produto.categoria.nome if item.produto.categoria else "Outros"
            if cat_nome not in categorias_view: categorias_view[cat_nome] = []
            
            qtd = int(item.quantidade) if item.quantidade and item.quantidade % 1 == 0 else item.quantidade
            und = item.unidade.simbolo if item.unidade else ""
            
            # Passa o Emoji do produto para a view
            categorias_view[cat_nome].append({
                'id': item.id,
                'nome': item.produto.nome.title(),
                'emoji': item.produto.emoji or "🛒", # Fallback se não tiver emoji
                'detalhes': f"{qtd}{und}" if und else str(qtd),
                'usuario': item.usuario,
                'status': item.status
            })
            
        return render_template('index.html', categorias=categorias_view)
    except Exception as e:
        return f"Erro: {str(e)}"

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

@app.route('/magic', methods=['POST'])
# @login_required -> O n8n chama essa rota. Se o n8n não suportar cookies, 
# podemos proteger via API Key ou deixar aberto apenas para localhost no firewall.
# Por simplicidade da Sprint, vamos deixar aberto para o n8n acessar, 
# mas em produção real usaríamos um token no header.
def magic_endpoint():
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
            cat = Categoria.query.filter(Categoria.nome.ilike(f"%{item.get('categoria')}%")).first()
            if not cat and item.get('categoria'):
                # Cria categoria se não existir (Opcional, mas útil para novas sugeridas pela IA)
                cat = Categoria(nome=item.get('categoria'))
                db.session.add(cat)
                db.session.flush()

            und = UnidadeMedida.query.filter(UnidadeMedida.simbolo.ilike(f"{item.get('unidade')}")).first()
            
            prod = Produto.query.filter(Produto.nome.ilike(item.get('nome'))).first()
            if not prod:
                prod = Produto(
                    nome=item.get('nome'), 
                    emoji=item.get('emoji'), # Salva o Emoji
                    categoria_id=cat.id if cat else None, 
                    unidade_padrao_id=und.id if und else None
                )
                db.session.add(prod)
                db.session.flush()
            else:
                # Atualiza emoji se o produto já existia mas não tinha emoji
                if not prod.emoji and item.get('emoji'):
                    prod.emoji = item.get('emoji')

            # Anti-Duplicidade
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