### 🏗️ Arquitetura do Módulo Lembretes | Sprint 9

#### 1\. A Estratégia de Sincronização (Sync)

Para manter o sistema rápido e o Python leve, usaremos o padrão **"Espelhamento via Banco de Dados"**:

1.  **Leitura Rápida:** O FamilyOS lê uma tabela local `reminders` no Postgres (instantâneo).
2.  **Sincronização (Download):** O n8n roda a cada X minutos (polling) ou via Webhook, busca tarefas no Google Tasks e atualiza o Postgres.
3.  **Criação/Edição (Upload):** Quando você cria/edita no FamilyOS, o Python salva no Postgres e chama um Webhook do n8n para empurrar essa mudança para o Google.

#### 2\. Integração com Gmail

O Google Tasks já é nativamente integrado ao Gmail.

  * **Fluxo:** Se você marcar um e-mail como "Adicionar às Tarefas" no Gmail, ele aparece no Google Tasks.
  * **No FamilyOS:** Como estaremos espelhando o Google Tasks, esses e-mails aparecerão automaticamente na sua lista de Lembretes com um ícone de 📧 e o link para abrir o e-mail.

-----

## 🆕 Módulo: Lembretes (Google Tasks Sync)

### Visão Geral
Gerenciamento de compromissos com data e hora marcadas, sincronizados bidirecionalmente com o Google Tasks.

### Regras de Negócio
1.  **Fonte da Verdade Híbrida:** O sistema aceita alterações tanto do FamilyOS quanto do Google Apps.
2.  **Agendamento:** Obrigatório ter Data. Hora é opcional (Dia inteiro).
3.  **Vínculo com Gmail:** Se a tarefa vier de um e-mail, deve exibir um link "Abrir Gmail".
4.  **Notificações:** O próprio app do Google Tasks no celular cuidará dos push notifications (nós não precisamos recriar isso).

### Banco de Dados: Tabela `reminders`
| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | Integer (PK) | ID Interno. |
| `google_id` | String (Unique) | ID da tarefa no Google (para sync). |
| `title` | String | Título do lembrete. |
| `notes` | Text | Detalhes ou Link do Gmail. |
| `due_date` | DateTime | Data/Hora de vencimento. |
| `status` | String | 'needsAction' (pendente) ou 'completed'. |
| `last_sync` | DateTime | Quando foi atualizado pela última vez. |

-----

#### 2\. `api_docs.md` (Novas Rotas)

O Python precisará de endpoints para gerenciar isso localmente e acionar o n8n.

```markdown
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
```

-----

#### 3\. Frontend & UX (`frontend_docs.md`)

  * **Local:** Aba nova `/reminders` ou Widget no Dashboard.
  * **Visual:** Cards com destaque para a **Data/Hora**.
      * **Hoje:** Destaque Amarelo.
      * **Atrasado:** Destaque Vermelho.
      * **Futuro:** Texto Branco.
  * **Ícones:** Se tiver link do Gmail, mostrar ícone de carta.

-----

### ⚔️ Estratégia de Desenvolvimento (Passo a Passo)

Para não quebrarmos o que já existe, faremos assim:

1.  **Fase 1: Preparação (n8n & Google)**

      * Configurar credenciais do Google Tasks no n8n.
      * Criar um Workflow no n8n: "Sync Google -\> Postgres".
      * Testar se o n8n consegue ler suas tarefas e gravar no banco do FamilyOS.

2.  **Fase 2: Backend (Python)**

      * Criar o modelo `Reminder` no `app.py`.
      * Criar a rota de listagem (`/reminders`).

3.  **Fase 3: Frontend (Visual)**

      * Criar o template `reminders.html`.
      * Adicionar o Widget de Lembretes no Dashboard (substituindo o placeholder opaco).

4.  **Fase 4: Criação e Edição**

      * Implementar o modal de criar tarefa que chama o n8n para enviar pro Google.


---

# 🚀 Planejamento Sprint 10 (Parte 2): O Hub de Notificações

**Objetivo:** Transformar o FamilyOS em um assistente proativo, centralizando eventos críticos no Google Tasks e implementando notificações ativas (E-mail).

