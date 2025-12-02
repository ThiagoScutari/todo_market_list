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

# --- RAG AUTOMÁTICO ---
def carregar_contexto_docs():
    contexto = "--- DOCUMENTAÇÃO TÉCNICA (LEIA APENAS SE NECESSÁRIO) ---\n"
    arquivos_md = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    if not arquivos_md: return contexto + "Nenhum documento encontrado."
    for arquivo in arquivos_md:
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                # Limitamos o tamanho para não estourar o contexto com atas velhas
                conteudo = f.read()[-5000:] 
                contexto += f"\n=== ARQUIVO: {os.path.basename(arquivo)} (Trecho Final) ===\n{conteudo}\n"
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")
    return contexto

CONTEXTO_PROJETO = carregar_contexto_docs()
print(f"📚 Contexto carregado.")

conn = sqlite3.connect("memoria_v11_fixed.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# Forçando Lite para evitar bloqueios e alucinações criativas
model = init_chat_model("gemini-2.5-pro", model_provider="google_genai", temperature=0.1)

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
def ler_codigo_fonte(nome_arquivo: str) -> str:
    """Lê o código ATUAL de um arquivo na pasta src."""
    caminho = os.path.join(BASE_DIR, os.path.basename(nome_arquivo))
    if not os.path.exists(caminho): return f"❌ Arquivo {nome_arquivo} não existe."
    try:
        with open(caminho, "r", encoding="utf-8") as f: return f.read()
    except Exception as e: return f"❌ Erro: {e}"

@tool
def escrever_codigo(nome_arquivo: str, conteudo: str) -> str:
    """Salva código na pasta 'codigo_gerado'."""
    caminho = os.path.join(CODIGO_DIR, os.path.basename(nome_arquivo))
    try:
        with open(caminho, "w", encoding="utf-8") as f: f.write(conteudo)
        return f"✅ Código salvo em codigo_gerado/{nome_arquivo}."
    except Exception as e: return f"❌ Erro: {e}"

# --- 3. AGENTES ---

prompt_base = f"Contexto:\n{CONTEXTO_PROJETO}"

alpha = create_agent(model, tools=[], system_prompt=f"{prompt_base}\nVocê é Alpha (Gerente).", checkpointer=checkpointer)
architect = create_agent(model, tools=[ler_codigo_fonte], system_prompt=f"{prompt_base}\nVocê é Architect (Tech).", checkpointer=checkpointer)
experience = create_agent(model, tools=[], system_prompt=f"{prompt_base}\nVocê é Experience (UX).", checkpointer=checkpointer)

# BUILDER BLINDADO v2 (Protocolo de Preservação Visual)
builder = create_agent(
    model, 
    tools=[escrever_codigo, ler_codigo_fonte], 
    system_prompt=f"""
    VOCÊ É O BUILDER. UM ROBÔ DE CODIFICAÇÃO.
    
    SUAS REGRAS DE OURO (LEIA COM ATENÇÃO EXTREMA):
    1. PROIBIÇÃO ABSOLUTA DE MUDANÇA VISUAL: NÃO ALTERE O DESIGN, CSS, CLASSES OU ESTRUTURA HTML A MENOS QUE A ORDEM SEJA EXPLICITAMENTE "MUDE O LAYOUT".
    2. PRESERVAÇÃO TOTAL: Ao editar arquivos (especialmente .html e .css), você DEVE LER O ARQUIVO PRIMEIRO e manter TODAS as classes, IDs e estruturas existentes.
    3. FOCO CIRÚRGICO: Se a tarefa for lógica (Python/JS), injete o código apenas onde necessário. Não reescreva o HTML inteiro com um template genérico.
    4. O LAYOUT É "DARK NEON" COM BOOTSTRAP. Nunca reverta para HTML simples ou fundo branco.
    5. NÃO CUMPRIMENTE. NÃO EXPLIQUE. APENAS GERE O CÓDIGO FINAL.
    6. Sempre use a tool 'ler_codigo_fonte' antes de escrever.
    """, 
    checkpointer=checkpointer
)

star = create_agent(
    model, tools=[], 
    system_prompt="Você é Star. Gere a Ata da reunião baseada no log.", 
    checkpointer=checkpointer
)

# --- 4. FUNÇÕES ---

def rodada_debate(user_input, config):
    print("\n   📢 [SISTEMA]: Debate...")
    registrar_log("Usuario", user_input)
    
    res = alpha.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
    msg = limpar_conteudo(res['messages'][-1].content)
    print(f"🤖 Alpha: {msg}")
    registrar_log("Alpha", msg)
    
    res = architect.invoke({"messages": [{"role": "user", "content": "Visão técnica?"}]}, config=config)
    msg = limpar_conteudo(res['messages'][-1].content)
    print(f"🤖 Architect: {msg}")
    registrar_log("Architect", msg)

    return msg

def rodada_execucao(ordem, config):
    print("\n   🔨 [SISTEMA]: Builder ativado...")
    registrar_log("Usuario (Ordem)", ordem)
    
    # CORREÇÃO CRÍTICA: Prompt de Enquadramento
    ordem_blindada = f"""
    ORDEM TÉCNICA IMEDIATA:
    {ordem}
    
    INSTRUÇÃO:
    1. Leia o arquivo necessário usando 'ler_codigo_fonte'.
    2. Escreva o novo código usando 'escrever_codigo'.
    NÃO GERE TEXTO DE CONVERSA. APENAS USE AS FERRAMENTAS.
    """
    
    # CORREÇÃO CRÍTICA: Usando a variável certa
    res = builder.invoke({"messages": [{"role": "user", "content": ordem_blindada}]}, config=config)
    
    msg_builder = limpar_conteudo(res['messages'][-1].content)
    print(f"🤖 Builder: {msg_builder}")
    registrar_log("Builder", msg_builder)

def encerramento_inteligente(config):
    if len(historico_sessao) < 2: sys.exit(0)
    print("\n   🌟 [STAR]: Gerando Ata...")
    log = "\n".join(historico_sessao)
    res = star.invoke({"messages": [{"role": "user", "content": f"Ata:\n{log}"}]}, config=config)
    
    caminho = os.path.join(DOCS_DIR, f"Ata_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.md")
    with open(caminho, "w", encoding="utf-8") as f: f.write(str(res['messages'][-1].content))
    print(f"   💾 Salvo: {caminho}")
    sys.exit(0)

# --- 5. LOOP ---
config = {"configurable": {"thread_id": "sessao_v11_fixed_2"}}
print("\n--- 🏢 FamilyOS V11 (Builder Corrigido) ---")

while True:
    try:
        print("\n" + "-"*60)
        user_input = input("👤 Você: ").strip()
        if not user_input: continue
        if user_input.lower() in ["sair", "exit"]: encerramento_inteligente(config)

        if any(user_input.lower().startswith(p) for p in ["builder", "crie", "gere"]):
            rodada_execucao(user_input, config)
        else:
            rodada_debate(user_input, config)
            if input("\n   👉 Acionar Builder? (s/n): ").lower() == 's':
                pedido = input("   📝 Ordem: ")
                rodada_execucao(pedido, config)
    except KeyboardInterrupt: encerramento_inteligente(config)
    except Exception as e: print(f"❌ Erro: {e}")