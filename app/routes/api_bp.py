import os
import datetime
import requests
import traceback
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.shopping import ListaItem, Categoria, Produto
from app.models.tasks import Task, Reminder

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# --- SHOPPING API ---

@api_bp.route('/toggle_item/<int:id>', methods=['POST'])
@login_required
def toggle_item(id):
    i = db.session.get(ListaItem, id)
    if i:
        i.status = 'comprado' if i.status == 'pendente' else 'pendente'
        db.session.commit()
        return jsonify({'status': 'success', 'novo_status': i.status})
    return jsonify({'status': 'error'}), 404

@api_bp.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    db.session.query(ListaItem).filter(ListaItem.status=='comprado').update({'status': 'finalizado'})
    db.session.commit()
    return jsonify({'status': 'success'})

@api_bp.route('/update_item', methods=['POST'])
@login_required
def update_item():
    d = request.get_json()
    i = db.session.get(ListaItem, int(d.get('id')))
    if not i: return jsonify({'error': '404'}), 404
    
    cat_nome = d.get('categoria').upper().strip()
    prod_nome = d.get('nome').lower().strip()
    
    cat = Categoria.query.filter_by(nome=cat_nome).first()
    if not cat: 
        cat = Categoria(nome=cat_nome)
        db.session.add(cat)
        db.session.flush()
        
    prod = Produto.query.filter_by(nome=prod_nome).first()
    if not prod:
        prod = Produto(nome=prod_nome, categoria_id=cat.id, emoji=i.produto.emoji, unidade_padrao_id=i.produto.unidade_padrao_id)
        db.session.add(prod)
        db.session.flush()
    else: 
        prod.categoria_id = cat.id
        
    i.produto_id = prod.id
    db.session.commit()
    return jsonify({'message': 'OK'})

# --- TASKS API ---

@api_bp.route('/toggle_task/<int:id>', methods=['POST'])
@login_required
def toggle_task(id):
    t = db.session.get(Task, id)
    if t:
        t.status = 'concluido' if t.status == 'pendente' else 'pendente'
        db.session.commit()
        return jsonify({'status': 'success', 'novo_status': t.status})
    return jsonify({'status': 'error'}), 404

@api_bp.route('/clear_tasks', methods=['POST'])
@login_required
def clear_tasks():
    db.session.query(Task).filter(Task.status=='concluido').update({'status': 'arquivado'})
    db.session.commit()
    return jsonify({'status': 'success'})

@api_bp.route('/tasks/update', methods=['POST'])
@login_required
def update_task():
    d = request.get_json()
    task = db.session.get(Task, int(d.get('id')))
    if not task: return jsonify({'error': 'Tarefa não encontrada'}), 404

    task.descricao = d.get('descricao')
    task.responsavel = d.get('responsavel')
    task.prioridade = int(d.get('prioridade'))
    db.session.commit()
    return jsonify({'status': 'success'})

# --- REMINDERS API (COM LOGS DE DEBUG) ---

