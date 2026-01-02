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
# NOVO IMPORT
from app.services.ai_assistant import AIAssistant

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
    """Busca dados de clima com Cache de 60 minutos"""
    cidade = "Itajai,SC"
    agora = datetime.datetime.utcnow()
    
    cache = db.session.query(WeatherCache).first()
    if cache and cache.last_updated and (agora - cache.last_updated).total_seconds() < 3600:
        try:
            return json.loads(cache.data_json)
        except:
            pass 

    key = os.getenv('HGBRASIL_KEY')
    if not key: return None

    try:
        url = f"https://api.hgbrasil.com/weather?key={key}&city_name={cidade}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
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

# --- ROTAS GET (VISUALIZAÇÃO) ---

@main_bp.route('/')
@login_required
def index():
    weather = get_weather_data()
    temp = weather['results']['temp'] if weather else "--"
    desc = weather['results']['description'] if weather else "Indisponível"
    
    shopping_count = ListaItem.query.filter_by(status='pendente').count()
    tasks_count = Task.query.filter_by(status='pendente').count()
    reminders_count = Reminder.query.filter(Reminder.status != 'completed').count()
    
    return render_template('dashboard.html', 
                         usuario=current_user.username,
                         frase=get_daily_quote(),
                         temp=temp,
                         desc=desc,
                         shopping_count=shopping_count,
                         tasks_count=tasks_count,
                         reminders_count=reminders_count,
                         active_page='home')

