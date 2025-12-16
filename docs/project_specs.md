# 🏗️ Documento Mestre de Arquitetura: FamilyOS

**Versão:** v2.2 (Omniscient Sync)
**Data da Revisão:** 12/12/2025
**Status:** ✅ Produção (Estável)
**Escopo:** Gestão Doméstica Unificada & Assistente Pessoal Híbrido

---

## 1. Visão Estratégica

### 1.1. O Conceito
O **FamilyOS** é um Sistema Operacional da Casa projetado para centralizar a rotina familiar (Thiago & Débora). Ele atua como um hub central que orquestra dados de diferentes fontes (Google Tasks, APIs de Clima, Input de Voz) e oferece uma interface unificada e simplificada ("Zero Friction").

---

## 2. Módulos Funcionais

### 2.1. 🏠 Dashboard (Hub Central)
O ponto de partida da aplicação.
* **Widget de Clima:** Integração com HG Brasil (via Cache de Banco para evitar Rate Limit). Exibe temperatura, condição e cidade (Itajaí, SC).
* **Mensagem do Dia:** Frase inspiracional ou informativa rotativa.
* **Acesso Rápido:** Cards de navegação para os outros módulos com badges de contagem de pendências.

### 2.2. 🛒 Mercado (Shopping)
Gestão inteligente de suprimentos.
* **Categorização:** Itens são organizados automaticamente (Hortifrúti, Padaria, Limpeza, etc.).
* **Input:** Via Interface Web, Voz ou Texto.
* **UX:** Checkbox circular grande para marcar comprados. Botão de "Limpar Carrinho" move itens para histórico.

### 2.3. ✅ Tarefas (Tasks)
Quadro de afazeres domésticos focados em execução.
* **Atribuição Inteligente:** O sistema define o responsável automaticamente:
    * *"Thiago precisa..."* ➝ Responsável: **Thiago**.
    * *"Nós precisamos..."* ➝ Responsável: **Casal**.
* **Priorização:** Classificação visual (🔴 Alta, 🟡 Média, 🟢 Baixa).

### 2.4. 🔔 Lembretes (Google Sync) **[NOVO - Sprint 9]**
Módulo de agenda e compromissos com data marcada.
* **Sincronização Bidirecional:** Integração total com **Google Tasks** e **Google Calendar**.
    * O que é criado no Google aparece no FamilyOS.
    * O que é concluído/deletado no Google some do FamilyOS.
* **Batch Processing:** O sistema recebe e processa listas inteiras de tarefas de uma só vez para alta performance.
* **Gatilho Manual:** Botão "Sincronizar Agora" na interface que dispara o Webhook do n8n.

---

## 3. Arquitetura de Infraestrutura

O projeto segue uma arquitetura moderna baseada em microsserviços containerizados, com fluxos distintos para desenvolvimento e produção.

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

## 4. Stack Tecnológico

### 4.1. Front-End
* **Linguagem:** HTML5, CSS3 (Vanilla), JavaScript (ES6).
* **Template Engine:** Jinja2 (Server-side rendering).
* **Design System:** Tema "Cyberpunk Dark Neon".
    * Cores: Deep Void (`#050509`), Neon Purple (`#611af0`), Neon Green (`#22ff7a`).
    * Componentes: Cards translúcidos (Glassmorphism), Inputs customizados, Badges dinâmicos.
* **Interatividade:**
    * **Long Press (800ms):** Abre modais de edição.
    * **Vibração (Haptic Feedback):** Ao concluir tarefas.
    * **Optimistic UI:** Atualiza a tela antes da resposta do servidor.

### 4.2. Back-End
* **Framework:** Python Flask.
* **ORM:** SQLAlchemy.
* **Servidor WSGI:** Gunicorn (Produção).
* **Rotas Críticas:**
    * `POST /voice/process`: Recebe transcrição de áudio, usa Gemini para categorizar e insere no banco.
    * `POST /reminders/sync`: Endpoint inteligente que aceita listas puras (`[...]`) do n8n para sincronia em massa.
    * `POST /chat/process`: (Em desenvolvimento) Interface de chat ativo.

### 4.3. Banco de Dados (PostgreSQL)
Schema Relacional Normalizado.

**Tabela: `reminders` (Atualizada)**
| Coluna | Tipo | Função |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | Identificador local. |
| `google_id` | VARCHAR | ID da tarefa no Google (Link de Sync). |
| `title` | VARCHAR | Título do compromisso. |
| `notes` | TEXT | Detalhes ou link para e-mail. |
| `due_date` | TIMESTAMP | Data e hora do vencimento. |
| `status` | VARCHAR | 'needsAction' ou 'completed'. |
| `usuario` | VARCHAR | Quem criou/sincronizou. |
| `last_updated` | TIMESTAMP | Controle de versão. |

---

## 5. Automação e IA (O Cérebro)

### 5.1. Fluxo de Sincronização (Google Tasks ↔ FamilyOS)
Para resolver problemas de performance e timeouts, a arquitetura de sync foi refinada:
1.  **Gatilho:** Cron (a cada 30min) OU Botão Manual no Front.
2.  **n8n (Extração):** Node "Google Tasks" baixa todas as tarefas pendentes.
3.  **n8n (Agregação):** Node "Item Lists" (Aggregate) compila as tarefas em uma única lista JSON (`tasks: [...]`).
4.  **Envio:** Um único POST HTTP envia o pacote para o Python.
5.  **Python:** Processa a lista, cria o que não existe, atualiza o que mudou e remove (Soft/Hard delete) o que foi concluído.

### 5.2. Processamento de Linguagem Natural (Gemini 2.5)
O sistema não usa comandos rígidos ("Adicionar X em Y"). Ele entende intenção:
* *Input:* "Lavar o carro e a reunião com a diretoria é amanhã às 14h."
* *Processamento:* O Gemini separa em:
    1.  **Task:** "Lavar o carro" (Prio: Média, Resp: Thiago).
    2.  **Reminder:** "Reunião Diretoria" (Data: Amanhã 14:00).

---

## 6. Próximos Passos (Roadmap)

* [ ] **Módulo Chatbot:** Implementar interface de chat real-time (`chat.html`) substituindo o log estático.
* [ ] **IA Ativa:** Permitir que o sistema pergunte coisas ("Você já comprou o leite que estava na lista?").
* [ ] **Multi-usuário:** Refinar permissões para uso simultâneo intenso.

---
**Autor:** Thiago Scutari & FamilyOS AI
**Documentação Gerada Automaticamente**