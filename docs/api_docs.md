# 📡 FamilyOS API Documentation

**Versão:** 2.1 (Stable - Multi-Module)
**Base URL:** `https://api.thiagoscutari.com.br`
**Tecnologia:** Python Flask, PostgreSQL, SQLAlchemy
**Data de Atualização:** 05/12/2025

---

## 🔐 1. Autenticação e Segurança

O sistema utiliza um modelo híbrido de segurança dependendo da origem da requisição.

### 1.1. Acesso Web (Frontend)
Utiliza **Cookies de Sessão** (`session`) gerados pelo Flask-Login.
* **Cookie Name:** `session`
* **Propriedades:** `HttpOnly`, `Secure`, `SameSite=Lax`.
* **Duração:** 30 dias (`REMEMBER_COOKIE_DURATION`).
* **Proteção:** Todas as rotas (exceto `/magic` e `/login`) possuem o decorador `@login_required`.

### 1.2. Acesso via n8n (Webhooks)
As rotas de IA (`/magic` e `/tasks/magic`) são públicas para permitir o acesso via webhook do n8n sem complexidade de cookies, porém são protegidas por **obscuridade de rota** (não divulgadas publicamente).

---

## 🤖 2. Endpoints de IA (Core n8n)

Estes endpoints são chamados exclusivamente pelo orquestrador **n8n** após a transcrição do áudio.

### 2.1. Processar Compras
**Rota:** `POST /magic`
**Descrição:** Recebe texto natural, extrai itens via IA, categoriza e insere na lista de compras.

* **Headers:** `Content-Type: application/json`
* **Corpo da Requisição (JSON):**
    ```json
    {
      "texto": "Comprar 2 pacotes de café e sabão em pó",
      "usuario": "Thiago"
    }
    ```
