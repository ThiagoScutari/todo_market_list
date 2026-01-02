import os
import re
import json
import logging
import datetime
import traceback
import requests
from flask import Blueprint, jsonify, request
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Imports internos
from app.extensions import db
from app.models.shopping import ListaItem, Categoria, Produto
from app.models.tasks import Task, Reminder

# --- CONFIGURAÇÃO DE LOGS ---
logger = logging.getLogger(__name__)
webhook_bp = Blueprint('webhook', __name__)

# --- CONFIGURAÇÃO DA IA ---
# Instancia aqui para evitar recriação a cada request (Singleton pattern simples)
try:
    llm_gemini = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0.0, 
        max_retries=2, 
        timeout=15     
    )
    logger.info("✅ Google Gemini inicializado para Webhook.")
except Exception as e:
    logger.error(f"❌ Erro ao instanciar Gemini: {e}")
    llm_gemini = None

# --- ROTAS ---

@webhook_bp.route('/voice/process', methods=['POST'])
def voice_process():
    d = request.get_json()
    if not d: return jsonify({'erro': 'JSON invalido'}), 400
    
    texto_entrada = d.get('texto', '')
    usuario = d.get('usuario', 'Casal') 

    if not texto_entrada: return jsonify({'erro': 'Texto vazio'}), 400
    if not llm_gemini: return jsonify({'erro': 'IA indisponível'}), 503

    # Variáveis de Tempo
    agora = datetime.datetime.now()
    str_agora = agora.strftime("%Y-%m-%d %H:%M Semana: %A")
    data_hoje_iso = agora.strftime("%Y-%m-%d")

    try:
        # 1. INTELIGÊNCIA: Extração de Dados
        dados_json = _call_ai_extraction(texto_entrada, usuario, str_agora, data_hoje_iso)
        
        # 2. ROTEAMENTO E EXECUÇÃO (Dividir e Conquistar)
        logs_acao = []
        
        # Módulo Shopping
        if 'shopping' in dados_json and dados_json['shopping']:
            logs_acao.extend(_handle_shopping(dados_json['shopping'], usuario))
            
        # Módulo Tasks
        if 'tasks' in dados_json and dados_json['tasks']:
            logs_acao.extend(_handle_tasks(dados_json['tasks'], usuario))
            
        # Módulo Reminders
        if 'reminders' in dados_json and dados_json['reminders']:
            logs_acao.extend(_handle_reminders(dados_json['reminders'], usuario, data_hoje_iso))

        # Commit final único
        db.session.commit()
        
        msg_final = "\n".join(logs_acao) if logs_acao else "Nenhuma ação identificada."
        return jsonify({'message': msg_final}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"⚠️ Erro Crítico Processamento: {traceback.format_exc()}")
        return jsonify({'erro': f'Falha no processamento: {str(e)}'}), 500

# --- FUNÇÕES AUXILIARES (Private Methods) ---

def _call_ai_extraction(texto, usuario, str_agora, data_hoje_iso):
    """Encapsula a lógica de prompt e chamada ao Gemini"""
    
    template_str = """
    Você é o cérebro do FamilyOS. Sua função é classificar e estruturar intenções.

    CONTEXTO:
    - Data Atual: {data_atual}
    - Usuário Remetente: {usuario}

    🚨 REGRAS DE DESAMBIGUAÇÃO (SHOPPING vs TASKS):
    1. O verbo "Comprar" seguido de itens de supermercado (pão, leite, carne, detergente) -> DEVE ir para 'SHOPPING'.
    2. O verbo "Comprar" seguido de bens duráveis ou genéricos (TV, presente, carro) -> DEVE ir para 'TASKS'.
    3. Itens soltos sem verbo (ex: "Tomate, Alface") -> Assumir 'SHOPPING'.

    REGRAS DE ATRIBUIÇÃO (Quem fará?):
    1. Nome citado explicitamente ("Débora, ...") -> Débora.
    2. Contexto "Nós/Casal" -> Casal.
    3. Padrão -> O remetente ({usuario}).

    ESTRUTURA DE SAÍDA (JSON):
    {{
        "shopping": [ {{ "nome": "Leite", "cat": "LATICINIOS", "qty": 2 }} ],
        "tasks": [ {{ "desc": "Comprar presente da mãe", "resp": "Thiago", "prio": 2 }} ],
        "reminders": [ {{ "title": "Médico", "date": "YYYY-MM-DD", "time": "HH:MM" }} ]
    }}

    ENTRADA DO USUÁRIO: "{texto}"
    
    Responda APENAS o JSON válido.
    """
    
    prompt = ChatPromptTemplate.from_template(template_str)
    chain = prompt | llm_gemini
    
    logger.info(f"🤖 [IA] Processando: {texto[:50]}...")
    res = chain.invoke({
        "data_atual": str_agora,
        "texto": texto,
        "usuario": usuario
    })
    
    # Limpeza do JSON
    clean_json = re.sub(r'```json|```', '', res.content).strip()
    if not clean_json.startswith('{'):
        match = re.search(r'\{.*\}', clean_json, re.DOTALL)
        if match: clean_json = match.group(0)
        
    return json.loads(clean_json)

