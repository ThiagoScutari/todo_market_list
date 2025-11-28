import sqlite3
import os
import sys
import datetime
import glob
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver

# --- 1. CONFIGURAÇÃO ---
try:
    load_dotenv()
except:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Pasta src
DOCS_DIR = os.path.join(os.path.dirname(BASE_DIR), "docs")
CODIGO_DIR = os.path.join(BASE_DIR, "codigo_gerado")

for path in [DOCS_DIR, CODIGO_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# --- RAG AUTOMÁTICO (Docs) ---
def carregar_contexto_docs():
    contexto = "--- DOCUMENTAÇÃO DO PROJETO ---\n"
    arquivos_md = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    if not arquivos_md: return contexto + "Nenhum doc encontrado."
    for arquivo in arquivos_md:
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                contexto += f"\n=== {os.path.basename(arquivo)} ===\n{f.read()}\n"
        except: pass
    return contexto

CONTEXTO_PROJETO = carregar_contexto_docs()

conn = sqlite3.connect("memoria_v11_leitura.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# Modelo Lite para economizar
model = init_chat_model("gemini-2.5-flash-lite", model_provider="google_genai", temperature=0.3)

historico_sessao = []

def registrar_log(quem, o_que):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entrada = f"[{timestamp}] {quem}: {str(o_que)}"
    historico_sessao.append(entrada)

# --- 2. FERRAMENTAS ---

@tool
def ler_codigo_fonte(nome_arquivo: str) -> str:
    """
    Lê o código ATUAL de um arquivo na pasta src.
    USE ISTO ANTES DE EDITAR QUALQUER ARQUIVO.
    Exemplo: ler_codigo_fonte('app.py')
    """
    caminho = os.path.join(BASE_DIR, os.path.basename(nome_arquivo))
    if not os.path.exists(caminho):
        return f"❌ Arquivo {nome_arquivo} não encontrado em src."
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"❌ Erro ao ler: {e}"

@tool
def escrever_codigo(nome_arquivo: str, conteudo: str) -> str:
    """Salva código na pasta 'codigo_gerado'."""
    caminho = os.path.join(CODIGO_DIR, os.path.basename(nome_arquivo))
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return f"✅ Código salvo em codigo_gerado/{nome_arquivo}. O usuário deve mover para src."
    except Exception as e:
        return f"❌ Erro: {e}"

@tool
def ler_base_conhecimento(nome_arquivo: str) -> str:
    """Lê arquivos da pasta 'docs'."""
    caminho = os.path.join(DOCS_DIR, os.path.basename(nome_arquivo))
    if not os.path.exists(caminho): return "Arquivo não encontrado."
    with open(caminho, "r", encoding="utf-8") as f: return f.read()

# --- 3. AGENTES ---

prompt_base = f"Contexto do Projeto:\n{CONTEXTO_PROJETO}"

alpha = create_agent(model, tools=[ler_base_conhecimento], system_prompt=f"{prompt_base}\nVocê é Alpha (Gerente).", checkpointer=checkpointer)
architect = create_agent(model, tools=[ler_base_conhecimento, ler_codigo_fonte], system_prompt=f"{prompt_base}\nVocê é Architect (Tech). Pode ler código para analisar.", checkpointer=checkpointer)
experience = create_agent(model, tools=[], system_prompt=f"{prompt_base}\nVocê é Experience (UX).", checkpointer=checkpointer)

# Builder agora tem SUPER PODERES DE LEITURA
builder = create_agent(
    model, 
    tools=[escrever_codigo, ler_codigo_fonte], 
    system_prompt=f"""{prompt_base}
    Você é Builder (Dev).
    REGRA DE OURO: Antes de modificar um arquivo existente (como app.py), 
    USE A TOOL 'ler_codigo_fonte' para ver o conteúdo atual.
    Nunca sobrescreva código às cegas.
    """, 
    checkpointer=checkpointer
)

prompt_star = "Você é o Star (Relator). Gere a ata da reunião."
star = create_agent(model, tools=[], system_prompt=prompt_star, checkpointer=checkpointer)

# --- 4. FUNÇÕES ---

def rodada_debate(user_input, config):
    print("\n   📢 [SISTEMA]: Iniciando Debate...")
    registrar_log("Usuario", user_input)
    
    # Alpha
    print(f"\n🔹 Alpha...")
    res = alpha.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
    print(f"🤖 Alpha: {res['messages'][-1].content}")
    registrar_log("Alpha", res['messages'][-1].content)
    
    # Architect
    print(f"\n🔸 Architect...")
    res = architect.invoke({"messages": [{"role": "user", "content": "Analise tecnicamente."}]}, config=config)
    print(f"🤖 Architect: {res['messages'][-1].content}")
    registrar_log("Architect", res['messages'][-1].content)

    return "Debate concluído."

def rodada_execucao(ordem, config):
    print("\n   🔨 [SISTEMA]: Builder ativado...")
    registrar_log("Usuario (Ordem)", ordem)
    # Reforça a instrução de leitura no prompt dinâmico
    ordem_segura = f"IMPORTANTE: Leia o arquivo atual antes de gerar o novo código. \n\nORDEM: {ordem}"
    res = builder.invoke({"messages": [{"role": "user", "content": ordem_segura}]}, config=config)
    print(f"🤖 Builder: {res['messages'][-1].content}")
    registrar_log("Builder", res['messages'][-1].content)

def encerramento_inteligente(config):
    if len(historico_sessao) < 2: sys.exit(0)
    print("\n   🌟 [STAR]: Gerando Ata...")
    res = star.invoke({"messages": [{"role": "user", "content": f"Gere a ata:\n" + "\n".join(historico_sessao)}]}, config=config)
    
    caminho = os.path.join(DOCS_DIR, f"Ata_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.md")
    with open(caminho, "w", encoding="utf-8") as f: f.write(str(res['messages'][-1].content))
    print(f"   💾 Salvo: {caminho}")
    sys.exit(0)

# --- 5. LOOP ---
config = {"configurable": {"thread_id": "sessao_v11_leitura"}}
print("\n--- 🏢 FamilyOS V11 (Builder com Leitura) ---")

while True:
    try:
        user_input = input("\n👤 Você: ").strip()
        if not user_input: continue
        if user_input.lower() in ["sair", "exit"]: encerramento_inteligente(config)

        if any(user_input.lower().startswith(p) for p in ["builder", "crie", "gere"]):
            rodada_execucao(user_input, config)
        else:
            rodada_debate(user_input, config)
            if input("\n   👉 Acionar Builder? (s/n): ").lower() == 's':
                rodada_execucao(f"Contexto anterior. ORDEM: {input('   📝 Ordem: ')}", config)
    except KeyboardInterrupt: encerramento_inteligente(config)
    except Exception as e: print(f"❌ Erro: {e}")