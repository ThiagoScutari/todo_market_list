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
    cidade = "Itajai,SC"
    agora = datetime.datetime.utcnow()
    
    # 1. Cache Local
    cache = db.session.query(WeatherCache).first()
    if cache and cache.last_updated and (agora - cache.last_updated).total_seconds() < 3600:
        try: return json.loads(cache.data_json)
        except: pass

    # 2. API Externa
    chave = os.getenv('HGBRASIL_KEY')
    if not chave: return None

    try:
        url = f"https://api.hgbrasil.com/weather?key={chave}&city_name={cidade}"
        response = requests.get(url)
        dados = response.json()
        
        if not cache:
            cache = WeatherCache(city=cidade)
            db.session.add(cache)
        
        cache.data_json = json.dumps(dados)
        cache.last_updated = agora
        db.session.commit()
        return dados
    except Exception as e:
        print(f"Erro API Clima: {e}")
        return None

# --- ROTAS ---

@main_bp.route('/')
@login_required
def dashboard():
    qtd_compras = ListaItem.query.filter_by(status='pendente').count()
    qtd_tarefas = Task.query.filter_by(status='pendente').count()
    qtd_lembretes = Reminder.query.filter_by(status='needsAction').count()

    # Clima
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

    return render_template('dashboard.html',
                           active_page='dashboard',
                           qtd_compras=qtd_compras,
                           qtd_tarefas=qtd_tarefas,
                           qtd_lembretes=qtd_lembretes,
                           clima=clima,
                           forecast=forecast,
                           mensagem=get_daily_quote())

@main_bp.route('/shopping')
@login_required
def shopping_list():
    itens = ListaItem.query.options(
        joinedload(ListaItem.produto).joinedload(Produto.categoria), 
        joinedload(ListaItem.unidade)
    ).filter(or_(ListaItem.status == 'pendente', ListaItem.status == 'comprado')) \
     .order_by(ListaItem.adicionado_em.desc()).all()

    view = {}
    for i in itens:
        c = i.produto.categoria.nome if i.produto.categoria else "OUTROS"
        if c not in view: view[c] = []
        qtd = int(i.quantidade) if i.quantidade % 1 == 0 else i.quantidade
        und = i.unidade.simbolo if i.unidade else ""
        view[c].append({
            'id': i.id, 
            'nome': i.produto.nome.title(), 
            'emoji': i.produto.emoji, 
            'detalhes': f"{qtd}{und}", 
            'usuario': i.usuario, 
            'status': i.status
        })
    return render_template('shopping.html', categorias=view, active_page='shopping')

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
        or_(Reminder.status == 'needsAction', Reminder.status.is_(None))
    ).order_by(Reminder.due_date.asc().nulls_last()).all()

    return render_template('reminders.html', tasks=tasks, active_page='reminders')

@main_bp.route('/chat')
def chat_page():
    return render_template('chat.html')