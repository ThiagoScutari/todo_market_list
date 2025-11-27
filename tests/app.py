import os
import re
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import joinedload

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do App Flask e SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../todo_market.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Importar modelos após a inicialização do db para evitar importação circular
from models.models import Categoria, UnidadeMedida, Produto, ListaItem

# Configuração do Modelo de Linguagem (Gemini)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.1)

# --- FUNÇÕES DE LÓGICA DE NEGÓCIO ---

def extrair_json_do_texto(texto_bruto):
    """Usa regex para encontrar e extrair o conteúdo de um bloco JSON no texto."""
    match = re.search(r'```json\s*([\s\S]*?)\s*```', texto_bruto)
    if match:
        return match.group(1).strip()
    return texto_bruto.strip()

def interpretar_e_salvar(texto_usuario, nome_usuario):
    """Função central que processa o texto, chama o LLM e salva no banco."""
    prompt_template = f"""
    Sua tarefa é extrair itens de uma frase para uma lista de compras.
    Analise o texto: "{texto_usuario}"
    Retorne uma LISTA de objetos JSON. Cada objeto deve ter as chaves: "nome", "quantidade", "unidade" e "categoria".
    - Se a quantidade não for especificada, use 1.
    - Se a unidade não for especificada, use "Unidade".
    - A categoria DEVE ser uma das seguintes: 'Hortifrúti', 'Padaria', 'Carnes', 'Bebidas', 'Limpeza', 'Higiene', 'Mercearia', 'Outros'. Se não tiver certeza, use 'Outros'.
    - O nome do item deve ser normalizado (ex: "costelas" -> "costela").
    - Retorne APENAS a lista JSON, sem nenhum texto adicional ou markdown.
    """
    
    try:
        response = llm.invoke(prompt_template)
        json_str = extrair_json_do_texto(response.content)
        itens = json.loads(json_str)
        
        if not isinstance(itens, list):
            itens = [itens]

        itens_adicionados = []
        for item_data in itens:
            # Busca ou cria Categoria
            categoria_nome = item_data.get('categoria', 'Outros')
            categoria = Categoria.query.filter_by(nome=categoria_nome).first()
            if not categoria:
                categoria = Categoria(nome=categoria_nome)
                db.session.add(categoria)
                db.session.flush()

            # Busca ou cria Unidade de Medida
            unidade_nome = item_data.get('unidade', 'Unidade')
            unidade = UnidadeMedida.query.filter_by(nome=unidade_nome).first()
            if not unidade:
                unidade = UnidadeMedida(nome=unidade_nome)
                db.session.add(unidade)
                db.session.flush()

            # Busca ou cria Produto
            produto_nome = item_data.get('nome').lower().strip()
            produto = Produto.query.filter_by(nome=produto_nome).first()
            if not produto:
                produto = Produto(nome=produto_nome, categoria_id=categoria.id)
                db.session.add(produto)
                db.session.flush()

            # Cria o item na lista
            novo_item = ListaItem(
                produto_id=produto.id,
                quantidade=float(item_data.get('quantidade', 1)),
                unidade_id=unidade.id,
                usuario=nome_usuario
            )
            db.session.add(novo_item)
            itens_adicionados.append(produto_nome)

        db.session.commit()
        return {"status": "sucesso", "itens": itens_adicionados}

    except json.JSONDecodeError:
        db.session.rollback()
        return {"status": "erro", "mensagem": "Erro ao decodificar JSON da IA."}
    except Exception as e:
        db.session.rollback()
        return {"status": "erro", "mensagem": str(e)}

# --- ROTAS DA API ---

@app.route('/magic', methods=['POST'])
def magic_endpoint():
    """Endpoint unificado para receber texto, processar com IA e salvar no banco."""
    data = request.get_json()
    if not data or 'texto' not in data:
        return jsonify({"erro": "JSON inválido ou chave 'texto' ausente."}), 400

    texto_usuario = data['texto']
    nome_usuario = data.get('usuario', 'Indefinido')
    
    resultado = interpretar_e_salvar(texto_usuario, nome_usuario)

    if resultado["status"] == "sucesso":
        nomes_itens = ', '.join(resultado['itens'])
        return jsonify({"message": f"Sucesso! {nome_usuario} adicionou: {nomes_itens}"}), 201
    else:
        return jsonify({"erro": resultado["mensagem"]}), 500

@app.route('/', methods=['GET'])
def home():
    """Renderiza a página inicial com a lista de compras."""
    try:
        # Query para buscar itens pendentes, fazendo join com as tabelas relacionadas
        itens_pendentes = db.session.query(ListaItem).options(
            joinedload(ListaItem.produto).joinedload(Produto.categoria),
            joinedload(ListaItem.unidade)
        ).filter(ListaItem.status == 'pendente').order_by(Produto.categoria_id).all()

        # Agrupa os itens por categoria (contrato de dados definido pelo Architect)
        categorias_agrupadas = {}
        for item in itens_pendentes:
            categoria_nome = item.produto.categoria.nome
            if categoria_nome not in categorias_agrupadas:
                categorias_agrupadas[categoria_nome] = []
            
            # Formata os detalhes conforme especificação
            detalhes = f"{item.quantidade if item.quantidade % 1 != 0 else int(item.quantidade)} {item.unidade.nome}"

            categorias_agrupadas[categoria_nome].append({
                'id': item.id,
                'nome': item.produto.nome.capitalize(),
                'detalhes': detalhes
            })
            
        return render_template('index.html', categorias=categorias_agrupadas)

    except Exception as e:
        # Em caso de erro, renderiza a página com uma mensagem de erro
        return render_template('index.html', erro=str(e))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
