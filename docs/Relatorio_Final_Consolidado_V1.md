# 📘 Relatório Técnico Consolidado: FamilyOS (Versão 1.0)

**Projeto:** ToDo Market & List (Módulo de Compras)
**Status:** MVP Funcional em Produção (Local/Híbrido)
**Data de Conclusão:** 27/11/2025
**Objetivo Central:** Gestão doméstica com **Fricção Zero** (Voice-to-Database).

---

## 1. Visão Geral da Arquitetura

O FamilyOS opera sob uma arquitetura de **Microserviço Inteligente Híbrido**. Ele combina a facilidade de interfaces de nuvem com a privacidade e controle de um backend local.

### O Fluxo de Dados (Pipeline)
1.  **Coleta (Input):** O usuário envia áudio ou texto via **Telegram**.
2.  **Orquestração (Nuvem):** O **n8n** recebe a mensagem, transcreve o áudio (via **OpenAI Whisper**) e identifica o usuário.
3.  **Túnel (Conectividade):** O **Ngrok** transporta a requisição segura da nuvem para o servidor local (`localhost:5000`).
4.  **Inteligência (Backend):** A API **Flask** recebe o texto bruto e aciona o **Google Gemini 2.5 Flash-Lite**.
5.  **Processamento (NLP):** O Gemini extrai dados estruturados (Item, Qtd, Unidade, Categoria), normaliza para singular e remove duplicatas.
6.  **Persistência (Banco):** O **SQLAlchemy** grava os dados relacionais no **SQLite**.
7.  **Visualização (Frontend):** Uma Web App **Mobile-First** exibe a lista em tempo real para uso no mercado.

---

## 2. Estrutura do Projeto (File System)

```text
projects/todo_market_list/
├── docs/                   # Documentação e Atas de Reunião
├── src/
│   ├── static/
│   │   └── css/
│   │       └── styles.css  # Estilização Mobile-First (No-Zoom Checkbox)
│   ├── templates/
│   │   └── index.html      # Frontend Jinja2 com Fetch API
│   ├── app.py              # Cérebro: API Flask + Modelos + Lógica NLP
│   ├── reset_db.py         # Utilitário para recriar o banco
│   ├── requirements.txt    # Dependências do Python
│   └── todo_market.db      # Banco de Dados SQLite (Arquivo Vivo)
└── .gitignore              # Proteção de dados sensíveis
````

-----

## 3\. Especificações Técnicas dos Componentes

### 3.1. Backend (`src/app.py`)

Um monólito leve que centraliza a lógica de negócio.

  * **Framework:** Flask.
  * **ORM:** Flask-SQLAlchemy.
  * **AI:** LangChain + Google Generative AI (`gemini-2.5-flash-lite`).
  * **Endpoints:**
      * `POST /magic`: Recebe `{'texto': '...', 'usuario': '...'}`. Processa NLP, verifica duplicidade e salva.
      * `GET /`: Renderiza a lista de compras agrupada por categorias (Acordeão).
      * `POST /toggle_item/<id>`: Inverte status (`pendente` ↔ `comprado`).
      * `POST /clear_cart`: Arquiva itens comprados (`comprado` → `finalizado`).

### 3.2. Banco de Dados (Schema)

Modelagem relacional normalizada para integridade de dados.

  * **Produtos:** Catálogo mestre (Nome, FK Categoria, FK Unidade Padrão).
  * **ListaItem:** A "compra" atual. Contém `quantidade`, `usuario` (quem pediu) e `status`.
  * **Categorias/Unidades:** Tabelas de domínio para padronização.

### 3.3. Frontend (`index.html` + `styles.css`)

Interface desenhada para uso com uma mão (no supermercado).

  * **UX "No-Zoom":** Checkboxes customizados de 32px para toque fácil.
  * **Organização:** Itens agrupados por Categoria em painéis expansíveis (Acordeão).
  * **Interatividade:** JavaScript (`fetch`) atualiza o banco sem recarregar a página.
  * **Feedback:** Itens comprados ficam riscados e opacos visualmente.

-----

## 4\. Regras de Negócio Implementadas

1.  **Anti-Duplicidade Inteligente:**

      * Se o usuário pede "Leite" e já existe "Leite" pendente na lista, o sistema **ignora** a adição e avisa no log. Não há itens repetidos.

2.  **Normalização via IA:**

      * O Prompt do Gemini força: "Converta tudo para **singular** e **minúsculas**".
      * *Exemplo:* "Comprar 3 Batatas" vira `{"nome": "batata", "qtd": 3}`.

3.  **Fluxo de 3 Estados:**

      * `pendente`: Item na lista para comprar.
      * `comprado`: Item no carrinho (riscado na tela).
      * `finalizado`: Item processado (removido da tela pelo botão "Limpar").

4.  **Identidade:**

      * O sistema registra quem fez o pedido ("Thiago" ou "Esposa") e exibe essa tag no card do produto.

-----

## 5\. Guia de Operação (Como Rodar)

### Passo 1: Iniciar o Backend

No terminal, dentro da pasta `src`:

```powershell
python app.py
```

*(O servidor rodará em `http://127.0.0.1:5000`)*

### Passo 2: Abrir o Túnel

Em outro terminal (na pasta `src`):

```powershell
.\ngrok.exe http 5000
```

*(Copie a URL HTTPS gerada e atualize o nó HTTP Request no n8n)*

### Passo 3: Usar

  * **Adicionar:** Mande áudio no Telegram.
  * **Visualizar:** Abra `http://127.0.0.1:5000` no navegador (PC ou Celular na mesma rede).
  * **Comprar:** Clique nas bolinhas para marcar.
  * **Finalizar:** Clique em "Limpar" no final da compra.

-----

## 6\. Próximos Passos (Roadmap Futuro)

  * **Sprint 5 (Deploy):** Migrar para VPS/Render para eliminar a dependência do PC ligado e do Ngrok.
  * **Módulo de Receitas:** Implementar comando "Salvar receita de bolo" para adicionar múltiplos ingredientes de uma vez.
  * **Analytics:** Dashboard para ver "Quanto gastamos com carne este mês?".

-----

**Desenvolvido por:** Thiago Scutari & Gemini e Equipe de Agentes (Alpha, Architect, Builder, Star).
**Tecnologia:** Python, AI, Automation.

```
