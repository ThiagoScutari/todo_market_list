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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(os.path.dirname(BASE_DIR), "docs")
CODIGO_DIR = os.path.join(BASE_DIR, "codigo_gerado")

for path in [DOCS_DIR, CODIGO_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# --- RAG SIMPLIFICADO (Carregamento Automático) ---
def carregar_contexto_docs():
    """Lê todos os .md da pasta docs e retorna um stringão."""
    contexto = "--- BASE DE CONHECIMENTO DO PROJETO ---\n"
    arquivos_md = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    
    if not arquivos_md:
        return contexto + "Nenhum documento encontrado na pasta docs."
    
    for arquivo in arquivos_md:
        nome = os.path.basename(arquivo)
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                conteudo = f.read()
                contexto += f"\n=== ARQUIVO: {nome} ===\n{conteudo}\n"
        except Exception as e:
            print(f"Erro ao ler {nome}: {e}")
            
    return contexto

# Carrega tudo na memória agora
CONTEXTO_PROJETO = carregar_contexto_docs()
print(f"📚 {len(CONTEXTO_PROJETO)} caracteres de documentação carregados na memória dos agentes.")

conn = sqlite3.connect("memoria_v10_rag.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# Usando o modelo Lite
model = init_chat_model("gemini-2.5-pro", model_provider="google_genai", temperature=0.3)

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

# --- 2. FERRAMENTAS ---

@tool
def escrever_codigo(nome_arquivo: str, conteudo: str) -> str:
    """Salva código na pasta 'codigo_gerado'. USE APENAS QUANDO TIVER CERTEZA DO CÓDIGO."""
    caminho = os.path.join(CODIGO_DIR, os.path.basename(nome_arquivo))
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return f"✅ Código salvo: {caminho}"
    except Exception as e:
        return f"❌ Erro: {e}"

# --- 3. AGENTES (Com Contexto Injetado) ---

# O Prompt do Sistema agora inclui o conteúdo dos arquivos
prompt_base = f"""
Você é um especialista parte da equipe FamilyOS.
Abaixo está TODA a documentação do projeto. Você NÃO PRECISA ler arquivos, eles já estão aqui.
Baseie suas respostas EXCLUSIVAMENTE nestes dados:

{CONTEXTO_PROJETO}
"""

alpha = create_agent(
    model, tools=[], 
    system_prompt=f"{prompt_base}\nVocê é Alpha (Gerente). Coordene o debate e valide requisitos.", 
    checkpointer=checkpointer
)

architect = create_agent(
    model, tools=[], 
    system_prompt=f"{prompt_base}\nVocê é Architect (Tech Lead). Valide Banco de Dados e Stack.", 
    checkpointer=checkpointer
)

experience = create_agent(
    model, tools=[], 
    system_prompt=f"{prompt_base}\nVocê é Experience (UX). Valide a usabilidade.", 
    checkpointer=checkpointer
)

# O Builder precisa da tool de escrita, mas também recebe o contexto para saber O QUE escrever
builder = create_agent(
    model, tools=[escrever_codigo], 
    system_prompt=f"{prompt_base}\nVocê é Builder (Dev). Sua função é escrever código. Use a tool 'escrever_codigo' quando ordenado.", 
    checkpointer=checkpointer
)

prompt_star = """
Você é o Star (Relator). Gere uma Ata em Markdown baseada no log.
Não invente. Se for curto, diga que foi curto.
"""
star = create_agent(model, tools=[], system_prompt=prompt_star, checkpointer=checkpointer)

# --- 4. FUNÇÕES ---

def rodada_debate(user_input, config):
    print("\n   📢 [SISTEMA]: Iniciando Debate (Agentes já leram a doc)...")
    registrar_log("Usuario", user_input)
    
    # Alpha
    print(f"\n🔹 Alpha falando...")
    res = alpha.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
    msg_alpha = limpar_conteudo(res['messages'][-1].content)
    print(f"🤖 Alpha: {msg_alpha}")
    registrar_log("Alpha", msg_alpha)
    
    # Architect
    print(f"\n🔸 Architect complementando...")
    res = architect.invoke({"messages": [{"role": "user", "content": "Com base na documentação que você já leu, qual a visão técnica?"}]}, config=config)
    msg_arch = limpar_conteudo(res['messages'][-1].content)
    print(f"🤖 Architect: {msg_arch}")
    registrar_log("Architect", msg_arch)
    
    return f"{msg_alpha}\n{msg_arch}"

def rodada_execucao(ordem, config):
    print("\n   🔨 [SISTEMA]: Builder ativado...")
    registrar_log("Usuario (Ordem)", ordem)
    res = builder.invoke({"messages": [{"role": "user", "content": ordem}]}, config=config)
    msg_builder = limpar_conteudo(res['messages'][-1].content)
    print(f"🤖 Builder: {msg_builder}")
    registrar_log("Builder", msg_builder)

def encerramento_inteligente(config):
    print("\n" + "="*60)
    if len(historico_sessao) < 2:
        print("   🚫 Sessão curta demais. Nada salvo.")
        sys.exit(0)

    print("   🌟 [STAR]: Gerando Ata...")
    log_completo = "\n".join(historico_sessao)
    res = star.invoke({"messages": [{"role": "user", "content": f"Gere a ata:\n{log_completo}"}]}, config=config)
    conteudo_md = limpar_conteudo(res['messages'][-1].content)
    
    data_hoje = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    caminho = os.path.join(DOCS_DIR, f"Ata_{data_hoje}.md")
    
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo_md)
    print(f"   💾 Salvo em: {caminho}")
    sys.exit(0)

# --- 5. LOOP ---

config = {"configurable": {"thread_id": "sessao_v10_rag_auto"}}

print(f"\n--- 🏢 FamilyOS V10 (Contexto Carregado) ---")

while True:
    try:
        print("\n" + "-"*60)
        user_input = input("👤 Você: ").strip()
        if not user_input: continue
        
        if user_input.lower() in ["sair", "exit"]:
            encerramento_inteligente(config)
            break

        if any(user_input.lower().startswith(p) for p in ["builder", "crie", "gere"]):
            rodada_execucao(user_input, config)
        else:
            resumo = rodada_debate(user_input, config)
            print("\n   👉 Deseja acionar o Builder? (s/n)")
            if input("   👤 Decisão: ").lower() == 's':
                pedido = input("   📝 Ordem: ")
                rodada_execucao(f"Contexto: {resumo}\nORDEM: {pedido}", config)

    except KeyboardInterrupt:
        encerramento_inteligente(config)
    except Exception as e:
        print(f"❌ Erro: {e}")