---

## 1. Visão Estratégica: Google Tasks como "Hub Central"

Para evitar ter que olhar em dois lugares (App FamilyOS + Agenda do Google), adotaremos a seguinte regra de ouro:

> **"Se tem data marcada ou é urgente, deve estar no Google Tasks."**

### Fluxo de Dados Unificado
1.  **Lembretes (Reminders):** Nascem e vivem no Google Tasks. O FamilyOS apenas espelha.
2.  **Tarefas Críticas (Tasks):** Nascem no FamilyOS. Se forem marcadas como **🔴 Alta Prioridade** ou atribuídas ao **👥 Casal**, o sistema cria automaticamente uma cópia no Google Tasks para garantir visibilidade.

---

## 2. Roteiro de Implementação (Passo a Passo)

Seguiremos esta ordem para garantir que a infraestrutura suporte as funcionalidades.

### ✅ Fase 1: Edição de Lembretes (Frontend & Backend)
*Permitir alterar data, hora e descrição de um lembrete direto pelo FamilyOS.*

1.  **Backend (`app.py`):**
    * Criar rota `POST /reminders/update`.
    * *Lógica:* Atualiza o banco local Postgres **E** dispara um Webhook para o n8n atualizar o Google Tasks (para manter a sincronia).
2.  **Frontend (`reminders.html`):**
    * Criar Modal de Edição (Estilo Cyberpunk).
    * Implementar Long Press nos cards de lembrete.

### 🗣️ Fase 2: Criação via Voz (Telegram -> n8n -> Google)
*Permitir criar lembretes falando: "Lembrar de pagar a luz dia 15".*

1.  **n8n (Inteligência):**
    * Atualizar o **Classificador IA** para detectar 3 intenções: `SHOPPING`, `TASK`, `REMINDER`.
2.  **n8n (Fluxo Reminder):**
    * Novo caminho no Switch.
    * Nó de IA para extrair: **Título**, **Data** e **Hora** da frase.
    * Nó Google Tasks: Cria a tarefa direto no Google.
    * *Nota:* O sync automático de 10min trará esse lembrete para o FamilyOS depois.

### 🔄 Fase 3: Sincronização Estratégica (Tarefas -> Google)
*Fazer com que tarefas importantes do FamilyOS apareçam na sua agenda.*

1.  **Backend (`app.py`):**
    * Alterar a função `tasks_magic` (Criação de Tarefa).
    * **Regra de Negócio:** Se `prioridade == 3` (Alta) OU `responsavel == 'Casal'`:
        * Disparar Webhook para o n8n criar uma cópia no Google Tasks.
        * Salvar o `google_id` na tabela de tarefas para referência futura.

### 📧 Fase 4: O "Briefing Matinal" (E-mail)
*Receber um resumo do dia por e-mail.*

1.  **n8n (Workflow Agendado):**
    * **Trigger:** Todo dia às 07:00.
    * **Ação:** Listar tarefas do Google Tasks com `due_date` = Hoje.
    * **Ação:** Listar tarefas do FamilyOS com `prioridade` = Alta.
    * **Ação:** Enviar e-mail formatado (HTML) para Thiago e Débora com o resumo.

---

## 3. Arquitetura de Dados Necessária

Não precisamos criar tabelas novas, mas vamos precisar de **novos Webhooks no n8n** para servir de ponte para o Python.

### Novos Webhooks (n8n)
1.  `POST /webhook/google-tasks/update`
    * **Recebe:** `{ google_id, title, notes, due }`
    * **Ação:** Atualiza a tarefa no Google.
2.  `POST /webhook/google-tasks/create`
    * **Recebe:** `{ title, notes, due }`
    * **Ação:** Cria tarefa no Google.

---

## 4. Definição de Pronto (DoD)

* [ ] Consigo editar um lembrete no site e a mudança aparece no app do Google Tasks.
* [ ] Mando um áudio "Lembrar dentista amanhã" e ele aparece na lista de Lembretes.
* [ ] Crio uma tarefa "Urgente" e ela aparece no meu Google Tasks.
* [ ] Recebo um e-mail teste com o resumo das pendências.
