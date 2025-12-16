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

# Import do Serviço de Chat (ajustado para nova pasta)
try:
    from app.services.chat_processor import ChatProcessor
except ImportError:
    # Fallback caso o arquivo não tenha sido movido ainda
    print("⚠️ AVISO: chat_processor não encontrado em app.services. Tentando raiz...")
    try:
        from chat_processor import ChatProcessor
    except:
        ChatProcessor = None
        print("❌ ERRO CRÍTICO: ChatProcessor não encontrado.")

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

# --- INICIALIZAÇÃO DA IA (Singleton simples) ---
llm_model = ChatOpenAI(model="gpt-4o", temperature=0.2)
chat_brain = ChatProcessor(llm_model) if ChatProcessor else None

# --- ROTAS ---

@webhook_bp.route('/voice/process', methods=['POST'])
def voice_process():
    d = request.get_json()
    if not d: return jsonify({'erro': 'JSON invalido'}), 400
    
    texto_entrada = d.get('texto', '')
    usuario = d.get('usuario', 'Casal') 

    if not texto_entrada:
        return jsonify({'erro': 'Texto vazio'}), 400

    agora = datetime.datetime.now()
    str_agora = agora.strftime("%Y-%m-%d %H:%M Semana: %A")
    data_hoje_iso = agora.strftime("%Y-%m-%d")

    dados = {}

    # --- 1. Configuração da IA ---
    try:
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.0, 
            max_retries=0,
            timeout=10
        )
        
        template_str = """
        Você é o FamilyOS, um assistente doméstico inteligente que gerencia tarefas, compras e lembretes.

        CONTEXTO:
        - Data: {data_atual}
        - Remetente: {usuario}
        - Regras de Atribuição:
        1. Se a mensagem CONTÉM nome próprio (ex: "Débora", "Thiago") -> Responsável é a pessoa mencionada
        2. Se a mensagem CONTÉM "nós", "a gente", "casal", "ambos" -> Responsável é "Casal"
        3. Se a mensagem CONTÉM "eu", "me", "mim" -> Responsável é o remetente ({usuario})
        4. Caso padrão -> Responsável é o remetente ({usuario})

        OBJETIVO: Analisar o texto e extrair informações estruturadas em JSON.

        INSTRUÇÕES DETALHADAS:

        1. SHOPPING (Lista de Compras):
        - Categorias devem estar em MAIÚSCULAS: PADARIA, HORTIFRUTI, CARNES, LATICINIOS, LIMPEZA, HIGIENE, BEBIDAS, OUTROS
        - Cada item deve ter: nome (string), cat (categoria), qty (número, padrão: 1), emoji (opcional)

        2. TASKS (Tarefas):
        - Identificar ações que precisam ser feitas (verbos de ação: fazer, lavar, comprar, buscar, etc.)
        - Prioridade (prio): 1=Alta, 2=Média, 3=Baixa. Use contexto para determinar.
        - RESPONSÁVEL (resp): Aplicar regras de atribuição acima. Capitalizar nome ("Débora", "Thiago", "Casal")
        - Cada tarefa: desc (string), resp (string), prio (1-3)

        3. REMINDERS (Lembretes):
        - Identificar eventos com data/hora específica
        - Se mencionar hora mas não data -> assumir HOJE ({data_hoje_iso})
        - Formato date: "YYYY-MM-DD", time: "HH:MM"
        - Cada lembrete: title (string), date (string opcional), time (string opcional), notes (string opcional)

        SAÍDA ESTRITA:
        - Apenas JSON válido
        - Sem explicações, sem markdown
        - Arrays vazios se não houver elementos

        EXEMPLOS DE ATRIBUIÇÃO:
        - "Débora, buscar a Catharina na escola" → resp: "Débora"
        - "Thiago precisa lavar o carro" → resp: "Thiago"
        - "Nós precisamos organizar a garagem" → resp: "Casal"
        - "Comprar leite" → resp: "{usuario}" (remetente padrão)

        TEXTO PARA ANALISAR: "{texto}"

        SAÍDA JSON:
        """

        prompt = ChatPromptTemplate.from_template(template_str)
        chain = prompt | model
        
        logger.info(f"🤖 Enviando para IA: {texto_entrada[:50]}...")
        
        # --- CORREÇÃO DO ERRO DE VARIÁVEIS ---
        res = chain.invoke({
            "data_atual": str_agora,
            "data_hoje_iso": data_hoje_iso, # <--- ESSENCIAL
            "texto": texto_entrada,
            "usuario": usuario 
        })
        
        raw_content = res.content
        logger.info(f"🤖 Resposta Bruta IA: {raw_content}")

        # --- PARSER ---
        clean_json = re.sub(r'```json|```', '', raw_content).strip()
        
        if not clean_json.startswith('{'):
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match: clean_json = match.group(0)
        
        try:
            dados_raw = json.loads(clean_json)
        except json.JSONDecodeError as e_json:
            logger.error(f"❌ Erro JSON Decode: {e_json} | Conteúdo: {clean_json}")
            return jsonify({'erro': 'IA retornou formato inválido'}), 500

        dados = {k.lower(): v for k, v in dados_raw.items()}

    except Exception as e:
        logger.error(f"⚠️ Erro Crítico IA: {traceback.format_exc()}")
        return jsonify({'erro': f'Falha processamento IA: {str(e)}'}), 500

    # --- 2. EXECUÇÃO ---
    logs_acao = []
    webhook_create_url = os.getenv('N8N_WEBHOOK_TASKS', '').strip()
    
    # Log para validar se a variável de ambiente existe
    if not webhook_create_url:
        logger.warning("⚠️ [ENV] N8N_WEBHOOK_TASKS não está definida ou está vazia!")

    try:
        # A. SHOPPING
        for item in dados.get('shopping', []):
            nome = item.get('nome', '').lower().strip()
            if not nome: continue 
            
            cat_raw = item.get('cat', 'OUTROS').upper()
            mapa_cats = {'FRUTAS': 'HORTIFRÚTI', 'LEGUMES': 'HORTIFRÚTI', 'LIMPEZA': 'LIMPEZA', 'CARNE': 'CARNES'}
            cat_nome = mapa_cats.get(cat_raw, cat_raw)

            cat = Categoria.query.filter_by(nome=cat_nome).first()
            if not cat: cat = Categoria(nome=cat_nome); db.session.add(cat); db.session.flush()
            
            prod = Produto.query.filter_by(nome=nome).first()
            if not prod:
                prod = Produto(nome=nome, categoria_id=cat.id, emoji=item.get('emoji', '📦'))
                db.session.add(prod); db.session.flush()
            
            existe = ListaItem.query.filter(ListaItem.produto_id == prod.id, ListaItem.status.in_(['pendente', 'comprado'])).first()
            if not existe:
                db.session.add(ListaItem(produto_id=prod.id, quantidade=item.get('qty', 1), usuario=usuario, origem_input="omniscient"))
                logs_acao.append(f"🛒 Add: {nome}")
            else:
                logs_acao.append(f"⚠️ Já existe: {nome}")

        # B. TASKS
        for task in dados.get('tasks', []):
            desc = task.get('desc', '').strip()
            if not desc: continue 
            
            resp_raw = task.get('resp', usuario).capitalize()
            # Normalização de Nomes
            r_low = resp_raw.lower()
            if 'debora' in r_low or 'débora' in r_low or 'ela' in r_low: resp = 'Debora'
            elif 'thiago' in r_low or 'ele' in r_low: resp = 'Thiago'
            elif 'casal' in r_low or 'nos' in r_low or 'nós' in r_low: resp = 'Casal'
            else: resp = resp_raw

            try: prio = int(task.get('prio', 1))
            except: prio = 1

            existe = Task.query.filter_by(descricao=desc, responsavel=resp, status='pendente').first()
            if not existe:
                db.session.add(Task(descricao=desc, responsavel=resp, prioridade=prio))
                logs_acao.append(f"✅ Task ({resp}): {desc}")

        # C. REMINDERS (AQUI ESTÁ O FOCO DO DEBUG)
        for rem in dados.get('reminders', []):
            title = rem.get('title', '').strip()
            if not title: continue 
            date_str = rem.get('date', data_hoje_iso)
            time_str = rem.get('time')
            
            if date_str:
                try:
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    if time_str:
                        tm = datetime.datetime.strptime(time_str, "%H:%M").time()
                        full_dt = datetime.datetime.combine(dt, tm)
                        iso_google = full_dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')
                    else:
                        full_dt = datetime.datetime.combine(dt, datetime.time.min)
                        iso_google = full_dt.strftime('%Y-%m-%dT00:00:00-03:00')

                    novo_rem = Reminder(title=title, notes=rem.get('notes',''), due_date=full_dt, status='needsAction', usuario=usuario)
                    db.session.add(novo_rem); db.session.flush()
                    logs_acao.append(f"🔔 Reminder: {title}")

                    # --- DEBUG N8N ---
                    if webhook_create_url:
                        payload = {"action": "create", "local_id": novo_rem.id, "title": title, "due": iso_google}
                        logger.info(f"🚀 [CREATE] Enviando para N8N: {webhook_create_url} | Payload: {payload}")
                        try:
                            resp = requests.post(webhook_create_url, json=payload, timeout=5)
                            logger.info(f"📬 [CREATE] Resposta N8N: {resp.status_code} - {resp.text}")
                        except Exception as e_req:
                             logger.error(f"❌ [CREATE] Erro conexao N8N: {e_req}")
                    else:
                        logger.warning("⚠️ [CREATE] Ignorado pois N8N_WEBHOOK_TASKS está vazio.")

                except Exception as e:
                    logger.error(f"❌ Erro date reminder: {e}")

        db.session.commit()
        msg_final = "\n".join(logs_acao) if logs_acao else "Sem ações identificadas."
        return jsonify({'message': msg_final}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro Geral Banco: {traceback.format_exc()}")
        return jsonify({'erro': str(e)}), 500

@webhook_bp.route('/reminders/sync', methods=['POST'])
def sync_reminders():
    # ... (código existente mantido igual) ...
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
    # ... (código existente mantido igual) ...
    try:
        if not chat_brain: return jsonify({'response': "Erro: Cérebro do Chat não carregado."}), 500
        data = request.json
        user_message = data.get('message', '')
        user_name = data.get('usuario', 'Thiago')
        response_data = chat_brain.process_message(user_message, user_name)
        if isinstance(response_data, str):
            return jsonify({'response': response_data})
        return jsonify({'response': response_data})
    except Exception as e:
        return jsonify({'response': "Erro interno no Chat."}), 500