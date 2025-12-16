# 📐 Planejamento de Arquitetura RAG Avançada (FamilyOS)

[cite_start]**Baseado em:** "Aprofundando em RAG e suas Variações" [cite: 1]
**Objetivo:** Implementar um pipeline de recuperação robusto que supere as limitações do "Naive RAG" para o Chat do FamilyOS.

---

## 1. Diagnóstico e Necessidade

O documento alerta que o **Naive RAG** (apenas busca vetorial simples) falha em casos de:
* [cite_start]**Recuperação Lexical:** Quando o usuário busca por IDs ou nomes exatos (ex: "Tarefa #123")[cite: 48].
* [cite_start]**Lost-in-the-Middle:** LLMs esquecem informações no meio de contextos longos[cite: 178].

[cite_start]**Solução Adotada:** **Modular RAG**  [cite_start]com **Busca Híbrida**.

---

## 2. Arquitetura do Pipeline (Modular RAG)

[cite_start]O fluxo de dados será decomposto em módulos independentes[cite: 79]:
### Módulo 1: Indexação e Chunking (Offline)
* [cite_start]**Estratégia:** Evitar "Blind Chunking" (corte cego)[cite: 49]. [cite_start]Usaremos **Semantic Chunking** ou fragmentação recursiva respeitando limites de frases/parágrafos[cite: 31].
* [cite_start]**Modelo de Embedding:** Utilizar um modelo otimizado para *Retrieval* (MTEB Leaderboard), focado na métrica **NDCG@10**[cite: 162].

### Módulo 2: Recuperação Híbrida (Pre-Retrieval & Retrieval)
* [cite_start]**Router (Roteador):** Um pequeno LLM classifica a intenção[cite: 88]:
    * *Intenção Factual:* "O que é RAG?" -> Rota para Vector DB.
    * [cite_start]*Intenção de Dados:* "Status da tarefa 10" -> Rota para SQL/API[cite: 91].
* **Hybrid Search:**
    * [cite_start]**Vetor (Semântico):** ChromaDB ou FAISS para similaridade[cite: 173].
    * [cite_start]**Lexical (Palavra-chave):** BM25 para encontrar termos exatos.
* [cite_start]**Fusão:** Combinar resultados usando *Reciprocal Rank Fusion (RRF)*[cite: 103].

### Módulo 3: Pós-Recuperação (Reranking)
* [cite_start]**Problema:** O Recuperador inicial prioriza Recall (trazer tudo), mas traz ruído[cite: 65].
* [cite_start]**Solução:** Implementar um **Cross-Encoder** (Reranker) para reordenar os Top-50 resultados e entregar apenas o Top-5 mais relevante ao LLM[cite: 69, 70].
* [cite_start]**Mitigação de Viés:** Posicionar os chunks mais importantes no início e no fim do prompt para evitar o problema "Lost-in-the-Middle"[cite: 186].

### Módulo 4: Geração e Avaliação (Self-Correction)
* [cite_start]**Corrective RAG (CRAG):** Se a recuperação for avaliada como "Incorreta" ou "Ambígua"[cite: 131, 133], o sistema deve acionar um fallback (ex: pedir clarificação ao usuário ou buscar na web, se habilitado).

---

## 3. Stack Tecnológico Sugerido

[cite_start]Baseado na comparação de Vector DBs[cite: 172]:

| Componente | Tecnologia Sugerida | Justificativa |
| :--- | :--- | :--- |
| **Vector DB** | **Chroma** | [cite_start]Open Source, ideal para prototipagem média e simples de usar[cite: 173]. |
| **Embedding** | **text-embedding-3-small** | (OpenAI) Bom balanceamento custo/performance MTEB. |
| **Orquestração** | **LangChain** | [cite_start]Framework maduro para compor esses módulos "lego"[cite: 107]. |
| **Avaliação** | **RAGAs** | [cite_start]Framework "LLM-as-a-judge" para medir Fidelidade e Relevância[cite: 216]. |

---

## 4. Plano de Implementação (Fases)

1.  **Fase 1 (MVP Híbrido):** Implementar ChromaDB + BM25 (via LangChain EnsembleRetriever).
2.  **Fase 2 (Refinamento):** Adicionar Reranker (Cross-Encoder) no pipeline.
3.  [cite_start]**Fase 3 (Qualidade):** Configurar RAGAs para testar "Faithfulness" e "Answer Relevancy"[cite: 221, 225].

---