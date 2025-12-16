import sqlite3
import os
import sys
import datetime
import glob
from dotenv import load_dotenv

# --- IMPORTS LANGCHAIN & OPENAI ---
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.callbacks import StdOutCallbackHandler

# --- 1. CONFIGURAÇÃO DE DIRETÓRIOS (NOVA ARQUITETURA) ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # Raiz do Projeto
DATA_DIR = os.path.join(BASE_DIR, "data")            # Persistência
DOCS_DIR = os.path.join(BASE_DIR, "docs")            # Documentação
CODIGO_DIR = os.path.join(BASE_DIR, "codigo_gerado") # Saída da IA
APP_DIR = os.path.join(BASE_DIR, "app")              # Código Fonte Principal

# Garante que as pastas existem
for path in [DATA_DIR, DOCS_DIR, CODIGO_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# --- IMPORTS ADAPTADOS (APP.SERVICES) ---
# Adiciona o diretório atual ao path para garantir que 'app' seja importável
sys.path.append(BASE_DIR)

try:
    from app.services.ai_core.wrapper_codex import GPT5CodexResponsesWrapper
except ImportError as e:
    print(f"❌ Erro de Importação: {e}")
    print("Dica: Verifique se a pasta 'app/services/ai_core' existe e tem o __init__.py")
    sys.exit(1)

# --- IMPORT DA MEMÓRIA RAG ---
try:
    from app.services.ai_core.knowledge_base import consultar_documentacao
except ImportError:
    print("⚠️ Aviso: 'knowledge_base' não encontrado. O RAG não estará ativo.")
    @tool
    def consultar_documentacao(pergunta: str) -> str:
        """Ferramenta placeholder se o RAG falhar."""
        return "RAG indisponível."

# --- CARREGA AMBIENTE ---
try:
    load_dotenv()
except:
    pass

print(f"📚 RAG ativado: O Builder agora pode consultar vetores.")

# --- CONFIGURAÇÃO DO CHECKPOINTER (MEMÓRIA) ---
# Mudança: Salvando dentro da pasta 'data' para consistência
db_path = os.path.join(DATA_DIR, "ai_memory.sqlite")
print(f"🧠 Memória da IA: {db_path}")

conn = sqlite3.connect(db_path, check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

historico_sessao = []

def registrar_log(quem, o_que):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    texto_limpo = limpar_conteudo(o_que)
    entrada = f"[{timestamp}] {quem}: {texto_limpo}"
    historico_sessao.append(entrada)

def limpar_conteudo(conteudo):
    if isinstance(conteudo, list):
        for bloco in conteudo:
            if isinstance(bloco, dict) and 'text' in bloco:
                return bloco['text']
    return str(conteudo)

# --- 2. CONFIGURAÇÃO DOS MODELOS ---

llm_manager = ChatOpenAI(model="gpt-4o", temperature=0.5)
llm_tech = ChatOpenAI(model="gpt-4o", temperature=0.2)
llm_ux = ChatOpenAI(model="gpt-4o", temperature=0.4)
llm_scribe = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

# BUILDER (GPT-4o Stable)
llm_builder = GPT5CodexResponsesWrapper(
    reasoning_effort="high"
)

# --- 3. FERRAMENTAS (TOOLS) ---

@tool
def ler_codigo_fonte(caminho_relativo: str) -> str:
    """
    Lê o código de um arquivo no projeto.
    Exemplos de entrada: 'app/routes/main_bp.py', 'run.py', 'app/templates/dashboard.html'.
    """
    # Remove barra inicial se houver para evitar erro de join
    if caminho_relativo.startswith("/") or caminho_relativo.startswith("\\"):
        caminho_relativo = caminho_relativo[1:]
        
    caminho_completo = os.path.join(BASE_DIR, caminho_relativo)
    
    if not os.path.exists(caminho_completo): 
        return f"❌ Arquivo não encontrado: {caminho_completo}"
    try:
        with open(caminho_completo, "r", encoding="utf-8") as f: return f.read()
    except Exception as e: return f"❌ Erro de leitura: {e}"

@tool
def escrever_codigo(caminho_relativo: str, conteudo: str) -> str:
    """
    Salva código no projeto.
    Use caminhos relativos à raiz: 'app/routes/novo.py', 'codigo_gerado/teste.py'.
    """
    # Remove barra inicial
    if caminho_relativo.startswith("/") or caminho_relativo.startswith("\\"):
        caminho_relativo = caminho_relativo[1:]

    caminho_destino = os.path.join(BASE_DIR, caminho_relativo)
    pasta_destino = os.path.dirname(caminho_destino)
    
    try:
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino)
        with open(caminho_destino, "w", encoding="utf-8") as f: f.write(conteudo)
        return f"✅ Código salvo em: {caminho_relativo}"
    except Exception as e: return f"❌ Erro de escrita: {e}"

# --- 4. CRIAÇÃO DOS AGENTES ---

prompt_base = "Você faz parte do FamilyOS AI Team (v3.0 Modular Architecture)."

alpha = create_agent(
    model=llm_manager, 
    tools=[consultar_documentacao], 
    system_prompt=f"{prompt_base} Você é Alpha (PO). Use 'consultar_documentacao' para validar requisitos.", 
    checkpointer=checkpointer
)

architect = create_agent(
    model=llm_tech, 
    tools=[ler_codigo_fonte, consultar_documentacao], 
    system_prompt=f"{prompt_base} Você é Architect (Tech Lead). Valide a arquitetura modular (Blueprints, Services, Factory).", 
    checkpointer=checkpointer
)

experience = create_agent(
    model=llm_ux, 
    tools=[consultar_documentacao], 
    system_prompt=f"{prompt_base} Você é Experience (UX). Garanta que a UI siga o 'frontend_docs.md' (Cyberpunk Dark Neon).", 
    checkpointer=checkpointer
)

# --- SYSTEM PROMPT DO BUILDER ---
SYSTEM_PROMPT_CODEX = f"""
You are Codex (Builder), an expert software engineer specialized in Flask Modular Architecture.
{prompt_base}

# ARCHITECTURE CONTEXT (v3.0):
- Root: run.py, .env, docker-compose.yml
- App Package: app/ (__init__, config, extensions)
- Database: app/models/ (SQLAlchemy)
- Logic: app/routes/ (Blueprints) & app/services/
- Frontend: app/templates/ & app/static/

# CRITICAL INSTRUCTION:
You are a DOER.
- If the user asks to implement something, you MUST use the tool 'escrever_codigo'.
- Do not output only text plans. Output the CODE FILES using the tool.

# TOOL USAGE
1. **consultar_documentacao**: Search for specs.
2. **ler_codigo_fonte**: Read existing files to match style.
3. **escrever_codigo**: Write the final code.

# CONSTRAINTS
- Always implement the FULL file content when writing.
- Respect the folder structure (don't put models in routes).
"""

builder = create_agent(
    model=llm_builder, 
    tools=[escrever_codigo, ler_codigo_fonte, consultar_documentacao], 
    system_prompt=SYSTEM_PROMPT_CODEX, 
    checkpointer=checkpointer
)

star = create_agent(
    model=llm_scribe, 
    tools=[], 
    system_prompt="Você é Star. Gere a Ata da reunião resumida.", 
    checkpointer=checkpointer
)

# --- 5. FUNÇÕES DE FLUXO ---

def rodada_debate(user_input, config):
    print("\n   📢 [SISTEMA]: Debate (RAG Enabled)...")
    registrar_log("Usuario", user_input)
    
    handler = StdOutCallbackHandler()
    config_log = config.copy()
    config_log["callbacks"] = [handler]

    # 1. Alpha
    print("\n   👔 Alpha (PO)...")
    res = alpha.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config_log)
    msg_alpha = limpar_conteudo(res['messages'][-1].content)
    print(f"   💬 Alpha diz:\n{msg_alpha}\n")
    registrar_log("Alpha", msg_alpha)
    
    # 2. Architect
    print("   🏗️ Architect (Tech Lead)...")
    res = architect.invoke({"messages": [{"role": "user", "content": "Análise técnica considerando a estrutura v3.0?"}]}, config=config_log)
    msg_arch = limpar_conteudo(res['messages'][-1].content)
    print(f"   💬 Architect diz:\n{msg_arch}\n")
    registrar_log("Architect", msg_arch)

    # 3. Experience
    print("   🎨 Experience (UX/UI)...")
    res = experience.invoke({"messages": [{"role": "user", "content": "Essa solução respeita o Design System?"}]}, config=config_log)
    msg_ux = limpar_conteudo(res['messages'][-1].content)
    print(f"   💬 Experience diz:\n{msg_ux}\n")
    registrar_log("Experience", msg_ux)

    return msg_alpha

