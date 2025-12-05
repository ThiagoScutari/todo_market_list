## 2. Arquitetura de Informação (UX/UI)

### 2.1. O Dashboard (Tela Inicial)
A nova entrada do sistema será um Dashboard "Heads-up Display" (HUD).

**Estrutura da Tela:**
1.  **Header:** Saudação + Clima Rápido (Ícone + Temp).
2.  **Widget "Message of the Day":** Card com texto inspiracional (API externa ou Banco de frases).
3.  **Widget "Weather Strategy":**
    * *Hoje:* Manhã/Tarde/Noite.
    * *Weekend:* Previsão resumida para Sábado/Domingo (Churrasco ou Netflix?).
4.  **Grid de Navegação (Módulos):**
    * [🛒 Compras] (Ativo)
    * [✅ Tarefas] (Ativo - Com badge de pendências)
    * [🥗 Inserir Ingredientes] (Opaco/Desabilitado)
    * [⏰ Lembretes] (Opaco/Desabilitado)

---

## 3. Regras de Negócio: Módulo de Tarefas

O diferencial do FamilyOS é a **Inteligência de Atribuição (NLP)**.

### 3.1. Roteamento de Intenção (n8n Router)
O n8n deixará de enviar tudo para \`/magic\`. Ele terá um passo anterior de **Classificação de Intenção**:
* *"Comprar leite"* -> Rota **Shopping**.
* *"Lavar o carro"* -> Rota **Tasks**.

### 3.2. Lógica de Atribuição Automática
Ao receber uma tarefa, a IA deve identificar o **Responsável** (`assignee`) baseado em 3 regras:

1.  **Explícito (Nome na frase):**
    * *Input:* "Thiago colocar roupas para lavar"
    * *Logic:* Detectou "Thiago".
    * *Assignee:* **Thiago**.

2.  **Coletivo (Palavras-chave):**
    * *Input:* "Temos que ir jantar no Frasini", "Precisamos arrumar a sala".
    * *Logic:* Detectou "Temos", "Precisamos", "Nós".
    * *Assignee:* **Casal**.

3.  **Implícito (Remetente):**
    * *Input:* "Pegar Catharina na escola" (Enviado por Débora).
    * *Logic:* Sem nome e sem plural. Assume-se "eu vou fazer".
    * *Assignee:* **Débora** (Remetente).

### 3.3. Classificação de Prioridade
As tarefas terão 3 níveis, definidos via IA (análise de urgência) ou edição manual (Long Press):
* 🟢 **Baixa:** Coisas rotineiras.
* 🟡 **Média:** Importante, mas sem data crítica.
* 🔴 **Alta:** Urgente/Crítico.
    * **Regra de Gatilho:** Se \`Priority == High\`, o sistema deve disparar um e-mail para o responsável (ou ambos se for Casal).

---

## 4. Banco de Dados (Schema v2.0)

O banco SQLite será expandido com novas tabelas.

### 4.1. Tabela \`tasks\`
| Campo | Tipo | Detalhes |
| :--- | :--- | :--- |
| \`id\` | PK | Identificador único. |
| \`descricao\` | String | O que fazer. |
| \`responsavel\` | String | 'Thiago', 'Debora', 'Casal'. |
| \`prioridade\` | Integer | 1 (Verde), 2 (Amarelo), 3 (Vermelho). |
| \`status\` | String | 'pendente', 'concluido'. |
| \`prazo\` | DateTime | Opcional. |
| \`created_at\` | DateTime | Data de criação. |

### 4.2. Tabela \`weather_cache\`
Para evitar estourar limites de API e acelerar o load da Home.
| Campo | Tipo | Detalhes |
| :--- | :--- | :--- |
| \`id\` | PK | 1 (Singleton). |
| \`city\` | String | 'Itajaí'. |
| \`data_json\` | JSON | O payload completo da API de tempo. |
| \`last_updated\` | DateTime | Timestamp. Atualizar se > 1h. |

---

## 5. Integrações Externas (APIs)

### 5.1. Meteorologia
* **Provider:** OpenWeatherMap ou HG Brasil (A definir).
* **Dados:** Temperatura, Condição (Chuva/Sol), Previsão 3 dias.

### 5.2. Mensagem do Dia
* **Provider:** API de citações ou lista local randômica.

---

## 6. Estratégia de Desenvolvimento (Roadmap Sprint 8)

Para mitigar riscos, a implementação será gradual:

1.  **Backend (Foundation):**
    * Criar tabelas \`tasks\` e \`weather_cache\` via migration (ou reset se aceitável).
    * Criar endpoints \`/tasks/magic\`, \`/tasks/update\`, \`/weather\`.

2.  **Inteligência (n8n):**
    * Criar o "Router" que decide se o áudio é Compra ou Tarefa.
    * Ajustar o Prompt do Gemini para extrair \`responsavel\` e \`prioridade\`.

3.  **Frontend (Dashboard):**
    * Criar a nova \`home.html\` (Dashboard).
    * Mover a lista de compras atual para \`shopping.html\`.
    * Criar a visualização de Tarefas (Cards com badge de responsável e cor de prioridade).

---

**Autor:** Thiago Scutari & Alpha Agent.
**Visão:** Transformar a casa em uma empresa autogerenciável.