@main_bp.route('/shopping')
@login_required
def shopping_list():
    itens = ListaItem.query.options(joinedload(ListaItem.produto).joinedload(Produto.categoria)) \
             .filter(ListaItem.status.in_(['pendente', 'comprado'])) \
             .order_by(ListaItem.status.desc(), ListaItem.id.desc()).all()

    categorias = {}
    for item in itens:
        cat_nome = item.produto.categoria.nome if item.produto.categoria else 'OUTROS'
        if cat_nome not in categorias:
            categorias[cat_nome] = []
        
        emoji = item.produto.emoji if item.produto.emoji else '📦'
        
        categorias[cat_nome].append({
            'id': item.id,
            'nome': item.produto.nome,
            'emoji': emoji,
            'usuario': item.usuario,
            'detalhes': "Lista", 
            'status': item.status,
            'quantidade': int(item.quantidade) # FORÇA INTEIRO NO DISPLAY
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
    tasks = Reminder.query.filter(Reminder.status != 'completed').order_by(Reminder.due_date.asc()).all()
    return render_template('reminders.html', tasks=tasks, active_page='reminders')

@main_bp.route('/chat')
@login_required
def chat_interface():
    return render_template('chat.html', active_page='chat')

@main_bp.route('/login')
def login():
    return render_template('login.html')

# --- ROTAS POST (AÇÃO) ---

@main_bp.route('/shopping/add', methods=['POST'])
@login_required
def add_shopping_item():
    """
    Adiciona item via IA (Mesmo fluxo do Telegram).
    Monta uma frase "Comprar {qty} {nome}" e manda para o Gemini.
    """
    data = request.get_json()
    nome_input = data.get('nome', '').strip()
    
    try:
        qty_input = int(data.get('quantidade', 1))
        if qty_input < 1: qty_input = 1
    except:
        qty_input = 1
    
    if not nome_input:
        return jsonify({'error': 'Nome é obrigatório'}), 400

    try:
        # 1. TRUQUE: Monta uma frase natural para a IA
        # Ex: "Comprar 2 Leite"
        frase_ia = f"Comprar {qty_input} {nome_input}"
        
        # 2. Chama o Serviço de IA
        ai = AIAssistant()
        resultado = ai.process_intention(frase_ia, current_user.username)
        
        if not resultado or 'shopping' not in resultado or not resultado['shopping']:
            # Fallback se a IA falhar: Salva como OUTROS/Caixa
            logger.warning("IA falhou ou não identificou compra. Usando fallback.")
            return _fallback_add_item(nome_input, qty_input)

        # 3. Processa o retorno da IA (Geralmente vem 1 item, mas o loop garante)
        msg_final = ""
        for item_ia in resultado['shopping']:
            nome_ia = item_ia.get('nome', nome_input).strip()
            emoji_ia = item_ia.get('emoji', '📦')
            cat_raw = item_ia.get('cat', 'OUTROS').upper()
            qty_ia = int(item_ia.get('qty', qty_input))

            # Normalização de Categoria
            mapa_cats = {
                'FRUTAS': 'HORTIFRÚTI', 'LEGUMES': 'HORTIFRÚTI', 
                'LIMPEZA': 'LIMPEZA', 'CARNE': 'CARNES', 
                'PADARIA': 'PADARIA', 'BEBIDAS': 'BEBIDAS'
            }
            cat_nome = mapa_cats.get(cat_raw, cat_raw)

            # --- Lógica de Banco (Igual ao Webhook) ---
            
            # Categoria
            categoria = Categoria.query.filter_by(nome=cat_nome).first()
            if not categoria:
                categoria = Categoria(nome=cat_nome)
                db.session.add(categoria)
                db.session.flush()

            # Produto (Atualiza emoji se já existir mas estiver genérico)
            produto = Produto.query.filter_by(nome=nome_ia).first()
            if not produto:
                produto = Produto(nome=nome_ia, categoria_id=categoria.id, emoji=emoji_ia)
                db.session.add(produto)
            else:
                # Se o produto existe mas o emoji era a caixa, atualiza para o novo da IA
                if produto.emoji == '📦' and emoji_ia != '📦':
                    produto.emoji = emoji_ia
            
            db.session.flush()

            # Lista
            item_lista = ListaItem.query.filter_by(
                produto_id=produto.id, 
                usuario=current_user.username
            ).filter(ListaItem.status.in_(['pendente', 'comprado'])).first()

            if item_lista:
                item_lista.quantidade = qty_ia
                if item_lista.status == 'comprado':
                    item_lista.status = 'pendente'
                    msg_final = f"Reativado: {qty_ia}x {nome_ia} {emoji_ia}"
                else:
                    msg_final = f"Atualizado: {qty_ia}x {nome_ia} {emoji_ia}"
            else:
                db.session.add(ListaItem(produto_id=produto.id, quantidade=qty_ia, usuario=current_user.username))
                msg_final = f"Adicionado: {qty_ia}x {nome_ia} {emoji_ia}"

        db.session.commit()
        return jsonify({'message': msg_final, 'status': 'success'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def _fallback_add_item(nome, qty):
    """Lógica antiga de 'burro' caso a IA esteja offline"""
    # ... (Pode copiar sua lógica antiga aqui se quiser segurança, 
    # ou apenas retornar erro. Vou simplificar criando básico)
    cat = Categoria.query.filter_by(nome='OUTROS').first()
    if not cat: 
        cat = Categoria(nome='OUTROS')
        db.session.add(cat)
    
    prod = Produto.query.filter_by(nome=nome).first()
    if not prod:
        prod = Produto(nome=nome, categoria_id=cat.id, emoji='📦')
        db.session.add(prod)
    
    db.session.add(ListaItem(produto_id=prod.id, quantidade=qty, usuario=current_user.username))
    db.session.commit()
    return jsonify({'message': f"Adicionado (Offline): {nome}", 'status': 'success'})

@main_bp.route('/update_item', methods=['POST'])
@login_required
def update_item():
    data = request.get_json()
    item_id = data.get('id')
    nome = data.get('nome')
    
    try:
        qty = int(data.get('quantidade', 1))
        if qty < 1: qty = 1
    except:
        qty = 1

    item = ListaItem.query.get(item_id)
    if not item: return jsonify({'error': 'Item não encontrado'}), 404

    try:
        # Renomear
        if nome and nome != item.produto.nome:
            prod_existente = Produto.query.filter_by(nome=nome).first()
            if prod_existente:
                item.produto = prod_existente
            else:
                item.produto.nome = nome
        
        # Atualiza Quantidade (Forçando Inteiro)
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
    ListaItem.query.filter_by(status='comprado').update({'status': 'arquivado'})
    db.session.commit()
    return jsonify({'success': True})