* **Lógica de Negócio:**
    * **Parsing:** Ignora blocos Markdown (` ```json `) retornados pela IA.
    * **Deduplicação:** Se o item já existe (`pendente` ou `comprado`), ele é ignorado.
    * **Categorização:** Automática via Google Gemini.
* **Resposta Sucesso (201 Created):**
    ```json
    {
      "message": "✅ Adicionados: Café, Sabão em pó"
    }
    ```
* **Resposta Parcial (201 Created):**
    ```json
    {
      "message": "✅ Adicionados: Café | ⚠️ Já na lista: Sabão em pó"
    }
    ```

### 2.2. Processar Tarefas
**Rota:** `POST /tasks/magic`
**Descrição:** Recebe texto natural, extrai múltiplas tarefas, define prioridade e atribui responsável.

* **Headers:** `Content-Type: application/json`
* **Corpo da Requisição (JSON):**
    ```json
    {
      "texto": "Thiago precisa lavar o carro urgente e nós vamos que jantar fora",
      "remetente": "Débora"
    }
    ```
    * *Nota:* O campo `remetente` é usado para atribuição implícita (se a frase não citar nomes).
* **Lógica de Atribuição:**
    * Cita nome ("Thiago", "Debora") -> Atribui direto.
    * Cita coletivo ("Nós", "Temos") -> Atribui a "Casal".
    * Sem citação -> Atribui ao `remetente`.
* **Resposta Sucesso (201 Created):**
    ```json
    {
      "message": "✅ Thiago: 🔴 Lavar o carro\n✅ Casal: 🟡 Jantar fora",
      "task_id": 45
    }
    ```

---

## 🛒 3. Módulo de Mercado (Frontend Actions)

Endpoints utilizados pelo JavaScript (`shopping.html`) para interatividade.

### 3.1. Alternar Status (Check)
**Rota:** `POST /toggle_item/<id>`
**Descrição:** Marca ou desmarca um item como comprado.
* **Parâmetros:** `id` (Integer) - ID do item na tabela `lista_itens`.
* **Resposta (200 OK):**
    ```json
    {
      "status": "success",
      "novo_status": "comprado"
    }
    ```

### 3.2. Atualizar Item
**Rota:** `POST /update_item`
**Descrição:** Edita nome e categoria via Modal.
* **Corpo (JSON):**
    ```json
    {
      "id": 10,
      "nome": "Pão Francês",
      "categoria": "PADARIA"
    }
    ```
* **Resposta (200 OK):** `{"message": "OK"}`

### 3.3. Arquivar Carrinho
**Rota:** `POST /clear_cart`
**Descrição:** Altera o status de todos os itens `comprado` para `finalizado` (Soft Delete).
* **Resposta (200 OK):** `{"status": "success"}`

---

## ✅ 4. Módulo de Tarefas (Frontend Actions)

Endpoints utilizados pelo JavaScript (`tasks.html`).

### 4.1. Concluir Tarefa
**Rota:** `POST /toggle_task/<id>`
**Descrição:** Alterna o status entre `pendente` e `concluido`.
* **Parâmetros:** `id` (Integer) - ID na tabela `tasks`.
* **Resposta (200 OK):**
    ```json
    {
      "status": "success",
      "novo_status": "concluido"
    }
    ```

### 4.2. Atualizar Tarefa
**Rota:** `POST /tasks/update`
**Descrição:** Edita detalhes da tarefa via Modal.
* **Corpo (JSON):**
    ```json
    {
      "id": 55,
      "descricao": "Lavar o carro",
      "responsavel": "Thiago",
      "prioridade": 3
    }
    ```
    * *Prioridade:* 1 (Baixa/Verde), 2 (Média/Amarela), 3 (Alta/Vermelha).
* **Resposta (200 OK):** `{"status": "success"}`

### 4.3. Arquivar Tarefas
**Rota:** `POST /clear_tasks`
**Descrição:** Altera status de tarefas `concluido` para `arquivado`.
* **Resposta (200 OK):** `{"status": "success"}`

---

## 🌐 5. Interfaces (Views/HTML)

Estas rotas retornam HTML renderizado (Jinja2) para o navegador.

| Rota | Template | Descrição |
| :--- | :--- | :--- |
| `GET /` | `dashboard.html` | **Home:** Clima, Mensagem do Dia e Botões de Acesso. |
| `GET /shopping` | `shopping.html` | **Mercado:** Lista de compras categorizada. |
| `GET /tasks` | `tasks.html` | **Tarefas:** Quadro Kanban agrupado por responsável. |
| `GET /login` | `login.html` | Formulário de acesso. |

---

## 🌍 6. APIs Externas Integradas

O FamilyOS consome serviços de terceiros. As chaves ficam no arquivo `.env`.

### 6.1. Google Gemini (IA)
* **Provider:** Google AI Studio.
* **Modelo:** `gemini-2.5-flash`.
* **Biblioteca:** `langchain-google-genai`.
* **Uso:** Extração de entidades (JSON) a partir de linguagem natural.

### 6.2. HG Brasil (Clima)
* **Provider:** HG Weather API.
* **Uso:** Exibir temperatura e condições atuais no Dashboard.
* **Otimização:** Implementado sistema de **Cache no Banco** (`WeatherCache`).
    * A API só é chamada se o cache for mais antigo que 60 minutos.
    * Evita bloqueio por limite de requisições (Rate Limit).


---
# Sprint 9

## ⏰ Módulo de Lembretes

### `GET /reminders`
Retorna a lista de lembretes do banco local Postgres.
* **Filtros:** Próximos 7 dias, Atrasados.

### `POST /reminders/create`
Cria um lembrete novo.
1.  Salva no Postgres (status 'sync_pending').
2.  Dispara Webhook n8n para criar no Google.
3.  Atualiza Postgres com o `google_id` retornado.

### `POST /reminders/sync`
Força uma sincronização manual (chama n8n para baixar dados do Google).

---

**Documentação gerada automaticamente pelo Alpha Agent.**