def _handle_shopping(itens, usuario):
    logs = []
    for item in itens:
        nome = item.get('nome', '').strip()
        if not nome: continue
        
        # Normalização de categoria
        cat_raw = item.get('cat', 'OUTROS').upper()
        mapa_cats = {'FRUTAS': 'HORTIFRÚTI', 'LEGUMES': 'HORTIFRÚTI', 'LIMPEZA': 'LIMPEZA', 'CARNE': 'CARNES', 'PADARIA': 'PADARIA'}
        cat_nome = mapa_cats.get(cat_raw, cat_raw)

        # Lógica de Banco (Find or Create)
        cat = Categoria.query.filter_by(nome=cat_nome).first()
        if not cat: 
            cat = Categoria(nome=cat_nome)
            db.session.add(cat)
            db.session.flush()
        
        prod = Produto.query.filter_by(nome=nome).first()
        if not prod:
            prod = Produto(nome=nome, categoria_id=cat.id, emoji=item.get('emoji', '📦'))
            db.session.add(prod)
            db.session.flush()
        
        # Verifica duplicidade na lista ativa
        existe = ListaItem.query.filter(
            ListaItem.produto_id == prod.id, 
            ListaItem.status.in_(['pendente', 'comprado'])
        ).first()
        
        if not existe:
            # Add com origem "voice_ia"
            db.session.add(ListaItem(produto_id=prod.id, quantidade=item.get('qty', 1), usuario=usuario, origem_input="voice_ia"))
            logs.append(f"🛒 Add: {nome}")
        else:
            logs.append(f"⚠️ Já na lista: {nome}")
    return logs

def _handle_tasks(tasks, usuario):
    logs = []
    for task in tasks:
        desc = task.get('desc', '').strip()
        if not desc: continue
        
        # Normalização Responsável
        resp_raw = task.get('resp', usuario).capitalize()
        if any(x in resp_raw.lower() for x in ['debora', 'débora', 'ela']): resp = 'Debora'
        elif any(x in resp_raw.lower() for x in ['thiago', 'ele']): resp = 'Thiago'
        elif any(x in resp_raw.lower() for x in ['casal', 'nos', 'nós']): resp = 'Casal'
        else: resp = resp_raw

        try: prio = int(task.get('prio', 1))
        except: prio = 1

        existe = Task.query.filter_by(descricao=desc, responsavel=resp, status='pendente').first()
        if not existe:
            db.session.add(Task(descricao=desc, responsavel=resp, prioridade=prio))
            logs.append(f"✅ Task ({resp}): {desc}")
    return logs

def _handle_reminders(reminders, usuario, data_hoje_iso):
    logs = []
    webhook_create_url = os.getenv('N8N_WEBHOOK_TASKS', '').strip()
    
    for rem in reminders:
        title = rem.get('title', '').strip()
        if not title: continue
        
        date_str = rem.get('date', data_hoje_iso)
        time_str = rem.get('time')
        
        try:
            # Lógica de Data/Hora para Google Calendar format
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if time_str:
                tm = datetime.datetime.strptime(time_str, "%H:%M").time()
                full_dt = datetime.datetime.combine(dt, tm)
                iso_google = full_dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')
            else:
                full_dt = datetime.datetime.combine(dt, datetime.time.min)
                iso_google = full_dt.strftime('%Y-%m-%dT00:00:00-03:00')

            novo_rem = Reminder(title=title, notes=rem.get('notes',''), due_date=full_dt, status='needsAction', usuario=usuario)
            db.session.add(novo_rem)
            db.session.flush() # Necessário para gerar o ID
            logs.append(f"🔔 Reminder: {title}")

            # Disparo Assíncrono para N8N (Idealmente mover para Celery/Queue no futuro)
            if webhook_create_url:
                payload = {"action": "create", "local_id": novo_rem.id, "title": title, "due": iso_google}
                try:
                    requests.post(webhook_create_url, json=payload, timeout=2) # Timeout baixo para não travar request
                except Exception as e_req:
                    logger.error(f"❌ Falha envio N8N: {e_req}")

        except Exception as e:
            logger.error(f"❌ Erro processando data reminder: {e}")
            
    return logs

@webhook_bp.route('/reminders/sync', methods=['POST'])
def sync_reminders():
    # ... Lógica de sync mantida ...
    raw_data = request.get_json()
    tasks_final = []
    raw_list = [raw_data] if isinstance(raw_data, dict) else (raw_data if isinstance(raw_data, list) else [])
    for item in raw_list:
        if isinstance(item, dict):
            if 'dados_agrupados' in item and isinstance(item['dados_agrupados'], list):
                tasks_final.extend(item['dados_agrupados'])
            else:
                tasks_final.append(item)

    criado, atualizado, deletado = 0, 0, 0
    try:
        for item in tasks_final:
            if not isinstance(item, dict): continue
            gid = item.get('google_id') or item.get('id')
            if not gid: continue

            lembrete = Reminder.query.filter_by(google_id=gid).first()
            should_delete = str(item.get('deleted')).lower() == 'true'

            if should_delete:
                if lembrete: db.session.delete(lembrete); deletado += 1
                continue

            if not lembrete:
                lembrete = Reminder(google_id=gid); db.session.add(lembrete); criado += 1
            else:
                atualizado += 1

            lembrete.title = item.get('title', 'Sem Título')
            lembrete.notes = item.get('notes')
            lembrete.status = item.get('status')
            lembrete.parent_id = item.get('parent')
            
            due_str = item.get('due')
            if due_str:
                try: lembrete.due_date = datetime.datetime.fromisoformat(due_str.replace('Z', ''))
                except: pass
            
            lembrete.last_updated = datetime.datetime.utcnow()

        db.session.commit()
        return jsonify({"status": "success", "c": criado, "u": atualizado, "d": deletado}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500

@webhook_bp.route('/chat/message', methods=['POST'])
def chat_message():
    try:
        if not chat_brain: return jsonify({'response': "Erro: Cérebro do Chat não carregado (Ver logs)."}), 500
        data = request.json
        user_message = data.get('message', '')
        user_name = data.get('usuario', 'Thiago')
        response_data = chat_brain.process_message(user_message, user_name)
        if isinstance(response_data, str):
            return jsonify({'response': response_data})
        return jsonify({'response': response_data})
    except Exception as e:
        return jsonify({'response': "Erro interno no Chat."}), 500