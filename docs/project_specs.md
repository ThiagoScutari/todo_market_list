# 🏗️ Documento Mestre de Arquitetura: FamilyOS

**Versão:** v2.1 (The Home OS)
**Data da Revisão:** 05/12/2025
**Status:** ✅ Produção (Operacional)
**Escopo:** Gestão Doméstica Unificada (Compras, Tarefas, Clima)

---

## 1. Visão Estratégica

### 1.1. O Conceito "FamilyOS"
O sistema evoluiu de uma lista de compras para um **Sistema Operacional da Casa**. Ele centraliza informações vitais e atua proativamente na organização da rotina familiar através de um Dashboard central.

### 1.2. Módulos do Sistema
1.  **🏠 Dashboard:** Painel visual com Clima (Itajaí), Mensagem do Dia e Acesso Rápido.
2.  **🛒 Mercado (Shopping):** Gestão de suprimentos com categorização automática.
3.  **✅ Tarefas (Tasks):** Gestão de afazeres com:
    * Atribuição automática (Thiago, Débora, Casal).
    * Classificação de Prioridade (Baixa🟢, Média🟡, Alta🔴).
    * Processamento de múltiplas tarefas em uma única mensagem.
4.  **⏰ Futuro:** Ingredientes e Lembretes (Placeholders na UI).

---

## 2. Arquitetura de Informação (UX/UI)

### 2.1. Estrutura de Navegação
A aplicação agora utiliza uma arquitetura de **Base Template** com navegação inferior fixa.

* **Rota \`/\` (Dashboard):**
    * Widget de Clima (API HG Brasil com Cache).
    * Frase Inspiracional.
    * Botões de Acesso Rápido com Badges de Notificação (Pendências).
* **Rota \`/shopping\` (Mercado):** Lista clássica com checkboxes e edição via Long Press.
* **Rota \`/tasks\` (Tarefas):** Quadro de tarefas agrupado por Responsável.

---

## 3. Regras de Negócio e Inteligência (n8n + Gemini)

### 3.1. Roteamento de Intenção (n8n Router)
O n8n atua como triagem inicial. Um LLM analisa o texto/áudio e decide a rota:
* **SHOPPING:** *"Comprar pão"* -> Posta em \`/magic\`.
* **TASK:** *"Lavar o carro"* -> Posta em \`/tasks/magic\`.

### 3.2. Lógica de Tarefas (NLP Avançado)
O endpoint \`/tasks/magic\` utiliza o Google Gemini 2.5 Flash para extrair uma **Lista de Objetos**:

1.  **Multi-Tasking:** Uma mensagem como *"Lavar o carro e comprar remédio"* gera ações distintas.
2.  **Atribuição de Responsável:**
    * Explícito: *"Thiago lavar louça"* -> Thiago.
    * Coletivo: *"Temos que ir..."* -> Casal.
    * Implícito: Se não citado, atribui ao remetente do Telegram.
3.  **Prioridade:** Análise semântica de urgência ("agora", "hoje", "sem falta" = Alta).

---

## 4. Banco de Dados (Schema v2.1 - PostgreSQL)

O sistema migrou de SQLite para **PostgreSQL 15** rodando em Docker.

### 4.1. Tabela \`tasks\`
| Campo | Tipo | Detalhes |
| :--- | :--- | :--- |
| \`id\` | Integer | PK |
| \`descricao\` | String | O que fazer. |
| \`responsavel\` | String | 'Thiago', 'Debora', 'Casal'. |
| \`prioridade\` | Integer | 1 (Verde), 2 (Amarelo), 3 (Vermelho). |
| \`status\` | String | 'pendente', 'concluido', 'arquivado'. |
| \`created_at\` | DateTime | Data de criação. |

### 4.2. Tabela \`weather_cache\`
Cache para evitar rate-limit da API HG Brasil.
| Campo | Tipo | Detalhes |
| :--- | :--- | :--- |
| \`id\` | Integer | PK |
| \`city\` | String | 'Itajai,SC'. |
| \`data_json\` | Text | JSON completo da API. |
| \`last_updated\` | DateTime | Atualiza se > 60 min. |

*(As tabelas \`users\`, \`lista_itens\`, \`produtos\` e \`categorias\` permanecem iguais à v1.2)*

---

## 5. Infraestrutura e Deploy

### 5.1. Docker Compose (Híbrido)
* **Produção (VPS):** Roda App (Flask), Banco (Postgres), Traefik e n8n na mesma rede.
* **Desenvolvimento (Local):** Docker roda apenas o Banco de Dados. Python roda localmente para debug.

### 5.2. Variáveis de Ambiente (.env)
Novas chaves adicionadas:
\`\`\`bash
# Postgres
DB_USER=family_user
DB_PASSWORD=***
DATABASE_URL=postgresql://...

# API Externa
HGBRASIL_KEY=***
\`\`\`

---

## 6. Roadmap de Execução

| Sprint | Foco | Status |
| :--- | :--- | :--- |
| **Sprint 7** | Persistência e Base IA | ✅ Concluído |
| **Sprint 8** | Módulo Tarefas e Postgres | ✅ Concluído |
| **Sprint 9** | Dashboard e Clima | ✅ Concluído |
| **Sprint 10** | Refinamento de Lembretes | 🔮 Futuro |

---
# Sprint 9

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

**Autor:** Thiago Scutari.