import json
import random
import os
import requests
import datetime
from flask import Blueprint, render_template, current_app, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.core import WeatherCache
from app.models.shopping import ListaItem, Produto, Categoria
from app.models.tasks import Task, Reminder

main_bp = Blueprint('main', __name__)

# --- FUNÇÕES AUXILIARES ---

def get_daily_quote():
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

def get_weather_data():
    """Busca dados de clima com Cache de 60 minutos para evitar rate-limit"""
    cidade = "Itajai,SC"
    agora = datetime.datetime.utcnow()
    
    # 1. Tenta Cache Local
    cache = db.session.query(WeatherCache).first()
    if cache and cache.last_updated and (agora - cache.last_updated).total_seconds() < 3600:
        try:
            return json.loads(cache.data_json)
        except:
            pass # Se o JSON estiver corrompido, busca de novo

    # 2. Busca na API Externa (HG Brasil)
    key = os.getenv('HGBRASIL_KEY')
    if not key: return None

    try:
        url = f"https://api.hgbrasil.com/weather?key={key}&city_name={cidade}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            
            # 3. Salva no Cache
            if not cache:
                cache = WeatherCache(city=cidade)
                db.session.add(cache)
            
            cache.data_json = json.dumps(data)
            cache.last_updated = agora
            db.session.commit()
            
            return data
    except Exception as e:
        print(f"Erro clima: {e}")
        return None

def _smart_categorize(nome_produto):
    """
    Tenta adivinhar a categoria sem chamar a IA pesada.
    1. Verifica histórico (Memória).
    2. Verifica palavras-chave (Regras Rápidas).
    3. Fallback para 'OUTROS'.
    """
    nome = nome_produto.lower().strip()
    
    # 1. Memória Muscular (Já comprei isso antes?)
    # Busca qualquer produto com esse nome que já tenha categoria definida
    prod_existente = Produto.query.filter(Produto.nome.ilike(nome_produto)).first()
    if prod_existente and prod_existente.categoria:
        return prod_existente.categoria.nome

    # 2. Regras Básicas (Keywords)
    keywords = {
        'HORTIFRÚTI': ['maçã', 'banana', 'batata', 'cebola', 'tomate', 'alface', 'uva', 'limão', 'alho', 'cenoura'],
        'LATICINIOS': ['leite', 'queijo', 'manteiga', 'iogurte', 'requeijão', 'creme de leite'],
        'CARNES': ['frango', 'carne', 'peixe', 'linguiça', 'bacon', 'presunto', 'hambúrguer'],
        'PADARIA': ['pão', 'bolo', 'sonho', 'biscoito', 'torrada'],
        'BEBIDAS': ['cerveja', 'refrigerante', 'suco', 'água', 'vinho', 'coca', 'café'],
        'LIMPEZA': ['sabão', 'detergente', 'água sanitária', 'papel', 'bucha', 'amaciante', 'veja'],
        'HIGIENE': ['sabonete', 'pasta', 'shampoo', 'condicionador', 'papel higiênico']
    }
    
    for cat, terms in keywords.items():
        if any(term in nome for term in terms):
            return cat
            
    return 'OUTROS'

# --- ROTAS DE VISUALIZAÇÃO (GET) ---

@main_bp.route('/')
@login_required
def index():
    weather = get_weather_data()
    temp = weather['results']['temp'] if weather else "--"
    desc = weather['results']['description'] if weather else "Indisponível"
    
    # Resumo Rápido
    shopping_count = ListaItem.query.filter_by(status='pendente').count()
    tasks_count = Task.query.filter_by(status='pendente').count()
    
    return render_template('dashboard.html', 
                         usuario=current_user.username,
                         frase=get_daily_quote(),
                         temp=temp,
                         desc=desc,
                         shopping_count=shopping_count,
                         tasks_count=tasks_count,
                         active_page='home')

@main_bp.route('/shopping')
@login_required
def shopping_list():
    # Carrega itens pendentes/comprados com join otimizado
    itens = ListaItem.query.options(joinedload(ListaItem.produto).joinedload(Produto.categoria)) \
             .filter(ListaItem.status.in_(['pendente', 'comprado'])) \
             .order_by(ListaItem.status.desc(), ListaItem.created_at.desc()).all()

    # Agrupa por Categoria
    categorias = {}
    for item in itens:
        cat_nome = item.produto.categoria.nome if item.produto.categoria else 'OUTROS'
        if cat_nome not in categorias:
            categorias[cat_nome] = []
        
        # Formata para o template
        emoji = item.produto.emoji if item.produto.emoji else '📦'
        # Adiciona a quantidade no objeto para acesso fácil no template
        item.qty_display = item.quantidade 
        
        categorias[cat_nome].append({
            'id': item.id,
            'nome': item.produto.nome,
            'emoji': emoji,
            'usuario': item.usuario,
            'detalhes': item.created_at.strftime('%d/%m'),
            'status': item.status,
            'quantidade': item.quantidade  # Passando a quantidade explicitamente
        })

    return render_template('shopping.html', categorias=categorias, active_page='shopping')

