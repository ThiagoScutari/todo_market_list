# 🛒 FamilyOS: ToDo Market & List
### Software House Autônoma de Gestão Doméstica

O **FamilyOS** é um sistema híbrido de gestão doméstica inteligente, focado em eliminar a **fricção cognitiva e operacional** na organização familiar. O foco inicial é o Módulo de Compras, que utiliza Inteligência Artificial para transformar áudios no Telegram em uma **Lista de Compras Web Interativa**.

> **Versão Atual:** 1.1.0 (Cyberpunk Persistence)
> **Status:** Produção Estável (Dockerizada)

---

## 💡 Showcase: O Fluxo de Uso

### 1. Entrada de Dados (Telegram)
A interface de entrada é o Telegram. O sistema aceita áudios com linguagem natural ("preciso de 3 ovos e uma caixa de leite") ou texto direto. O bot confirma o recebimento e valida os itens.
![Interação Telegram](images/telegram.png)

### 2. Orquestração (n8n & Backend)
O **n8n** atua como o sistema nervoso, recebendo o webhook do Telegram, processando o áudio via Whisper e enviando para a API Python estruturar os dados com Gemini.
![Fluxo n8n](images/n8n.png)

### 3. Segurança e Acesso (Login)
O sistema conta com uma camada de autenticação para garantir que apenas a família tenha acesso à gestão da lista.
![Tela de Login](images/login.png)

### 4. A Lista Inteligente (Web App)
Uma interface *mobile-first* limpa com design **Dark Neon**. O sistema agrupa automaticamente os itens por categorias (Padaria, Laticínios, etc.) para otimizar o trajeto dentro do supermercado.
![Interface Principal](images/layout_principal.png)

### 5. Feedback Visual e Interatividade
Ao marcar um item, ele recebe um feedback visual imediato (check verde e risco).
* **[NOVO] Edição Rápida:** Um toque longo (Long Press) no item abre o menu de edição para corrigir nomes ou categorias.
![Efeitos Visuais](images/efeitos.png)

---

## 🏗️ Arquitetura Técnica (Sprint 7 - Persistence)

A arquitetura evoluiu para um **Microserviço Híbrido Resiliente**, hospedado em Docker. A principal evolução da versão 1.1 é a persistência de dados fora do container, garantindo que a lista sobreviva a reinicializações.

![Arquitetura do Sistema](images/arquitetura.png)

### Componentes Chave

| Componente | Função | Tecnologias Chave |
| :--- | :--- | :--- |
| **Interface de Entrada** | Captura de áudio/texto | Telegram Bot API |
| **Orquestrador** | Transcrição e Roteamento | n8n, OpenAI Whisper |
| **Cérebro (NLP)** | Extração e Sanitização | Google Gemini 2.5 Flash-Lite, LangChain |
| **Backend** | Regras de Negócio | Python Flask, Gunicorn, SQLAlchemy |
| **Persistência** | Banco de Dados Resiliente | SQLite (Volume Docker no Host) |
| **Frontend** | Visualização e Edição | HTML5, CSS3 (Glassmorphism), JS Fetch |

---

## 🎯 Funcionalidades do Módulo de Compras

### 1. Entrada Inteligente & Sanitização (`POST /magic`)
* **Processamento de Linguagem Natural (NLP):** O sistema entende contextos complexos. Ex: "2kg de carne moída para o almoço de domingo".
* **Normalização Estrita:** O sistema impede duplicatas convertendo automaticamente inputs para singular e minúsculas ("Leite " vira "leite"). Categorias são padronizadas em UPPERCASE.
* **Rastreabilidade:** Identifica quem solicitou o item (ex: Thiago ou Esposa), útil para tirar dúvidas na hora da compra.

### 2. Interface de Compras Otimizada (`GET /`)
* **Design No-Zoom:** Botões grandes e checkboxes de 32px, projetados para uso com uma mão.
* **Categorização Automática:** O Gemini classifica os itens em categorias reais de mercado (Hortifrúti, Limpeza, Açougue).
* **Edição In-Place (Long Press):** Segure o dedo sobre um item por 600ms para abrir o Modal de Edição e corrigir erros de classificação sem precisar apagar o item.

### 3. Gestão de Estado e Persistência
* **Toggle em Tempo Real:** Status salvo instantaneamente no banco de dados.
* **Docker Volumes:** O arquivo `todo_market.db` agora reside na pasta `./data` do servidor, garantindo backup fácil e persistência total.

---

## 🛠️ Setup e Deploy (Docker)

O método recomendado para rodar o FamilyOS v1.1 é via Docker Compose.

1.  **Clonar o Repositório:**
    ```bash
    git clone [https://github.com/ThiagoScutari/todo_market_list.git](https://github.com/ThiagoScutari/todo_market_list.git)
    cd todo_market_list
    ```

2.  **Configurar Chaves (`.env`):**
    Crie um arquivo `.env` na raiz com suas chaves (Google API Key, Secret Key).

3.  **Subir a Aplicação:**
    ```powershell
    docker compose up -d --build
    ```

4.  **Resetar/Criar Usuários (Primeiro Uso):**
    Para criar o banco e os usuários padrão (`thiago` / `debora`):
    ```powershell
    docker compose exec web python src/reset_db.py
    ```

5.  **Acessar:**
    * Frontend: `http://localhost:5000`

---

## 🗺️ Roadmap de Desenvolvimento

| Sprint | Foco | Status |
| :--- | :--- | :--- |
| **Sprint 1-4** | MVP, Backend, Frontend Básico | ✅ Concluído |
| **Sprint 5** | Deploy em Produção (Docker Base) | ✅ Concluído |
| **Sprint 6** | Refinamento Visual (Dark Neon) | ✅ Concluído |
| **Sprint 7** | **Persistência, Edição Mobile e Sanitização** | ✅ Concluído (v1.1) |
| **Sprint 8** | Deploy Nuvem (VPS/SSL) | 🚧 Planejado |
| **Sprint 9** | Módulo de Receitas | 🔮 Futuro |

---

**Desenvolvido por:** Thiago Scutari & Equipe de Agentes (Alpha, Architect, Builder, Experience).
**Tecnologia:** Google Gemini, Python, AI, Automation.