def gerar_instrucao_architect(config, feedback=None):
    print("\n   🏗️  [Architect]: Elaborando Spec Técnica...")
    handler = StdOutCallbackHandler()
    config_log = config.copy()
    config_log["callbacks"] = [handler]
    
    contexto = "Gere um PROMPT TÉCNICO para o Builder. Seja IMPERATIVO: 'Use escrever_codigo para criar o arquivo X em app/...'."
    if feedback: contexto += f" O usuário pediu ajuste: {feedback}"

    res = architect.invoke({"messages": [{"role": "user", "content": contexto}]}, config=config_log)
    msg = limpar_conteudo(res['messages'][-1].content)
    print(f"\n   📝 Spec Gerada:\n{msg}\n")
    return msg

def rodada_execucao(ordem, config):
    print("\n   🔨 [SISTEMA]: Builder Codex (Modular Arch)...")
    
    handler = StdOutCallbackHandler()
    config_log = config.copy()
    config_log["callbacks"] = [handler]
    
    ordem_refinada = f"""
    TASK: {ordem}
    ARCH: v3.0 (App Factory).
    CRITICAL: YOU MUST USE 'escrever_codigo' TO IMPLEMENT THE FILES.
    """
    
    try:
        res = builder.invoke(
            {"messages": [{"role": "user", "content": ordem_refinada}]}, 
            config=config_log
        )
        msg_builder = limpar_conteudo(res['messages'][-1].content)
        print(f"\n🤖 Builder:\n{msg_builder}")
        registrar_log("Builder", msg_builder)
    except Exception as e:
        print(f"❌ Erro: {e}")