@api_bp.route('/reminders/update', methods=['POST'])
@login_required
def update_reminder():
    d = request.get_json()
    rem_id = int(d.get('id'))
    reminder = db.session.get(Reminder, rem_id)
    if not reminder: return jsonify({'error': 'Lembrete não encontrado'}), 404
    
    reminder.title = d.get('title')
    reminder.notes = d.get('notes')
    
    date_str = d.get('date')
    time_str = d.get('time')
    iso_date_for_google = None 
    
    if date_str:
        if time_str:
            iso_str = f"{date_str}T{time_str}:00"
            iso_date_for_google = f"{date_str}T{time_str}:00.000Z"
        else:
            iso_str = f"{date_str}T00:00:00"
            iso_date_for_google = f"{date_str}T00:00:00.000Z"
        try:
            reminder.due_date = datetime.datetime.fromisoformat(iso_str)
        except: pass

    db.session.commit()
    
    # Dispara N8N (Update)
    try:
        webhook_url = os.getenv('N8N_WEBHOOK_TASKS')
        if webhook_url and (reminder.google_id or reminder.calendar_id):
            payload = {
                "action": "update",
                "local_id": reminder.id,
                "google_id": reminder.google_id,
                "calendar_id": reminder.calendar_id,
                "title": reminder.title,
                "notes": reminder.notes
            }
            if iso_date_for_google: payload["due"] = iso_date_for_google
            
            logger.info(f"🚀 [UPDATE] Enviando para N8N: {webhook_url} | Payload: {payload}")
            resp = requests.post(webhook_url, json=payload, timeout=5)
            logger.info(f"📬 [UPDATE] Resposta N8N: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        logger.error(f"❌ [UPDATE] Erro N8N: {e}")

    return jsonify({'status': 'success'})

@api_bp.route('/reminders/create', methods=['POST'])
def create_reminder():
    d = request.get_json()
    if not d: return jsonify({'erro': 'JSON invalido'}), 400

    title = d.get('title')
    notes = d.get('notes', '')
    date_str = d.get('date')
    time_str = d.get('time')
    
    dt_final = None
    iso_google = None
    
    if date_str:
        try:
            if time_str:
                dt_final = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
                iso_google = f"{date_str}T{time_str}:00.000Z"
            else:
                dt_final = datetime.datetime.fromisoformat(f"{date_str}T00:00:00")
                iso_google = f"{date_str}T00:00:00.000Z"
        except ValueError: pass

    try:
        # 1. Cria Localmente
        novo_lembrete = Reminder(
            title=title, notes=notes, due_date=dt_final,
            status='needsAction', usuario=d.get('usuario', 'API')
        )
        db.session.add(novo_lembrete)
        db.session.commit()

        # 2. Chama N8N
        webhook_url = os.getenv('N8N_WEBHOOK_TASKS') 
        if webhook_url:
            payload = {
                "action": "create", "local_id": novo_lembrete.id,
                "title": title, "notes": notes, "due": iso_google
            }
            try: 
                logger.info(f"🚀 [CREATE] Enviando para N8N: {webhook_url}")
                resp = requests.post(webhook_url, json=payload, timeout=5)
                logger.info(f"📬 [CREATE] Resposta N8N: {resp.status_code} - {resp.text}")
            except Exception as e_req: 
                 logger.error(f"❌ [CREATE] Falha Request N8N: {e_req}")

        return jsonify({'status': 'success', 'id': novo_lembrete.id, 'message': f'Lembrete "{title}" criado.'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/reminders/trigger', methods=['POST'])
@login_required
def trigger_manual_sync():
    """Rota chamada pelo Botão 'Sincronizar' do Frontend"""
    webhook_url = os.getenv('N8N_WEBHOOK_REMINDERS')
    
    if not webhook_url: 
        logger.error("❌ [TRIGGER] Erro: Var N8N_WEBHOOK_REMINDERS não definida")
        return jsonify({"status": "error", "message": "Sem config N8N"}), 500

    try:
        payload = {"trigger": "manual_button", "requested_by": current_user.username}
        logger.info(f"🚀 [TRIGGER] Solicitando Sync manual para: {webhook_url}")
        
        # Timeout curto (2s) porque não precisamos esperar o N8N terminar
        try: 
            requests.post(webhook_url, json=payload, timeout=2)
            logger.info("✅ [TRIGGER] Solicitação enviada com sucesso (Fire & Forget)")
        except requests.exceptions.ReadTimeout:
            logger.info("✅ [TRIGGER] Enviado (Timeout esperado)")
        except Exception as req_err:
            logger.error(f"⚠️ [TRIGGER] Erro de conexão: {req_err}")

        return jsonify({"status": "success", "message": "Sync solicitado!"}), 200
    except Exception as e:
        logger.error(f"❌ [TRIGGER] Erro crítico: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500