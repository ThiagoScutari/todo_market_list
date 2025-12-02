# Documento Mestre de Arquitetura: FamilyOS

**Versão:** v1.2 (Stable Persistence)
**Data da Última Atualização:** 02/12/2025
**Status:** ✅ Produção (Operacional)

---

## 1. Introdução

### 1.1. Propósito
Este documento estabelece a arquitetura técnica, regras de negócio e infraestrutura do sistema **FamilyOS**. Ele serve como fonte única da verdade para manutenção e evolução do projeto, substituindo todas as versões anteriores.

### 1.2. Escopo Atual
O sistema opera como um assistente de gestão doméstica focado em **Compras de Mercado**.
* **Entrada:** Áudio/Texto via Telegram (Zero UI).
* **Processamento:** IA Generativa para estruturação de dados.
* **Saída:** Web App Mobile-First para uso no supermercado (Rich UI).

---

## 2. Visão Geral da Arquitetura

O sistema segue uma arquitetura de microsserviços containerizados orquestrados via Docker Compose.

### 2.1. Diagrama de Fluxo
\`\`\`
[USUÁRIO] 🗣️ Áudio/Texto
    ⬇
[TELEGRAM]
    ⬇
[n8n] (Orquestrador)
    │ • Recebe Webhook
    │ • Baixa Áudio
    │ • Transcreve (Whisper)
    ⬇
[API FAMILYOS] (Flask/Python) ◀─── [GOOGLE GEMINI PRO] (Inteligência)
    │ • Recebe JSON
    │ • Extrai Entidades (Nome, Qtd, Categoria)
    │ • Verifica Duplicidade
    │ • Persiste no SQLite
    ⬇
[BANCO DE DADOS] (SQLite / Wal Mode)
    ⬆
[WEB APP] (Browser Mobile)
    │ • Renderiza Lista (Jinja2)
    │ • Edição/Check (JS/Fetch)
\`\`\`

---

## 3. Especificações Técnicas Detalhadas

### 3.1. Stack Tecnológica
* **Infraestrutura:** VPS Linux (HostGator), Docker, Docker Compose.
* **Proxy/Segurança:** Traefik (SSL Automático, Roteamento reverso).
* **Backend:** Python 3.11, Flask, Gunicorn, SQLAlchemy.
* **Banco de Dados:** SQLite (com Write-Ahead Logging - WAL ativado para concorrência).
* **Frontend:** HTML5, CSS3 (Variables), JavaScript Vanilla (ES6).
* **IA:** LangChain + Google Gemini Pro.

### 3.2. Estrutura de Dados (Schema)

#### Tabela \`users\`
| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| \`id\` | Integer | PK |
| \`username\` | String | Login (thiago, debora) |
| \`password_hash\` | String | Hash seguro (scrypt) |

#### Tabela \`lista_itens\` (Core)
| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| \`id\` | Integer | PK |
| \`produto_id\` | FK | Relacionamento com tabela produtos |
| \`quantidade\` | Float | Ex: 1.5, 2.0 |
| \`unidade_id\` | FK | Relacionamento com tabela unidades |
| \`usuario\` | String | Quem pediu (audit) |
| \`status\` | String | 'pendente', 'comprado', 'finalizado' |
| \`adicionado_em\` | DateTime | Timestamp de criação |
| \`origem_input\` | String | 'voice', 'manual' |

*(Tabelas auxiliares: \`categorias\`, \`unidades_medida\`, \`produtos\`)*

---

## 4. Funcionalidades e Regras de Negócio

### 4.1. O "Magic Endpoint" (IA)
* **Rota:** \`POST /magic\`
* **Modelo IA:** \`gemini-pro\` (Estável).
* **Lógica de Idempotência:**
    * Se o item já existe na lista com status \`pendente\` ou \`comprado\`, a IA **ignora** e avisa "Já na lista".
    * Se não existe, cria.
* **Parsing:** Utiliza localizadores de bloco JSON (\`[\`, \`]\`) para ignorar Markdown ou texto extra da IA.

### 4.2. Interface do Usuário (UX Mobile)
* **Long Press (800ms):** Abre modal de edição (Nome/Categoria).
* **Checkbox Otimista:** Feedback visual imediato + vibração tátil antes da resposta do servidor.
* **Limpar Carrinho:** Soft delete (status \`comprado\` -> \`finalizado\`).
* **Design System:** Tema "Cyberpunk Dark Neon" (Cores contrastantes para uso em ambientes claros/escuros).

---

## 5. Infraestrutura e Segurança

### 5.1. Estrutura de Pastas (Host)
\`\`\`text
/opt/n8n-traefik/
├── docker-compose.yml  # Orquestrador Mestre
├── .env                # Variáveis Secretas (API Keys)
├── letsencrypt/        # Certificados SSL
└── familyos/
    ├── Dockerfile      # Receita da Imagem
    ├── src/            # Código Fonte Python/HTML/CSS
    └── data/           # PERSISTÊNCIA (Banco de Dados)
\`\`\`

### 5.2. Segurança
* **Chaves de API:** Armazenadas estritamente no arquivo \`.env\` na raiz, injetadas via Docker Compose.
* **Banco de Dados:** Arquivo \`.db\` reside fora do container (Volume Mapeado) para garantir persistência pós-deploy.
* **Autenticação Web:** Cookies de Sessão HTTPOnly/Secure/Lax.

---

## 6. Histórico de Evolução (Sprints)

### ✅ Sprint 1-6: MVP e Estabilização
* Deploy inicial, integração n8n, Login básico.

### ✅ Sprint 7: Persistência e Robustez (Concluída em 02/12/2025)
* **Problema Resolvido:** Perda de dados ao reiniciar container.
* **Solução:** Implementação de Volumes Docker corretos.
* **Fix IA:** Migração para \`gemini-pro\` e parser JSON resiliente.
* **Fix DB:** Ativação de modo WAL para evitar erros de travamento (Database Locked).
* **Refatoração:** Limpeza total ("Terra Arrasada") e unificação de redes Docker.

### 🚧 Sprint 8: Refinamento e Expansão (Planejada)
* **Foco:** Usabilidade e Feedback em Tempo Real.
* **Backlog:**
    * Feedback no Frontend quando a IA está processando (WebSocket/Polling).
    * Suporte a múltiplas listas (Mercado vs Farmácia).
    * Dashboard de gastos (Analytics básico).

---

## 7. Procedimentos de Manutenção

### Atualizar Aplicação
\`\`\`bash
cd /opt/n8n-traefik
docker compose up -d --build familyos-app
\`\`\`

### Debugar Erros (Logs em Tempo Real)
\`\`\`bash
docker logs -f familyos_app
\`\`\`

### Resetar Banco de Dados (Zerar Tudo)
\`\`\`bash
docker exec familyos_app python src/reset_db.py
\`\`\`

---

## 8. Estrutura de Arquivos e Deploy

Esta seção descreve como os arquivos do seu ambiente de desenvolvimento (VS Code / Windows) devem ser organizados para garantir um deploy suave para a produção (VPS / Docker).

### 8.1. Estrutura do Projeto (VS Code)
Esta é a árvore de arquivos que você deve manter no seu computador local (\`C:\\Users\\thiag\\langchain\\projects\\todo_market_list\`).

\`\`\`text
todo_market_list/
├── .env                # Variáveis locais (NÃO COMMITAR)
├── .gitignore          # Ignora .env, __pycache__, data/
├── README.md           # Documentação Geral
├── requirements.txt    # Bibliotecas Python
├── deploy_pack/        # Pasta usada para enviar arquivos para a VPS (opcional)
├── data/               # Banco de Dados Local (SQLite)
├── docs/               # Documentação Técnica
│   ├── api_docs.md
│   ├── env_setup_docker.md
│   ├── frontend_docs.md
│   └── project_specs.md
└── src/                # Código Fonte da Aplicação
    ├── app.py          # O "Cérebro" (Backend Flask)
    ├── reset_db.py     # Script para zerar/popular o banco
    ├── static/
    │   └── css/
    │       └── styles.css  # Estilos (Tema Cyberpunk)
    └── templates/
        ├── index.html  # Frontend (Lista)
        └── login.html  # Frontend (Login)
\`\`\`

### 8.2. Mapeamento para Produção (VPS)
Quando subimos para a VPS, a estrutura muda ligeiramente pois o Docker assume o controle.

| Arquivo Local (Windows) | Caminho na VPS (Linux) | Caminho DENTRO do Container |
| :--- | :--- | :--- |
| \`src/*\` | \`/opt/n8n-traefik/familyos/src/*\` | \`/app/src/*\` |
| \`requirements.txt\` | \`/opt/n8n-traefik/familyos/requirements.txt\` | \`/app/requirements.txt\` |
| \`Dockerfile\` | \`/opt/n8n-traefik/familyos/Dockerfile\` | N/A (Usado no build) |
| \`data/familyos.db\` | \`/opt/n8n-traefik/familyos/data/familyos.db\` | \`/app/data/familyos.db\` |
| \`.env\` | \`/opt/n8n-traefik/.env\` | Variáveis de Ambiente |

### 8.3. Fluxo de Trabalho (Workflow)
1.  **Codar:** Faça as alterações no VS Code (pasta \`src\`).
2.  **Testar:** Rode localmente (`python src/app.py`) para validar.
3.  **Commitar:** Use o Git para salvar a versão.
4.  **Deploy:**
    * Copie a pasta \`src\` e o arquivo \`requirements.txt\` para a VPS (via SSH).
    * Na VPS, rode: \`docker compose up -d --build familyos-app\`.