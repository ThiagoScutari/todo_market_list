# 📡 FamilyOS API Documentation

**Versão:** 2.2 (Omniscient Sync + AI Core)
**Base URL:** `https://api.thiagoscutari.com.br`
**Tecnologia:** Python Flask, PostgreSQL, SQLAlchemy
**Data de Atualização:** 02/01/2026

Esta documentação detalha os endpoints da API do FamilyOS, utilizada tanto pelo Frontend (Web App) quanto pelas automações externas (n8n/Webhooks).

## 🔐 1. Autenticação e Segurança

O sistema utiliza sessões baseadas em cookies (`session`) para usuários via navegador e proteção por obscuridade/IP para webhooks externos.

### 1.1. Login de Usuário
**Rota:** `POST /login`  
**Autenticação:** Pública (requer credenciais no corpo).  
**Descrição:** Recebe usuário e senha. Se válidos, cria um cookie de sessão assinado pelo servidor (Flask-Login) e redireciona o usuário para a página inicial.

* **Exemplo de Requisição (Form Data ou JSON):**  
```json  
  {
    "username": "thiago",
    "password": "minha_senha_super_secreta"
  }  
   
```

* **Exemplo de Resposta (Sucesso - 302 Found):**
O servidor retorna um código de redirecionamento, não um JSON.
  * **Status:** `302 Found`
  * **Header Location:** `/` (Dashboard)
  * **Set-Cookie:** `session=ey...; Path=/; HttpOnly; Secure; SameSite=Lax`


* **Exemplo de Resposta (Erro - 200 OK com Flash):**
Se a senha estiver errada, ele recarrega a página de login mostrando a mensagem de erro.
  * **Status:** `200 OK`
  * **HTML Body:** `...<div class="alert">Login inválido</div>...`

### 1.2. Logout

**Rota:** `GET /logout`
**Autenticação:** Requer Sessão Ativa (`@login_required`).
**Descrição:** Encerra a sessão atual, invalida o cookie do navegador e redireciona para a tela de login.

* **Exemplo de Requisição:**
`GET https://api.thiagoscutari.com.br/logout`
* **Exemplo de Resposta:**
  * **Status:** `302 Found`
  * **Header Location:** `/login`
  * **Set-Cookie:** `session=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; ...` (Limpa o cookie)

## 🧠 2. Core Intelligence (IA & Webhooks)

Esta seção documenta os endpoints de "inteligência" do sistema. Eles geralmente são consumidos por automações externas (n8n) ou internamente pelo próprio backend.

### 2.1. Processador Omniscient (Voz/Texto)
**Rota:** `POST /voice/process`
**Autenticação:** Proteção por Obscuridade (IP/Header no futuro).
**Descrição:** É o ponto de entrada principal para comandos em linguagem natural. Recebe um texto transcrito (do Telegram/Whisper) ou digitado, envia para o `AIAssistant` (Gemini) e executa as ações necessárias (criar itens no mercado, agendar tarefas, definir lembretes).

* **Exemplo de Requisição (JSON):**
```json
  {
    "texto": "Comprar 2 caixas de leite desnatado e lembrar de pagar a conta de luz amanhã",
    "usuario": "Thiago"
  }

```

* **Exemplo de Resposta (Sucesso):**
O retorno é uma mensagem formatada pronta para ser devolvida ao usuário (ex: no chat do Telegram).
```json
{
  "message": "🛒 **Mercado:**\n- 2x Leite Desnatado 🥛\n\n🔔 **Lembrete Criado:**\n- Pagar a conta de luz (Amanhã)"
}

```

* **Fluxo Interno:**
  1. Recebe o texto.
  2. `AIAssistant` classifica as intenções (Shopping, Task, Reminder).
  3. Executa as operações no banco de dados.
  4. Gera o resumo em texto.

### 2.2. Sincronização de Lembretes (Google Tasks)

**Rota:** `POST /reminders/sync`
**Autenticação:** Proteção por Obscuridade.
**Descrição:** Endpoint passivo chamado periodicamente (ou via gatilho) pelo n8n. Ele recebe a lista atual de tarefas do Google Tasks e sincroniza com o banco local do FamilyOS, garantindo que o Dashboard mostre dados reais.

