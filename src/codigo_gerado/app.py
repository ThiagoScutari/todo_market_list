import os
import re
import json
import datetime
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import joinedload
from sqlalchemy import or_ # Importar or_

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do App Flask
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todo_market.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS ---

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

# --- CONFIGURAÇÃO DA IA ---
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.0)

prompt_template = """
Extraia os itens de compra. Retorne LISTA JSON.
Converta todos os nomes de produtos estritamente para o SINGULAR e minúsculas (ex: Batatas -> batata).
Exemplo: [{"nome": "leite", "quantidade": 2, "unidade": "L", "categoria": "Padaria"}]
Campos: nome, quantidade (float), unidade (símbolo: kg, g, L, ml, un), categoria (Hortifrúti, Padaria, Carnes, Limpeza).
Texto: {texto}
"""
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | model

# --- ROTAS ---

@app.route('/', methods=['GET'])
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
            
            categorias_view[cat_nome].append({
                'id': item.id,
                'nome': item.produto.nome.title(),
                'detalhes': f"{qtd}{und}" if und else str(qtd),
                'usuario': item.usuario,
                'status': item.status # Adicionar status para o frontend
            })
            
        return render_template('index.html', categorias=categorias_view)
    except Exception as e:
        logging.error(f"Erro ao carregar home: {str(e)}")
        return f"Erro ao carregar: {str(e)}"

@app.route('/toggle_item/<int:item_id>', methods=['POST'])
def toggle_item(item_id):
    try:
        item = ListaItem.query.get(item_id)
        if not item: return jsonify({'status': 'error'}), 404
        item.status = 'comprado' if item.status == 'pendente' else 'pendente'
        db.session.commit()
        return jsonify({'status': 'success', 'novo_status': item.status})
    except Exception as e:
        logging.error(f"Erro ao alternar item {item_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    try:
        itens_comprados = ListaItem.query.filter_by(status='comprado').all()
        for item in itens_comprados:
            item.status = 'finalizado'
        db.session.commit()
        logging.info(f"{len(itens_comprados)} itens marcados como 'finalizado'.")
        return jsonify({'status': 'success', 'message': f'{len(itens_comprados)} itens finalizados.'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro ao limpar carrinho: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/magic', methods=['POST'])
def magic_endpoint():
    data = request.get_json()
    if not data or 'texto' not in data:
        return jsonify({"erro": "JSON inválido"}), 400

    texto = data['texto']
    usuario = data.get('usuario', 'Anônimo')
    
    try:
        # 1. NLP
        res = chain.invoke({"texto": texto})
        clean_content = re.sub(r'```json|```', '', res.content).strip()
        
        try:
            dados = json.loads(clean_content)
        except:
            # Tenta corrigir JSON inválido (ex: múltiplos objetos sem array)
            fixed = re.sub(r'}\s*{', '}, {', clean_content)
            dados = json.loads(f"[{fixed}]" if not fixed.startswith('[') else fixed)

        if isinstance(dados, dict): dados = [dados]

        itens_salvos = []
        for item in dados:
            # Buscas
            cat = Categoria.query.filter(Categoria.nome.ilike(f"%{item.get('categoria')}%")).first()
            und = UnidadeMedida.query.filter(UnidadeMedida.simbolo.ilike(f"{item.get('unidade')}")).first()
            
            # Produto
            prod = Produto.query.filter(Produto.nome.ilike(item.get('nome'))).first()
            if not prod:
                prod = Produto(
                    nome=item.get('nome'),
                    categoria_id=cat.id if cat else None,
                    unidade_padrao_id=und.id if und else None
                )
                db.session.add(prod)
                db.session.flush() # Garante que prod.id esteja disponível

            # Lógica Anti-Duplicidade
            existing_item = ListaItem.query.filter(
                ListaItem.produto_id == prod.id,
                or_(ListaItem.status == 'pendente', ListaItem.status == 'comprado')
            ).first()

            if existing_item:
                logging.info(f"Item '{prod.nome}' (ID: {prod.id}) já existe com status 'pendente' ou 'comprado'. Ignorando adição.")
                continue # Ignora a adição deste item

            # Lista
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
        return jsonify({"message": f"Sucesso! Salvo: {', '.join(itens_salvos)}"}), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro no endpoint magic: {str(e)}")
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)