def encerramento_inteligente(config):
    if len(historico_sessao) < 2: sys.exit(0)
    print("\n   🌟 [STAR]: Gerando Ata...")
    log = "\n".join(historico_sessao)
    res = star.invoke({"messages": [{"role": "user", "content": f"Resuma a sessão:\n{log}"}]}, config=config)
    caminho = os.path.join(DOCS_DIR, f"Ata_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.md")
    with open(caminho, "w", encoding="utf-8") as f: f.write(str(res['messages'][-1].content))
    print(f"   💾 Salvo: {caminho}")
    sys.exit(0)

# --- 6. LOOP PRINCIPAL ---
config = {"configurable": {"thread_id": "sessao_v3_modular"}}
print("\n--- 🚀 FamilyOS AI Team (v3.0 Modular) ---")
print(f"📂 Raiz: {BASE_DIR}")
print(f"🧠 Memória: {DATA_DIR}")

COMANDOS_SAIDA = ["sair", "exit", "encerrar", "quit"]

while True:
    try:
        print("\n" + "-"*60)
        user_input = input("👤 Você: ").strip()
        if not user_input: continue
        if user_input.lower() in COMANDOS_SAIDA: encerramento_inteligente(config)

        if any(user_input.lower().startswith(p) for p in ["builder", "codar", "programe"]):
            rodada_execucao(user_input, config)
        else:
            rodada_debate(user_input, config)
            acao = input("\n   👉 Acionar Builder? (s/n): ").lower()
            if acao == 's':
                instrucao = gerar_instrucao_architect(config)
                if input("   ✅ Aprovar? (s/n): ").lower() == 's':
                    rodada_execucao(instrucao, config)

    except KeyboardInterrupt: encerramento_inteligente(config)
    except Exception as e: print(f"❌ Erro Crítico: {e}")