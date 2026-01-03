# 📝 FamilyOS - Project Specifications

**Versão:** 2.2 (Omniscient Sync + AI Core)
**Data de Atualização:** 02/01/2026
**Status:** Em Produção (Estável)

---

## 1. Visão Geral do Projeto
O **FamilyOS** é um sistema de gestão doméstica centralizado ("Second Brain"), projetado para reduzir a carga cognitiva familiar. Ele unifica listas de compras, tarefas e lembretes em uma interface minimalista, alimentada por Inteligência Artificial para processamento de linguagem natural.

### 1.1. Filosofia "Single Source of Truth" (Fonte Única da Verdade)
A arquitetura do sistema baseia-se no conceito de **IA Centralizada**. O serviço `AIAssistant` (baseado no Gemini) atua como o núcleo único de interpretação de intenções.

Isso significa que todo input no sistema — seja um comando de voz complexo enviado via Telegram ou uma adição manual rápida pelo Web App — é processado pelo mesmo motor de inteligência. Isso garante consistência absoluta na categorização, geração de emojis e padronização de dados em todos os módulos.

---

## 2. Arquitetura Técnica

### 2.1. Backend (Core)
* **Linguagem:** Python 3.11+
* **Framework:** Flask (Blueprints: Auth, Main, API, Webhook)
* **Banco de Dados:** PostgreSQL (SQLAlchemy ORM)
* **IA Engine:** `AIAssistant` Service (Google Gemini 2.5 Flash)
* **Gerenciador de Processos:** Gunicorn (Produção)

### 2.2. Frontend (Interface)
* **Renderização:** Server-Side (Jinja2)
* **Estilização:** CSS Customizado (Cyberpunk/Glassmorphism Clean) + Bootstrap Icons
* **Interatividade:** Vanilla JS (Fetch API) para operações assíncronas (AJAX)

### 2.3. Integrações Externas
* **n8n (Automação):** Hub central para Webhooks de Voz (Telegram/Whisper) e Sincronização de Lembretes (Google Tasks).
* **HG Brasil:** API de Clima para o Dashboard.
* **Google Tasks:** Fonte autoritativa para Lembretes.

---

## 3. Ambientes de Desenvolvimento

### 3.1. Ambiente de Homologação (Dev Local)
Focado em agilidade e debug.
1.  **IDE:** VSCode com extensões Python/Jinja2.
2.  **Container:** Docker roda apenas o **PostgreSQL** localmente.
3.  **Backend:** O Flask (`app.py`) roda nativamente na máquina para permitir debug em tempo real.
4.  **Túnel:** **Ngrok** expõe a porta 5000 para receber Webhooks do n8n/Telegram durante testes.
5.  **Testes de API:** **Postman** utilizado para validar payloads JSON brutos antes da implementação no n8n.
6.  **Automação:** Instância de n8n (pode ser local ou a da VPS apontando para o Ngrok).
7.  **Versionamento:** Git (Branch `develop` ou `feature/*`).

### 3.2. Ambiente de Produção (VPS)
Focado em estabilidade e segurança.
1.  **Hospedagem:** VPS Linux (CentOS/AlmaLinux).
2.  **Orquestração:** **Docker Compose** gerenciando todo o stack na rede `familyos_net`.
    * `familyos-app`: Container Python/Gunicorn.
    * `familyos-db`: Container PostgreSQL 15 (Alpine).
    * `n8n`: Orquestrador de automação.
    * `traefik`: Reverse Proxy e Gestão de Certificados SSL (HTTPS).
3.  **Deploy:** Via Git Pull (`origin main`) + Docker Build.
4.  **Integrações Externas:**
    * **Google Tasks API:** Via Credenciais Cloud Console (OAuth2 gerenciado pelo n8n).
    * **Google Calendar API:** Via Credenciais Cloud Console (OAuth2 gerenciado pelo n8n).
    * **Google Gemini (IA):** Processamento de Linguagem Natural.
    * **HG Brasil:** Dados meteorológicos.
    * **OpenAI:** Whisper.

---

## 4. Módulos Funcionais

### 🛒 4.1. Mercado (Shopping)
Gerenciamento inteligente de lista de compras.
* **Input Inteligente:** Adição de itens via texto (App) ou voz (Telegram) passa pela IA para inferir:
    * **Categoria:** (ex: "Maçã" -> HORTIFRÚTI)
    * **Emoji:** (ex: "Maçã" -> 🍎)
    * **Quantidade:** Suporte nativo a inteiros (ex: "2x Leite").
* **Funcionalidades:**
    * Listagem agrupada por categorias.
    * Edição rápida (Long Press) com sanitização de nome.
    * Check/Uncheck e Arquivamento em massa ("Limpar Carrinho").

### ✅ 4.2. Tarefas (Tasks)
Quadro Kanban para afazeres domésticos não agendados.
* **Estrutura:** Dividido por Responsável (Thiago, Debora, Casal).
* **Prioridade:** Sistema visual de urgência (Alta/Média/Baixa).
* **Funcionalidades:**
    * Visualização e Conclusão de tarefas.
    * Edição de responsável e prioridade.
    * Arquivamento de tarefas concluídas.

### ⏰ 4.3. Lembretes (Reminders)
Visualizador unificado de compromissos datados.
* **Modelo de Dados:** Espelho (*Mirror*) do Google Tasks.
* **Política "Read-Only":** O Frontend do FamilyOS serve apenas para **visualização**.
    * **Criação/Edição:** Deve ser feita via Google Tasks (Mobile/Web) ou Comando de Voz (que delega para o Google).
    * **Sincronização:** Via Webhook (`/reminders/sync`) acionado pelo n8n.

### 📊 4.4. Dashboard
Painel central de "Situação do Dia".
* **Saudação:** Personalizada com Clima atual (Itajaí, SC).
* **Resumo:** Contadores de pendências (Compras, Tarefas, Lembretes).
* **Inspiração:** Frase do dia aleatória.

---

## 5. Fluxos de Dados (Data Flow)

### 5.1. Fluxo de Input Manual (Shopping)
1.  Usuário digita "2 Pão de Queijo" no App.
2.  Frontend envia POST `/shopping/add`.
3.  Backend invoca `AIAssistant`.
4.  IA processa -> JSON: `{ "nome": "Pão de Queijo", "qty": 2, "cat": "PADARIA", "emoji": "🥯" }`.
5.  Backend salva no Banco.
6.  Frontend recarrega.

### 5.2. Fluxo de Sincronização (Lembretes)
1.  Alteração ocorre no Google Tasks.
2.  n8n detecta evento e envia Payload para POST `/reminders/sync`.
3.  Backend atualiza/insere registros na tabela `reminders`.
4.  Próximo acesso ao Dashboard reflete a mudança.

---

## 6. Estrutura de Banco de Dados (Resumo)

* **Users:** `id, username, password_hash`
* **Shopping (ListaItem):** `id, produto_id, quantidade (int), status, usuario`
    * **Produto:** `id, nome, emoji, categoria_id`
    * **Categoria:** `id, nome`
* **Tasks:** `id, descricao, responsavel, prioridade, status`
* **Reminders:** `id, google_id, title, due_date, status`
* **WeatherCache:** `city, data_json, last_updated`

---

## 7. Roadmap Futuro (Backlog)

* **[Sprint 10] Refinamento de Lembretes:** Melhorar a visualização de datas (Hoje, Amanhã, Próximos) no Dashboard.
* **[Sprint 11] Gestão de Estoque:** Mover itens comprados para uma "Despensa Virtual".
* **[Sprint 12] Multi-usuário:** Refinar permissões e visualizações por usuário logado.