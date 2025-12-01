# 📘 Relatório Técnico Mestre: FamilyOS

**Projeto:** FamilyOS (Módulo Compras)
**Versão:** 1.1.0 (Cyberpunk Persistence)
**Status:** Produção Estável (Dockerizado)
**Data de Atualização:** 01/12/2025
**Arquitetura:** Microserviço Híbrido com IA & Persistência em Volume

---

## 1. Visão Geral Executiva

O **FamilyOS** é um sistema de gestão doméstica autônomo. O módulo atual (Lista de Compras) resolve o problema da fragmentação de informações através de uma abordagem **Voice-to-Database**.

Diferente de listas de tarefas comuns, o FamilyOS utiliza Inteligência Artificial para estruturar, categorizar e normalizar os dados, e uma interface **"Dark Neon"** otimizada para uso rápido em supermercados.

### Principais Diferenciais (v1.1)
1.  **Fricção Zero:** Entrada de dados via áudio no Telegram (sem abrir apps).
2.  **Resiliência:** Arquitetura Docker com volumes persistentes (à prova de reinicialização).
3.  **Integridade:** Sanitização estrita de dados para impedir duplicatas.
4.  **UX Imersiva:** Design Glassmorphism com feedback tátil e edição "Long Press".

---

## 2. Arquitetura Técnica Detalhada

O sistema opera em um fluxo unidirecional de dados para entrada, e bidirecional para gestão.

### 2.1. O Pipeline de Dados
1.  **Input (Telegram):** Usuário envia áudio/texto.
2.  **Orquestração (n8n):**
    * Recebe o Webhook.
    * Transcreve áudio via **OpenAI Whisper**.
    * Envia JSON para o endpoint local via túnel.
3.  **Conectividade (Ngrok):** Túnel seguro expondo o container Docker local para a nuvem.
4.  **Cérebro (Flask + LangChain):**
    * Recebe o texto bruto.
    * Processa via **Google Gemini 2.5 Flash-Lite**.
    * **Sanitização:** Normaliza texto (Upper/Lower/Strip).
    * **Persistência:** Grava no SQLite via SQLAlchemy.
5.  **Interface (Frontend):** Web App reativa consumindo a API local.

### 2.2. Diagrama de Infraestrutura (Docker)

```mermaid
graph TD
    subgraph "Host (Windows/Server)"
        Dados[./data/todo_market.db]
    end

    subgraph "Container Docker (familyos)"
        App[Flask App]
        Vol((Volume Mount))
    end

    App <--> Vol
    Vol <--> Dados
````

O banco de dados **não reside** mais dentro do container efêmero. Ele é mapeado para a pasta `./data` do sistema hospedeiro, garantindo persistência total.

-----

## 3\. Estrutura do Projeto (File System)

Estrutura atualizada para suportar Docker e Volumes:

```text
projects/todo_market_list/
├── docs/                   # Memória do Projeto (Atas, Relatórios)
├── data/                   # [NOVO] Persistência do SQLite (Mapeado via Docker)
│   └── todo_market.db      # O Banco de Dados vivo
├── src/
│   ├── static/css/
│   │   └── styles.css      # Design System Dark Neon
│   ├── templates/
│   │   ├── index.html      # SPA com Modal de Edição e Long Press
│   │   └── login.html      # Autenticação Simples
│   ├── app.py              # Core: Rotas, Models, Sanitização, IA
│   ├── reset_db.py         # Script de Seed e Reset (Cria usuários admin)
│   └── requirements.txt    # Dependências (Flask, SQLAlchemy, LangChain)
├── docker-compose.yml      # [NOVO] Orquestração do Container e Volumes
├── Dockerfile              # Imagem Python 3.11 Slim
└── .env                    # Segredos (API Keys)
```

-----

## 4\. Especificações Funcionais (Backend & Frontend)

### 4.1. API Flask (`app.py`)

O backend atua como controlador central e guardião da integridade.

  * **Sanitização Estrita (Anti-Duplicidade):**

      * Antes de salvar qualquer dado, o sistema aplica:
          * *Categorias:* `UPPERCASE` + `strip()` (Ex: " Padaria " -\> "PADARIA").
          * *Itens:* `lowercase` + `strip()` (Ex: "Leite " -\> "leite").
      * Isso impede que "Leite" e "leite" coexistam.

  * **Endpoints Críticos:**

      * `POST /magic`: Entrada via IA (Telegram).
      * `POST /update_item`: **[NOVO]** Edição de item (Nome/Categoria).
      * `POST /toggle_item/<id>`: Check/Uncheck.
      * `GET /`: Renderização da lista.

### 4.2. Interface "Dark Neon" (`index.html`)

Um Design System proprietário focado em usabilidade noturna e contraste.

  * **Paleta de Cores:**
      * Fundo: *Deep Void* (`#050509`)
      * Acentos: *Neon Purple* (`#611af0`), *Green* (`#22ff7a`), *Red* (`#ff3131`).
  * **Interatividade Avançada (Sprint 7):**
      * **Long Press (600ms):** Tocar e segurar um item abre o modo de edição.
      * **Modal Glassmorphism:** Janela de edição com fundo desfocado e inputs escuros.
      * **DataList Inteligente:** Ao editar a categoria, o sistema sugere categorias existentes para evitar fragmentação.

-----

## 5\. Manual de Operação (Docker)

A execução agora é containerizada, eliminando problemas de dependência ("funciona na minha máquina").

### 5.1. Iniciar o Sistema

Na raiz do projeto (onde está o `docker-compose.yml`):

```powershell
# Iniciar em segundo plano (com rebuild para garantir código novo)
docker compose up -d --build
```

### 5.2. Resetar/Semear Banco de Dados

Se precisar limpar tudo e recriar os usuários padrão (`thiago` / `debora`):

```powershell
# Executa o script python DENTRO do container rodando
docker compose exec web python src/reset_db.py
```

### 5.3. Monitoramento

Para ver os logs da aplicação e da IA em tempo real:

```powershell
docker compose logs -f
```

-----

## 6\. Roadmap e Próximos Passos

O sistema atingiu a maturidade de **MVP Resiliente**. Os próximos passos visam expansão de features.

1.  **Deploy em Nuvem (Sprint 8):**

      * Migrar de `localhost` + Ngrok para uma VPS (ex: DigitalOcean ou HostGator) com SSL real.
      * Objetivo: Disponibilidade 24/7 sem depender do PC ligado.

2.  **Módulo de Receitas (Sprint 9):**

      * Comando: "Quero fazer um bolo de cenoura".
      * Ação: O sistema busca os ingredientes e adiciona à lista apenas o que não temos (estoque virtual).

3.  **Dashboards de Analytics (Sprint 10):**

      * Visualização de gastos por categoria (Gráficos Chart.js).

-----

**Equipe de Desenvolvimento (Agentes):**

  * 🤖 **Alpha:** Gerente de Produto
  * 🤖 **Architect:** Infraestrutura & Dados
  * 🤖 **Experience:** Frontend & UX
  * 🤖 **Builder:** Implementação de Código

**Aprovado em:** 01/12/2025

```
