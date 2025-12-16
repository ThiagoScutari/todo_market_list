import os
import glob
import shutil
from typing import List, Optional
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Caminhos
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR) # src/
DOCS_DIR = os.path.join(os.path.dirname(BASE_DIR), "docs")
DB_DIR = os.path.join(CURRENT_DIR, "chroma_db")

# Configuração de Embedding
embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")

# --- SINGLETON PARA CONEXÃO ---
_DB_INSTANCE: Optional[Chroma] = None

def resetar_banco():
    """Apaga o banco atual para recriar do zero (útil se corromper)."""
    global _DB_INSTANCE
    if os.path.exists(DB_DIR):
        try:
            shutil.rmtree(DB_DIR)
            print("🧹 Banco vetorial antigo removido.")
        except Exception as e:
            print(f"⚠️ Não foi possível apagar {DB_DIR}: {e}")
    _DB_INSTANCE = None

def indexar_documentos():
    """Lê documentos e cria o índice."""
    print(f"🔄 Iniciando indexação em: {DB_DIR}")
    
    # Se a pasta não existe ou está vazia, precisamos criar
    arquivos_md = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    
    if not arquivos_md:
        print("⚠️ Nenhum arquivo .md encontrado em docs/")
        return None

    documentos = []
    for arquivo in arquivos_md:
        try:
            loader = TextLoader(arquivo, encoding="utf-8")
            documentos.extend(loader.load())
            print(f"   📄 Indexando: {os.path.basename(arquivo)}")
        except Exception as e:
            print(f"   ❌ Erro ao ler {arquivo}: {e}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(documentos)
    print(f"   🧩 Gerados {len(chunks)} fragmentos.")

    # Criação do Banco
    vectorstore = Chroma.from_documents(
        documents=chunks, 
        embedding=embedding_function,
        persist_directory=DB_DIR
    )
    print("✅ Indexação concluída.")
    return vectorstore

def carregar_banco():
    """
    Retorna a instância do banco (Singleton).
    Se não existir ou der erro de conexão, tenta recriar.
    """
    global _DB_INSTANCE
    
    if _DB_INSTANCE is not None:
        return _DB_INSTANCE

    try:
        # Tenta carregar existente
        if os.path.exists(DB_DIR) and os.listdir(DB_DIR):
            _DB_INSTANCE = Chroma(
                persist_directory=DB_DIR, 
                embedding_function=embedding_function
            )
        else:
            # Cria novo
            _DB_INSTANCE = indexar_documentos()
            
    except Exception as e:
        print(f"⚠️ Erro ao conectar no Chroma: {e}. Tentando resetar...")
        resetar_banco()
        _DB_INSTANCE = indexar_documentos()

    return _DB_INSTANCE

@tool
def consultar_documentacao(pergunta: str) -> str:
    """
    Busca informações técnicas na documentação do projeto (RAG).
    Use para dúvidas sobre API, Banco de Dados, Frontend ou Specs.
    """
    try:
        db = carregar_banco()
        if not db:
            return "Erro: Banco de dados de conhecimento indisponível."
            
        # Busca
        docs = db.similarity_search(pergunta, k=4)
        
        # Formata resposta
        resposta = "\n\n".join([
            f"--- Fonte: {d.metadata.get('source', 'Desconhecido')} ---\n{d.page_content}" 
            for d in docs
        ])
        return resposta if resposta else "Nenhuma informação encontrada."
        
    except Exception as e:
        return f"Erro na consulta RAG: {str(e)}"

# Função auxiliar para o script de avaliação
def buscar_contexto_raw(pergunta: str, k: int = 4):
    db = carregar_banco()
    docs = db.similarity_search(pergunta, k=k)
    return [d.page_content for d in docs]