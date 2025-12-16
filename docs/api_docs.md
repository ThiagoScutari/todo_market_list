# 📡 FamilyOS API Documentation

**Versão:** 2.2 (Omniscient Sync)
**Base URL:** `https://api.thiagoscutari.com.br`
**Tecnologia:** Python Flask, PostgreSQL, SQLAlchemy
**Data de Atualização:** 12/12/2025

---

## 🔐 1. Autenticação e Segurança

### 1.1. Acesso Web (Frontend)
Utiliza **Cookies de Sessão** gerados pelo Flask-Login.
* **Proteção:** Decorador `@login_required` em todas as rotas de visualização e ação.
* **Sessão:** Duração de 30 dias (`REMEMBER_COOKIE_DURATION`).
* **Segurança:** Configurado com `HttpOnly`, `Secure` e `SameSite=Lax`.

### 1.2. Acesso via n8n (Webhooks)
As rotas de processamento são públicas para permitir gatilhos externos, mas devem ser mantidas obscuras (não divulgadas).
* **Rotas de Serviço:** `/voice/process`, `/reminders/sync`.

---

## 🧠 2. Core Intelligence (IA & Voz)

Endpoint central que processa linguagem natural (Gemini) para estruturar dados.

### 2.1. Processador Omniscient (Voz/Texto)
**Rota:** `POST /voice/process`
**Descrição:** O "cérebro" único do sistema. Recebe texto (transcrito ou digitado), identifica a intenção (Compras, Tarefas ou Lembretes) e executa a ação correspondente.

* **Headers:** `Content-Type: application/json`
* **Corpo da Requisição (JSON):**
    ```json
    {
      "texto": "Lavar o carro e comprar leite",
      "usuario": "Thiago"
    }
    ```
* **Lógica de Negócio (Gemini 2.5):**
    1.  **Shopping:** Verifica duplicidade, categoriza e insere.
    2.  **Tasks:** Define prioridade (1-3) e responsável (Thiago/Débora/Casal).
    3.  **Reminders:** Cria lembrete local e dispara webhook para criar no Google Tasks.
* **Resposta (201 Created):**
    ```json
    {
      "message": "🛒 Compra: 📦 Leite | ✅ Tarefa (Thiago): Lavar o carro"
    }
    ```

---

## 🔔 3. Módulo de Lembretes (Google Sync)

Gerenciamento de agenda com sincronização bidirecional (Google Tasks).

### 3.1. Sincronização em Lote (Batch Sync)
**Rota:** `POST /reminders/sync`
**Descrição:** Recebe uma lista de tarefas do n8n (Google Tasks) e atualiza o banco local.
* **Lógica:** Aceita Payload Puro (Lista) ou Payload Agregado pelo n8n.
* **Corpo da Requisição (Lista JSON):**
    ```json
    [
      {
        "id": "GTASK_ID_123",
        "title": "Reunião",
        "due": "2025-12-12T14:00:00.000Z",
        "status": "needsAction",
        "deleted": false
      }
    ]
    ```
* **Resposta (200 OK):**
    ```json
    {
      "status": "success",
      "criados": 1,
      "atualizados": 0,
      "deletados": 0
    }
    ```

### 3.2. Criar Lembrete
**Rota:** `POST /reminders/create`
**Descrição:** Cria lembrete localmente e dispara gatilho para o n8n criar no Google.
* **Corpo:** `{"title": "Ir ao médico", "date": "2025-12-20", "time": "10:00"}`

### 3.3. Atualizar Lembrete
**Rota:** `POST /reminders/update`
**Descrição:** Atualiza dados locais e envia para o Google via n8n.
* **Corpo:** `{"id": 1, "title": "Novo Título", "notes": "Detalhes..."}`

### 3.4. Gatilho Manual
**Rota:** `POST /reminders/trigger`
**Descrição:** O botão "Sincronizar Agora" do front-end chama essa rota, que por sua vez chama o Webhook do n8n para iniciar o fluxo de sync.

---

## 🛒 4. Módulo de Mercado (Ações)

### 4.1. Check/Uncheck Item
**Rota:** `POST /toggle_item/<id>`
**Descrição:** Alterna status entre `pendente` e `comprado`.

### 4.2. Limpar Carrinho (Arquivar)
**Rota:** `POST /clear_cart`
**Descrição:** Move itens `comprado` para `finalizado`.

### 4.3. Editar Item
**Rota:** `POST /update_item`
**Descrição:** Atualiza nome e categoria.

---

## ✅ 5. Módulo de Tarefas (Ações)

### 5.1. Concluir Tarefa
**Rota:** `POST /toggle_task/<id>`
**Descrição:** Alterna status entre `pendente` e `concluido`.

### 5.2. Arquivar Concluídas
**Rota:** `POST /clear_tasks`
**Descrição:** Move tarefas `concluido` para `arquivado`.

### 5.3. Editar Tarefa
**Rota:** `POST /tasks/update`
**Descrição:** Atualiza descrição, responsável e prioridade.

---

## 🌐 6. Views (Frontend)

* `GET /` - Dashboard (Home).
* `GET /login` - Tela de Login.
* `GET /shopping` - Lista de Compras.
* `GET /tasks` - Kanban de Tarefas.
* `GET /reminders` - Lista de Lembretes.