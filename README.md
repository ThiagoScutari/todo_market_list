# 🛒 FamilyOS: ToDo Market & List
### Software House Autônoma de Gestão Doméstica

O **FamilyOS** é um sistema híbrido de gestão doméstica inteligente, focado em eliminar a **fricção cognitiva e operacional** na organização familiar. O foco inicial é o Módulo de Compras, que utiliza Inteligência Artificial para aceitar inputs em linguagem natural (voz/texto) e persistir dados de forma estruturada.

---

## 💡 Visão Estratégica e Princípios

O projeto é guiado por um objetivo central: **Fricção Zero**. O sistema foi construído sobre princípios de **Resiliência Nativa** e **Desacoplamento**, garantindo que as falhas em um componente (como um provedor de IA) não quebrem o fluxo completo.

### Objetivos Principais
* Reduzir a fricção na entrada de dados (Priorizando Voz).
* Centralizar informações familiares de forma inteligente.
* Automatizar processos domésticos recorrentes.

---

## 🏗️ Arquitetura de Alto Nível (Sprint 2 - Concluída)

A arquitetura utiliza o padrão **Microserviço Inteligente**, separando a responsabilidade de orquestração da responsabilidade de processamento da lógica de negócio.

```

┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   INTERFACE     │    │   ORQUESTRADOR   │    │    CÉREBRO       │
│                 │    │                  │    │                  │
│  • Telegram     │───▶│  • n8n           │───▶│  • Flask API     │
│  • (Voz/Texto)  │    │  • Whisper/Ngrok │    │  • Gemini AI     │
└─────────────────┘    └──────────────────┘    └──────────────────┘
│
▼
┌─────────────────┐    ┌──────────────────┐
│   VISUALIZAÇÃO  │    │    MEMÓRIA       │
│                 │    │                  │
│  • Notion       │◀──│  • SQLite        │
│                 │    │                  │
└─────────────────┘    └──────────────────┘

```

*Fonte: Visão de Alto Nível do Documento Mestre de Arquitetura.*

### Componentes Chave

| Componente | Função | Tecnologias Chave |
| :--- | :--- | :--- |
| **Interface** | Entrada de dados (Voz) | Telegram Bot API |
| **Orquestrador** | Roteamento, Fallback de IA | n8n, Ngrok (Dev Tunnel) |
| **Cérebro (Backend)** | Processamento NLP, Lógica de Negócio | Flask, Gemini 2.5 Flash-Lite, SQLAlchemy |
| **Persistência** | Fonte da Verdade | SQLite (Dev) / PostgreSQL (Prod) |

---

## 🎯 Módulo Implementado: Lista de Compras Inteligente

Este módulo está funcional e pronto para ser conectado ao Notion.

### Fluxo Validado (Voice-to-Database)
1.  **Coleta:** Usuário envia áudio/texto no Telegram.
2.  **Preparação:** Áudio é transcrito (Whisper) e metadados são extraídos (Nome do Usuário).
3.  **Processamento:** A rota `POST /magic` recebe o texto e o **Gemini** extrai JSON de produto (nome, quantidade, categoria).
4.  **Persistência:** O item é inserido na tabela `lista_itens`, com rastreamento do `usuario` que fez a solicitação.

### Modelo de Dados Central (Tabela `lista_itens`)
Esta tabela armazena o estado atual da sua lista de compras.
* `produto_id`: Item a ser comprado (FK para o Catálogo).
* **`quantidade`:** Quanto comprar.
* **`usuario`:** Rastreamento por membro da família (Thiago ou Esposa).
* `status`: Máquina de estados (pendente, comprado, cancelado).

---

## 🛠️ Setup e Desenvolvimento

Para rodar o projeto localmente após clonar, siga estas instruções:

1.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/ThiagoScutari/todo_market_list.git
    cd todo_market_list
    ```

2.  **Configurar Ambiente:**
    * Crie o ambiente virtual (`python -m venv venv`).
    * Ative-o (`.\venv\Scripts\activate`).
    * Instale as dependências:
        ```bash
        pip install -r requirements.txt
        ```

3.  **Configurar Chaves:**
    * Crie um arquivo `.env` na raiz do projeto e insira as chaves API (Gemini, OpenAI, Telegram).
    ```
    # Exemplo de .env
    GEMINI_API_KEY="AIzaSy..."
    OPENAI_API_KEY="sk-..."
    ```

4.  **Inicializar o Banco de Dados:**
    * Este passo cria o banco (`todo_market.db`) e insere os dados iniciais (Categorias, Unidades).
    ```powershell
    python src/setup_database.py
    ```

5.  **Rodar a API (Backend):**
    ```powershell
    python src/app.py
    ```

6.  **Expor a API (Para testes com n8n):**
    * Em um novo terminal, inicie o túnel:
    ```powershell
    ngrok http 5000
    ```
    * Use a URL HTTPS gerada no seu workflow do n8n.

---

## 🗺️ Plano Futuro (Sprint 3 e Além)

O projeto está pronto para a próxima fase de visualização.

* **Sprint 3 (Visualização):** Integração com **Notion API** para criar o dashboard de listas de compras.
* **Sprint 4 (Produção):** Migração de `localhost` para um ambiente de **Deploy** profissional (VPS/Render).
* **Funcionalidades Avançadas:** Implementação do Módulo de Receitas e Sistema de Alertas.

***

[Apresentação do Projeto (Futuros Vídeos e Imagens de Sucesso)]

*Nota: As métricas de sucesso (Latência API < 2s, Precisão NLP > 95%) serão monitoradas continuamente.*
````