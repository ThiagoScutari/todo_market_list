# 🛒 FamilyOS: ToDo Market & List
### Software House Autônoma de Gestão Doméstica

O **FamilyOS** é um sistema híbrido de gestão doméstica inteligente, focado em eliminar a **fricção cognitiva e operacional** na organização familiar. O foco inicial é o Módulo de Compras, que utiliza Inteligência Artificial para transformar áudios no Telegram em uma **Lista de Compras Web Interativa**.

---

## 💡 Visão Estratégica e Princípios

O projeto é guiado por um objetivo central: **Fricção Zero**.
* **Na Entrada:** Basta falar ("Comprar leite") sem abrir apps complexos.
* **Na Saída:** Uma interface web desenhada para uso com uma mão no supermercado.

### Objetivos Principais
* **Voice-to-Database:** Entrada de dados natural via Telegram.
* **Mobile-First UX:** Interface web otimizada para compras rápidas.
* **Inteligência Anti-Duplicidade:** O sistema entende se você já pediu o item.

---

## 🏗️ Arquitetura de Alto Nível (Sprint 4 - Concluída)

A arquitetura evoluiu para um **Monólito Modular Inteligente**, onde o Flask gerencia tanto a API de inteligência quanto o Frontend de visualização.

```

┌─────────────────┐    ┌──────────────────┐    ┌───────────────────────────┐
│   INTERFACE     │    │   ORQUESTRADOR   │    │    CÉREBRO & FRONTEND     │
│                 │    │                  │    │                           │
│  • Telegram     │───▶│  • n8n           │───▶│  • Flask (API + Web)      │
│  • (Voz/Texto)  │    │  • Whisper/Ngrok │    │  • Gemini AI (NLP)        │
└─────────────────┘    └──────────────────┘    │  • SQLAlchemy (DB)        │
└─────────────┬─────────────┘
│
▼
┌──────────────────┐
│    MEMÓRIA       │
│                  │
│  • SQLite        │
│                  │
└──────────────────┘

````

### Componentes Chave

| Componente | Função | Tecnologias Chave |
| :--- | :--- | :--- |
| **Interface de Entrada** | Captura de áudio/texto | Telegram Bot API |
| **Orquestrador** | Transcrição e Roteamento | n8n, OpenAI Whisper, Ngrok |
| **Cérebro (NLP)** | Extração de itens e Categorização | Google Gemini 2.5 Flash-Lite, LangChain |
| **Backend** | Regras de Negócio e Persistência | Python Flask, SQLAlchemy |
| **Frontend** | Visualização e Controle (Check-off) | HTML5, CSS3 (Mobile-First), Jinja2, JS Fetch |

---

## 🎯 Funcionalidades do Módulo de Compras

### 1. Entrada Inteligente (`POST /magic`)
* **Processamento de Linguagem Natural:** Entende frases complexas ("3kg de costela para churrasco").
* **Normalização:** Converte plurais para singular e padroniza unidades.
* **Anti-Duplicidade:** Se o item já está na lista, ele não duplica.
* **Identidade:** Rastreia quem pediu o item (Thiago ou Esposa).

### 2. Interface de Compras (`GET /`)
* **Design No-Zoom:** Checkboxes grandes e áreas de toque otimizadas para celular.
* **Organização:** Agrupamento automático por categorias (Hortifrúti, Padaria, etc.).
* **Feedback Visual:** Itens comprados ficam riscados instantaneamente.

### 3. Gestão de Estado (`POST /toggle_item` & `/clear_cart`)
* **Persistência:** O status (pendente/comprado) é salvo no banco em tempo real.
* **Limpeza:** Botão para arquivar itens comprados ao final da feira.

---

## 🛠️ Setup e Desenvolvimento

Para rodar o projeto localmente:

1.  **Clonar o Repositório:**
    ```bash
    git clone [https://github.com/ThiagoScutari/todo_market_list.git](https://github.com/ThiagoScutari/todo_market_list.git)
    cd todo_market_list
    ```

2.  **Configurar Ambiente:**
    * Crie o ambiente virtual e instale as dependências:
        ```bash
        pip install -r requirements.txt
        ```

3.  **Configurar Chaves (`.env`):**
    * Crie um arquivo `.env` na raiz `src/` com suas chaves (Gemini, OpenAI).

4.  **Inicializar Banco de Dados:**
    * Execute o script que cria o SQLite e popula as categorias base:
    ```powershell
    python src/reset_db.py
    ```

5.  **Rodar a Aplicação:**
    ```powershell
    python src/app.py
    ```
    * Acesse o Frontend: `http://localhost:5000`

6.  **Conectar com a Nuvem (n8n):**
    * Inicie o Ngrok: `ngrok http 5000`
    * Atualize a URL no workflow do n8n.

---

## 🗺️ Roadmap de Desenvolvimento

| Sprint | Foco | Status |
| :--- | :--- | :--- |
| **Sprint 1** | Backend & Banco de Dados | ✅ Concluído |
| **Sprint 2** | Integração (n8n + Ngrok + NLP) | ✅ Concluído |
| **Sprint 3** | Frontend Web (Substituindo Notion) | ✅ Concluído |
| **Sprint 4** | Interatividade e Persistência | ✅ Concluído |
| **Sprint 5** | Deploy em Produção (VPS/Render) | 🚧 Próximo Passo |

---
**Desenvolvido com IA e Engenharia de Prompt.**
````