* **Exemplo de Requisição (JSON vindo do n8n):**
```json
{
  "tasks": [
    {
      "google_id": "Mjkxz...",
      "title": "Consulta Dentista",
      "due": "2026-02-15T14:00:00.000Z",
      "status": "needsAction"
    },
    {
      "google_id": "Abc12...",
      "title": "Comprar Ração",
      "status": "completed"
    }
  ]
}

```

* **Exemplo de Resposta:**
```json
{
  "status": "synced",
  "stats": {
    "received": 2,
    "created": 0,
    "updated": 1,
    "completed_locally": 1
  }
}

```

## 🛒 3. Módulo de Mercado (Shopping)

Endpoints protegidos (`@login_required`) utilizados pela interface web para gestão da lista de compras.

### 3.1. Adicionar Item (Manual com IA)
**Rota:** `POST /shopping/add`
**Autenticação:** Requer Sessão.
**Descrição:** Adiciona um novo item à lista. Diferente de um CRUD comum, este endpoint envia o input do usuário para o `AIAssistant` (Gemini), que:
1.  Normaliza o nome (ex: "leite desnatado" -> "Leite Desnatado").
2.  Define a Categoria correta (ex: LATICÍNIOS).
3.  Gera um Emoji representativo (ex: 🥛).

* **Exemplo de Requisição (JSON):**
```json
  {
    "nome": "Pão de Queijo",
    "quantidade": 2
  }

```

* **Exemplo de Resposta (Sucesso):**
```json
{
  "message": "Adicionado: 2x Pão de Queijo 🥯",
  "status": "success"
}

```

### 3.2. Editar Item

**Rota:** `POST /update_item`
**Autenticação:** Requer Sessão.
**Descrição:** Atualiza as propriedades básicas de um item já existente.

* **Nota:** O campo `quantidade` é forçado para inteiro (int) no backend.
* **Exemplo de Requisição (JSON):**
```json
{
  "id": 42,
  "nome": "Pão de Queijo Tradicional",
  "quantidade": 3
}

```

* **Exemplo de Resposta (Sucesso):**
```json
{
  "status": "success"
}

```

* **Exemplo de Resposta (Erro):**
```json
{
  "error": "Item não encontrado"
}

```

### 3.3. Alternar Status (Check/Uncheck)

**Rota:** `POST /toggle_item/<int:item_id>`
**Autenticação:** Requer Sessão.
**Descrição:** Alterna o estado do item entre `pendente` e `comprado`. Usado quando o usuário clica no checkbox da lista.

* **Exemplo de Requisição:**
`POST https://api.thiagoscutari.com.br/toggle_item/15` (Sem corpo)
* **Exemplo de Resposta:**
```json
{
  "success": true
}

```

### 3.4. Limpar Carrinho (Arquivar)

**Rota:** `POST /clear_cart`
**Autenticação:** Requer Sessão.
**Descrição:** Realiza uma limpeza na lista ("Soft Delete"). Todos os itens marcados como `comprado` têm seu status alterado para `arquivado` e deixam de aparecer na visualização principal.

* **Exemplo de Requisição:**
`POST https://api.thiagoscutari.com.br/clear_cart` (Sem corpo)
* **Exemplo de Resposta:**
```json
{
  "success": true
}
```

## ✅ 4. Módulo de Tarefas (Tasks)

Este módulo gerencia o quadro Kanban (ou lista) de afazeres domésticos, divididos por responsável (Thiago, Debora, Casal).

### 4.1. Visualizar Board (Frontend)
**Rota:** `GET /tasks`
**Autenticação:** Requer Sessão.
**Descrição:** Renderiza a página HTML com as tarefas pendentes e concluídas, agrupadas por responsável.
* **Retorno:** HTML (Template `tasks.html`).

### 4.2. Editar Tarefa
**Rota:** `POST /tasks/update`
**Autenticação:** Requer Sessão.
**Descrição:** Atualiza os detalhes de uma tarefa existente (descrição, responsável ou prioridade).
* **Exemplo de Requisição (JSON):**
```json
  {
    "id": 10,
    "descricao": "Consertar a torneira da cozinha",
    "responsavel": "Thiago",
    "prioridade": "3"
  }

```

