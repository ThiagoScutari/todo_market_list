import sys
import os

# --- SETUP DE CAMINHOS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

import json
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.callbacks import StdOutCallbackHandler
from dotenv import load_dotenv

# --- NOVOS IMPORTS DO RAGAS (CRITICO) ---
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from ai_core.knowledge_base import buscar_contexto_raw

# Configuração
load_dotenv()

# 1. Configurar LLM e Embeddings do LangChain (Como você já tinha)
handler = StdOutCallbackHandler()

# LLM Gerador (O que responde as perguntas)
llm_gerador = ChatOpenAI(
    model="gpt-4o", 
    temperature=0,
    callbacks=[handler]
)

# LLM Juiz (O que avalia - usado pelo Ragas)
llm_juiz = ChatOpenAI(model="gpt-4o", temperature=0)

# Embeddings (Usado para calcular relevância)
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

# 2. ENVELOPAR PARA O RAGAS (A CORREÇÃO MÁGICA)
# O Ragas precisa desses wrappers para conversar com objetos LangChain
ragas_llm = LangchainLLMWrapper(llm_juiz)
ragas_embeddings = LangchainEmbeddingsWrapper(embedding_model)

def main():
    caminho_dataset = os.path.join(os.path.dirname(src_dir), "docs", "golden_dataset.json")
    
    print(f"📂 Dataset: {caminho_dataset}")
    
    if not os.path.exists(caminho_dataset):
        print(f"❌ Erro: Arquivo não encontrado.")
        return

    with open(caminho_dataset, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    ground_truths = []
    contexts = []
    answers = []

    print(f"\n🚀 AVALIANDO {len(data)} QUESTÕES\n" + "="*60)

    for i, item in enumerate(data):
        q = item["question"]
        gt = item["ground_truth"]
        
        print(f"\n🔹 [{i+1}/{len(data)}] Q: {q}")
        
        # Recuperação
        # REDUZI O K PARA 2 PARA EVITAR ERRO DE MAX_TOKENS NO JUIZ
        retrieved_docs = buscar_contexto_raw(q, k=2) 
        
        # Geração
        context_block = "\n\n".join(retrieved_docs)
        prompt = f"""Use o contexto abaixo para responder tecnicamente:
        {context_block}
        Pergunta: {q}"""
        
        response = llm_gerador.invoke(prompt)
        ans = response.content
        print("   ✅ Gerado.")

        questions.append(q)
        ground_truths.append(gt) # String direta
        contexts.append(retrieved_docs)
        answers.append(ans)

    # Dataset HuggingFace
    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    hf_dataset = Dataset.from_dict(dataset_dict)

    print("\n" + "="*60)
    print("⚖️  RAGAs está julgando (Isso pode demorar)...")
    
    try:
        # Passamos explicitamente o llm e embeddings envelopados
        results = evaluate(
            hf_dataset,
            metrics=[
                context_precision, 
                context_recall,    
                faithfulness,      
                answer_relevancy   
            ],
            llm=ragas_llm,             # <--- AQUI
            embeddings=ragas_embeddings # <--- E AQUI
        )

        print("\n=== 📊 RESULTADOS ===")
        print(results)

        output_path = os.path.join(os.path.dirname(src_dir), "docs", "relatorio_rag.csv")
        df = results.to_pandas()
        df.to_csv(output_path, index=False)
        print(f"💾 Salvo em: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Erro RAGAs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()