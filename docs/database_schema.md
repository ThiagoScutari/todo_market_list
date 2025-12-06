### 📄 Arquivo: `docs/database_schema.md`

**Onde salvar:** Na pasta `docs/` do projeto.

````markdown
# 🗄️ Documentação do Banco de Dados (FamilyOS)

**SGBD:** PostgreSQL 15 (Alpine)
**Driver:** `psycopg2-binary` + SQLAlchemy ORM
**Encoding:** UTF-8
**Timezone:** America/Sao_Paulo

---

# 🗄️ Documentação do Banco de Dados (FamilyOS)

**SGBD:** PostgreSQL 15 (Alpine)
**Driver:** `psycopg2-binary` + SQLAlchemy ORM
**Encoding:** UTF-8
**Timezone:** America/Sao_Paulo

---

## 1. Diagrama Entidade-Relacionamento (DER)

![Diagrama](/projects/todo_market_list/images/DER.png)

-----

## 2\. Dicionário de Dados

### 👤 Tabela: `users`

Armazena as credenciais de acesso ao Web App.

  * **id** `(INTEGER, PK)`: Identificador único.
  * **username** `(VARCHAR(80), UNIQUE)`: Login (ex: 'thiago').
  * **password\_hash** `(VARCHAR(256))`: Hash da senha gerado pelo Werkzeug.

### 📂 Tabela: `categorias`

Categorização dos produtos para ordenar a lista de compras.

  * **id** `(INTEGER, PK)`: Identificador.
  * **nome** `(VARCHAR(50), UNIQUE)`: Nome da seção (ex: 'HORTIFRÚTI', 'CARNES').

### 📏 Tabela: `unidades_medida`

Unidades padrão para normalização de quantidades.

  * **id** `(INTEGER, PK)`: Identificador.
  * **nome** `(VARCHAR(20))`: Nome extenso (ex: 'Litro').
  * **simbolo** `(VARCHAR(5))`: Abreviação usada na interface (ex: 'L', 'un', 'kg').

### 🍎 Tabela: `produtos`

Catálogo de itens conhecidos pelo sistema (para autocompletar emojis e categorias).

  * **id** `(INTEGER, PK)`: Identificador.
  * **nome** `(VARCHAR(100))`: Nome normalizado (minúsculas).
  * **emoji** `(VARCHAR(10))`: Ícone visual (ex: '🍎').
  * **categoria\_id** `(INTEGER, FK)`: Referência à tabela `categorias`.
  * **unidade\_padrao\_id** `(INTEGER, FK)`: Referência à `unidades_medida` (opcional).

### 🛒 Tabela: `lista_itens` (Core do Mercado)

Representa a lista de compras ativa e o histórico.

  * **id** `(INTEGER, PK)`: Identificador.
  * **produto\_id** `(INTEGER, FK)`: O item sendo comprado.
  * **quantidade** `(FLOAT)`: Quantia a comprar.
  * **unidade\_id** `(INTEGER, FK)`: Unidade específica desta compra.
  * **usuario** `(VARCHAR(50))`: Nome do usuário que solicitou (via Telegram).
  * **status** `(VARCHAR(20))`:
      * `'pendente'`: Na lista para comprar.
      * `'comprado'`: Marcado no carrinho (riscado).
      * `'finalizado'`: Arquivado (histórico).
  * **adicionado\_em** `(DATETIME)`: Data de criação.
  * **origem\_input** `(VARCHAR(100))`: Metadado (ex: 'telegram\_voice').

### ✅ Tabela: `tasks` (Core de Tarefas)

Gerenciamento de afazeres domésticos.

  * **id** `(INTEGER, PK)`: Identificador.
  * **descricao** `(VARCHAR(200))`: O que deve ser feito.
  * **responsavel** `(VARCHAR(50))`: Quem executará ('Thiago', 'Debora', 'Casal').
  * **prioridade** `(INTEGER)`:
      * `1`: Baixa (Verde).
      * `2`: Média (Amarelo).
      * `3`: Alta (Vermelho).
  * **status** `(VARCHAR(20))`: 'pendente', 'concluido', 'arquivado'.
  * **created\_at** `(DATETIME)`: Data de criação.

### ⛅ Tabela: `weather_cache`

Cache temporário para dados da API HG Brasil.

  * **id** `(INTEGER, PK)`: Identificador.
  * **city** `(VARCHAR(50))`: Chave de busca (ex: 'Itajai,SC').
  * **data\_json** `(TEXT)`: O JSON bruto retornado pela API externa.
  * **last\_updated** `(DATETIME)`: Carimbo de tempo para cálculo de TTL (Time-To-Live).

-----

## 3\. Permissões e Segurança

O banco de dados roda isolado dentro da rede Docker (`familyos_net`), não acessível publicamente pela internet.

### Usuários do Banco (Roles)

  * **`family_user` (Owner):** \* Usuário principal definido no `.env` (`DB_USER`).
      * Possui permissão total (DDL e DML) no banco `familyos_db`.
      * Utilizado pela aplicação Python (SQLAlchemy) para migrações e operações.

### Conexão

A string de conexão é montada dinamicamente via variáveis de ambiente:
`postgresql://{DB_USER}:{DB_PASSWORD}@{HOST}:5432/{DB_NAME}`

-----

## 4\. Persistência e Backup

Os dados residem em um **Volume Docker** para garantir que sobrevivam à reinicialização ou atualização dos containers.

  * **Caminho no Container:** `/var/lib/postgresql/data`
  * **Mapeamento Local (Dev):** `./postgres_data_local`
  * **Mapeamento VPS (Prod):** `/opt/n8n-traefik/postgres_data`

**Estratégia de Backup Sugerida:**
Dump diário do container Postgres:

```bash
docker exec -t familyos_db pg_dumpall -c -U family_user > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql
```

```

---

Este documento cobre tudo: a estrutura visual, a descrição técnica campo a campo e como a segurança funciona. Salve-o como `docs/database_schema.md`.
```