* *Legenda Prioridade:* `1` (Normal/Baixa), `2` (Importante/Média), `3` (Urgente/Alta).
* **Exemplo de Resposta:**
```json
{
  "status": "success"
}

```

### 4.3. Concluir/Reabrir Tarefa

**Rota:** `POST /toggle_task/<int:task_id>`
**Autenticação:** Requer Sessão.
**Descrição:** Alterna o status da tarefa entre `pendente` e `concluido`.

* **Exemplo de Requisição:**
`POST https://api.thiagoscutari.com.br/toggle_task/25` (Sem corpo)
* **Exemplo de Resposta:**
```json
{
  "success": true,
  "new_status": "concluido"
}

```

### 4.4. Arquivar Tarefas Concluídas

**Rota:** `POST /clear_tasks`
**Autenticação:** Requer Sessão.
**Descrição:** Realiza o arquivamento em massa. Todas as tarefas com status `concluido` são movidas para `arquivado` e somem do quadro principal.

* **Exemplo de Requisição:**
`POST https://api.thiagoscutari.com.br/clear_tasks` (Sem corpo)
* **Exemplo de Resposta:**
```json
{
  "success": true,
  "archived_count": 5
}

```
## ⏰ 5. Módulo de Lembretes (Reminders)

Este módulo atua como um "espelho" do Google Tasks. Ele exibe os compromissos sincronizados, mas delega a gestão (Criação/Edição/Conclusão) para a integração externa para evitar conflitos de sincronização.

### 5.1. Listar Lembretes (Frontend)
**Rota:** `GET /reminders`
**Autenticação:** Requer Sessão.
**Descrição:** Renderiza a lista cronológica de lembretes ativos.
* **Filtros Aplicados:** Exibe apenas itens com status `needsAction` (pendentes). Itens `completed` são ocultados automaticamente.
* **Ordenação:** Por data de vencimento (`due_date`) ascendente.
* **Retorno:** HTML (Template `reminders.html`).

### 5.2. Gestão de Lembretes (Create/Update/Delete)
* **Via API:** Não existem endpoints públicos manuais para estas ações no FamilyOS.
* **Via Automação:** Utilize a rota de Webhook **`POST /reminders/sync`** (documentada na seção *2. Core Intelligence*) para injetar ou atualizar dados vindos do Google Tasks.
* **Fluxo:**
  1. Usuário cria/conclui tarefa no Google Tasks (Mobile/Web).
  2. n8n detecta o evento.
  3. n8n envia payload para `/reminders/sync`.
  4. FamilyOS atualiza o banco local para visualização.

## 📋 Resumo de Rotas (Cheat Sheet)

Tabela de referência rápida para todas as rotas ativas na versão 2.2.

| Módulo | Método | Rota | Autenticação | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/login` | Pública | Autenticação de usuário |
| **Auth** | `GET` | `/logout` | Session | Encerra sessão |
| **Core** | `POST` | `/voice/process` | Obscura/IP | Cérebro da IA (Voz/Texto) |
| **Core** | `POST` | `/reminders/sync` | Obscura/IP | Sync Google Tasks (via n8n) |
| **Shopping** | `POST` | `/shopping/add` | Session | Add Item (c/ IA Generativa) |
| **Shopping** | `POST` | `/update_item` | Session | Editar Item (Qtd/Nome) |
| **Shopping** | `POST` | `/toggle_item/<id>`| Session | Check/Uncheck Item |
| **Shopping** | `POST` | `/clear_cart` | Session | Arquivar Concluídos |
| **Tasks** | `POST` | `/tasks/update` | Session | Editar Tarefa |
| **Tasks** | `POST` | `/toggle_task/<id>`| Session | Concluir/Reabrir Tarefa |
| **Tasks** | `POST` | `/clear_tasks` | Session | Arquivar Concluídas |
| **View** | `GET` | `/` | Session | Dashboard |
| **View** | `GET` | `/shopping` | Session | Lista de Mercado |
| **View** | `GET` | `/tasks` | Session | Quadro de Tarefas |
| **View** | `GET` | `/reminders` | Session | Lista de Lembretes |
