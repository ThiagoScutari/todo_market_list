import os
import re
import json
import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

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
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    unidade_padrao_id = db.Column(db.Integer, db.ForeignKey('unidades_medida.id'), nullable=True)

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
    # NOVA COLUNA AQUI:
    usuario = db.Column(db.String(50)) 
    status = db.Column(db.String(20), default='pendente')
    adicionado_em = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    origem_input = db.Column(db.String(100))

# --- NLP ---
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.0)

prompt_template = """
Extraia os itens de compra. Retorne LISTA JSON.
Exemplo: [{{"nome": "leite", "quantidade": 2, "unidade": "L", "categoria": "Padaria"}}]
Campos: nome, quantidade (float), unidade (símbolo: kg, g, L, ml, un), categoria (Hortifrúti, Padaria, Carnes, Limpeza).
Texto: {texto}
"""
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | model

# --- ROTAS ---
@app.route('/magic', methods=['POST'])
def magic_item():
    data = request.get_json()
    texto = data.get('texto', '')
    usuario_nome = data.get('usuario', 'Desconhecido') # Pega o usuário do n8n
    
    try:
        # 1. NLP
        res = chain.invoke({"texto": texto})
        clean_content = re.sub(r'```json|```', '', res.content, flags=re.IGNORECASE).strip()
        
        try:
            dados_lista = json.loads(clean_content)
        except:
            fixed = re.sub(r'}\s*{', '}, {', clean_content)
            dados_lista = json.loads(f"[{fixed}]" if not fixed.startswith('[') else fixed)

        if isinstance(dados_lista, dict): dados_lista = [dados_lista]

        # 2. Persistência
        resultados = []
        for item in dados_lista:
            cat_nome = item.get('categoria')
            uni_simbolo = item.get('unidade') or 'un'
            
            categoria = Categoria.query.filter(Categoria.nome.ilike(f"%{cat_nome}%")).first()
            unidade = UnidadeMedida.query.filter(UnidadeMedida.simbolo.ilike(f"{uni_simbolo}")).first()
            
            produto_nome = item.get('nome')
            produto = Produto.query.filter(Produto.nome.ilike(produto_nome)).first()
            
            if not produto:
                produto = Produto(
                    nome=produto_nome,
                    categoria_id=categoria.id if categoria else None,
                    unidade_padrao_id=unidade.id if unidade else None
                )
                db.session.add(produto)
                db.session.flush()
            
            novo_item_lista = ListaItem(
                produto_id=produto.id,
                quantidade=item.get('quantidade') or 1.0,
                unidade_id=unidade.id if unidade else None,
                tipo_lista_id=1,
                usuario=usuario_nome, # SALVA O NOME AQUI
                origem_input="telegram_voice"
            )
            db.session.add(novo_item_lista)
            resultados.append(f"{produto.nome}")
        
        db.session.commit()
        
        return jsonify({
            'message': f"Sucesso! {usuario_nome} adicionou: {', '.join(resultados)}",
            'dados': dados_lista
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)