@main_bp.route('/tasks')
@login_required
def task_board():
    tasks = Task.query.filter(or_(Task.status=='pendente', Task.status=='concluido')) \
              .order_by(Task.prioridade.desc(), Task.created_at.asc()).all()

    view = {'Thiago': [], 'Debora': [], 'Casal': []}
    for t in tasks:
        resp = t.responsavel if t.responsavel in view else 'Thiago'
        view[resp].append(t)
    return render_template('tasks.html', tasks=view, active_page='tasks')

@main_bp.route('/reminders')
@login_required
def reminders_list():
    tasks = Reminder.query.filter(
        Reminder.status != 'completed'
    ).order_by(Reminder.due_date.asc()).all()
    
    return render_template('reminders.html', tasks=tasks, active_page='reminders')

@main_bp.route('/chat')
@login_required
def chat_interface():
    return render_template('chat.html', active_page='chat')

@main_bp.route('/login')
def login():
    return render_template('login.html')

# --- ROTAS DE AÇÃO (POST API) ---

@main_bp.route('/shopping/add', methods=['POST'])
@login_required
def add_shopping_item():
    """
    Adiciona item manualmente.
    - Categoria: Auto-detectada (_smart_categorize).
    - Quantidade: Recebida ou padrão 1.
    """
    data = request.get_json()
    nome = data.get('nome', '').strip()
    
    # Tratamento seguro da quantidade
    try:
        qty = int(data.get('quantidade', 1))
        if qty < 1: qty = 1
    except (ValueError, TypeError):
        qty = 1
    
    if not nome:
        return jsonify({'error': 'Nome é obrigatório'}), 400

    try:
        # 1. Inteligência: Define a Categoria Automaticamente
        cat_nome = _smart_categorize(nome)
        
        # 2. Busca ou Cria Categoria
        categoria = Categoria.query.filter_by(nome=cat_nome).first()
        if not categoria:
            categoria = Categoria(nome=cat_nome)
            db.session.add(categoria)
            db.session.flush()

        # 3. Busca ou Cria Produto
        produto = Produto.query.filter_by(nome=nome).first()
        if not produto:
            produto = Produto(nome=nome, categoria_id=categoria.id, emoji='📦')
            db.session.add(produto)
            db.session.flush()

        # 4. Adiciona/Atualiza na Lista
        item_existente = ListaItem.query.filter_by(
            produto_id=produto.id, 
            usuario=current_user.username
        ).filter(ListaItem.status.in_(['pendente', 'comprado'])).first()

        if item_existente:
            # Se já existe, atualizamos a quantidade e reativamos se necessário
            item_existente.quantidade = qty 
            if item_existente.status == 'comprado':
                item_existente.status = 'pendente'
                msg = f"Reativado: {qty}x {nome}"
            else:
                msg = f"Atualizado: {qty}x {nome}"
        else:
            novo_item = ListaItem(produto_id=produto.id, quantidade=qty, usuario=current_user.username)
            db.session.add(novo_item)
            msg = f"Adicionado: {qty}x {nome}"

        db.session.commit()
        return jsonify({'message': msg, 'status': 'success'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/update_item', methods=['POST'])
@login_required
def update_item():
    """
    Atualiza um item existente (Nome, Categoria ou Quantidade).
    """
    data = request.get_json()
    item_id = data.get('id')
    nome = data.get('nome')
    cat_nome = data.get('categoria') # Opcional agora
    
    try:
        qty = int(data.get('quantidade', 1))
        if qty < 1: qty = 1
    except:
        qty = 1

    item = ListaItem.query.get(item_id)
    if not item: return jsonify({'error': 'Item não encontrado'}), 404

    try:
        # Atualiza Nome do Produto
        if nome and nome != item.produto.nome:
            # Verifica se já existe outro produto com esse nome para não duplicar
            prod_existente = Produto.query.filter_by(nome=nome).first()
            if prod_existente:
                item.produto = prod_existente
            else:
                # Renomeia o produto atual (Simples)
                item.produto.nome = nome
        
        # Atualiza Categoria (Se fornecida)
        if cat_nome:
            cat = Categoria.query.filter_by(nome=cat_nome).first()
            if cat:
                item.produto.categoria = cat

        # Atualiza Quantidade
        item.quantidade = qty
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/toggle_item/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(item_id):
    item = ListaItem.query.get(item_id)
    if item:
        item.status = 'comprado' if item.status == 'pendente' else 'pendente'
        db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    # Arquiva apenas os itens do usuário atual ou todos? 
    # Modelo atual: Itens "pendente/comprado" ficam visíveis. 
    # Clear move 'comprado' -> 'arquivado'
    
    # Itens comprados viram 'arquivado' (soft delete da view)
    ListaItem.query.filter_by(status='comprado').update({'status': 'arquivado'})
    db.session.commit()
    return jsonify({'success': True})