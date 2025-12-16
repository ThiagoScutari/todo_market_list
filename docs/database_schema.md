# 🗄️ Documentação do Banco de Dados (FamilyOS)

**Versão:** v2.2 (Omniscient Sync)
**SGBD:** PostgreSQL 15 (Alpine)
**Driver:** `psycopg2-binary` + SQLAlchemy ORM
**Encoding:** UTF-8
**Timezone:** America/Sao_Paulo

---

## 1. Diagrama Entidade-Relacionamento (DER)

![Diagrama](/projects/todo_market_list/images/DER.png)

---

## 2. Dicionário de Dados

Abaixo estão as definições exatas das tabelas em produção.

### 👤 Tabela: `users`
Armazena as credenciais de acesso ao Web App.

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **username** | `varchar` | 80 | Não | Login único (ex: 'thiago'). |
| **password_hash** | `varchar` | 256 | Não | Hash da senha (Werkzeug). |

### 📂 Tabela: `categorias`
Categorização dos produtos para ordenar a lista de compras.

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **nome** | `varchar` | 50 | Não | Nome da seção (ex: 'HORTIFRÚTI'). |

### 📏 Tabela: `unidades_medida`
Unidades padrão para normalização de quantidades.

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **nome** | `varchar` | 20 | Não | Nome extenso (ex: 'Litro'). |
| **simbolo** | `varchar` | 5 | Não | Abreviação (ex: 'L', 'un', 'kg'). |

### 🍎 Tabela: `produtos`
Catálogo de itens conhecidos (memória do sistema).

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **nome** | `varchar` | 100 | Não | Nome do produto. |
| **emoji** | `varchar` | 10 | Sim | Ícone visual. |
| **categoria_id** | `integer` | - | Sim | FK para `categorias`. |
| **unidade_padrao_id** | `integer` | - | Sim | FK para `unidades_medida`. |

### 🛒 Tabela: `lista_itens` (Core do Mercado)
Itens da lista de compras ativa e histórico.

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **produto_id** | `integer` | - | Sim | FK para `produtos`. |
| **quantidade** | `double` | - | Não | Quantidade a comprar. |
| **unidade_id** | `integer` | - | Sim | FK para `unidades_medida`. |
| **usuario** | `varchar` | 50 | Sim | Quem solicitou. |
| **status** | `varchar` | 20 | Sim | 'pendente', 'comprado', 'finalizado'. |
| **adicionado_em** | `timestamp` | - | Sim | Data de criação. |
| **origem_input** | `varchar` | 100 | Sim | Fonte (ex: 'omniscient'). |

### ✅ Tabela: `tasks` (Core de Tarefas)
Gerenciamento de afazeres domésticos simples (Kanban).

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **descricao** | `varchar` | 200 | Não | O que fazer. |
| **responsavel** | `varchar` | 50 | Sim | 'Thiago', 'Debora', 'Casal'. |
| **prioridade** | `integer` | - | Sim | 1 (Baixa) a 3 (Alta). |
| **status** | `varchar` | 20 | Sim | 'pendente', 'concluido', 'arquivado'. |
| **created_at** | `timestamp` | - | Sim | Data de criação. |

### 🔔 Tabela: `reminders` (Novo - Sprint 9)
Sincronização bidirecional com Google Tasks.

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **google_id** | `varchar` | 100 | Sim | ID da Task no Google (Sync). |
| **calendar_id** | `varchar` | 100 | Sim | ID da Lista/Calendário no Google. |
| **parent_id** | `varchar` | 100 | Sim | ID da tarefa pai (se subtarefa). |
| **title** | `varchar` | 200 | Não | Título do lembrete. |
| **notes** | `text` | - | Sim | Detalhes ou Link do Gmail. |
| **due_date** | `timestamp` | - | Sim | Data de vencimento. |
| **status** | `varchar` | 20 | Sim | 'needsAction' ou 'completed'. |
| **usuario** | `varchar` | 50 | Sim | Origem ('Google' ou User). |
| **updated_at** | `timestamp` | - | Sim | Controle de versão. |

### ⛅ Tabela: `weather_cache`
Cache para evitar rate-limit da API de Clima.

| Coluna | Tipo | Max | Null | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **id** | `integer` | - | Não | Chave Primária (PK). |
| **city** | `varchar` | 50 | Sim | Chave de busca (ex: 'Itajai,SC'). |
| **data_json** | `text` | - | Sim | JSON bruto da API externa. |
| **last_updated** | `timestamp` | - | Sim | Data da última atualização. |

---

## 3. Permissões e Segurança

O banco de dados roda isolado dentro da rede Docker (`familyos_net`), sem exposição pública de porta (5432) para a internet.

### Conexão
A string de conexão é montada dinamicamente via variáveis de ambiente no container da aplicação:
`postgresql://{DB_USER}:{DB_PASSWORD}@familyos-db:5432/{DB_NAME}`

---

## 4. Persistência e Backup

Os dados residem em um **Volume Docker** gerenciado (`postgres_data`).

**Estratégia de Backup:**
O dump deve ser executado periodicamente via CRON na VPS:
```bash
docker exec -t familyos_db pg_dumpall -c -U family_user > /backups/db_backup_$(date +%F).sql