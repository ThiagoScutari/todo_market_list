import sqlite3
import os
from langgraph.checkpoint.sqlite import SqliteSaver

# Configurações de Caminho
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Pasta onde está este script (src)
PROJECT_ROOT = os.path.dirname(BASE_DIR)              # Pasta raiz do projeto
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")         # Pasta docs

# Garante que a pasta docs existe
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)
    print(f"📁 Pasta 'docs' criada automaticamente em: {DOCS_DIR}")

DB_PATH = "memoria_v10_rag.db"
THREAD_ID = "sessao_v10_rag_auto"

def recuperar_conversa():
    print(f"--- 🔍 Recuperando memória de: {DB_PATH} ---")
    
    try:
        # Conecta no DB (assume que o .db está na mesma pasta do script)
        db_full_path = os.path.join(BASE_DIR, DB_PATH)
        conn = sqlite3.connect(db_full_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn=conn)
        
        config = {"configurable": {"thread_id": THREAD_ID}}
        
        state_snapshot = checkpointer.get(config)
        
        if not state_snapshot:
            print("❌ Nenhum estado encontrado.")
            return

        # Lógica de extração segura (Objeto vs Dicionário)
        messages = []
        if hasattr(state_snapshot, "values"):
            try:
                dados = state_snapshot.values
                if isinstance(dados, dict):
                    messages = dados.get("messages", [])
                else:
                    raise AttributeError 
            except AttributeError:
                if isinstance(state_snapshot, dict):
                    messages = state_snapshot.get("channel_values", {}).get("messages", []) or state_snapshot.get("messages", [])

        if not messages and isinstance(state_snapshot, dict):
             messages = state_snapshot.get("channel_values", {}).get("messages", [])

        if not messages:
            print("⚠️ Nenhuma mensagem encontrada no estado recuperado.")
            return

        print(f"✅ Sucesso! Recuperadas {len(messages)} mensagens.")
        
        # Gera o Markdown
        relatorio_md = "# 🗂️ Relatório Recuperado (Crash Recovery)\n\n"
        
        for msg in messages:
            role = "Desconhecido"
            if hasattr(msg, "type"):
                if msg.type == "human":
                    role = "👤 VOCÊ"
                elif msg.type == "ai":
                    nome = getattr(msg, "name", "AGENTE")
                    role = f"🤖 {nome}"
                elif msg.type == "tool":
                    role = f"🛠️ TOOL ({getattr(msg, 'name', '?')})"
            
            conteudo = getattr(msg, "content", str(msg))
            relatorio_md += f"### {role}\n{conteudo}\n\n---\n\n"

        # Caminho final do arquivo
        nome_arquivo = os.path.join(DOCS_DIR, "relatorio_recuperado_2.md")
        
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(relatorio_md)
            
        print(f"🎉 Relatório salvo com sucesso em:\n{nome_arquivo}")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    recuperar_conversa()