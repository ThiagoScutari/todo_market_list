# 📡 FamilyOS API Documentation
**Versão:** 1.2 (Stable)
**Base URL:** \`https://api.thiagoscutari.com.br\`
**Tecnologia:** Python Flask + SQLite + SQLAlchemy

---

## 🔐 1. Autenticação e Segurança

### Mecanismo
O sistema utiliza **Session Cookies** para rotas protegidas.
* **Login:** Cria um cookie seguro (\`HttpOnly\`, \`Secure\`, \`SameSite=Lax\`).
* **Duração:** O cookie é persistente por 30 dias (\`REMEMBER_COOKIE_DURATION\`).
* **Rota Pública:** A única rota de API que não exige login é \`/magic\` (protegida apenas por obscuridade e uso interno via n8n).

---

## 🤖 2. Inteligência Artificial (Core)

### \`POST /magic\`
Esta é a rota principal utilizada pelo n8n para processar áudios e textos.

* **Descrição:** Recebe um texto natural, envia para o Google Gemini Pro, processa o JSON retornado, verifica duplicidade no banco de dados e insere os itens.
* **Auth:** Pública (Não requer header de sessão).
* **Headers:**
    * \`Content-Type: application/json\`

#### Corpo da Requisição (Request Body)
\`\`\`json
{
  "texto": "Comprar 2 kg de picanha e um pacote de carvão",
  "usuario": "Thiago"
}
\`\`\`
* \`texto\` (Obrigatório): A transcrição do áudio ou texto digitado.
* \`usuario\` (Opcional): Nome de quem enviou (padrão: "Anônimo").

#### Respostas (Response)

**Sucesso (201 Created):**
Retorna uma mensagem formatada pronta para ser exibida no Telegram.
\`\`\`json
{
  "message": "✅ Adicionados: Picanha, Carvão"
}
\`\`\`

**Sucesso Parcial (201 Created):**
Quando alguns itens são novos e outros já existiam (status 'pendente' ou 'comprado').
\`\`\`json
{
  "message": "✅ Adicionados: Picanha | ⚠️ Já na lista: Carvão"
}
\`\`\`

**Erro de Configuração (503 Service Unavailable):**
Quando a chave da API do Google falha ou o modelo não é encontrado.
\`\`\`json
{
  "erro": "Config IA Falhou: [Detalhes do erro Python...]"
}
\`\`\`

---

## 🛒 3. Gestão da Lista (Frontend)

### \`POST /toggle_item/<id>\`
Marca ou desmarca um item como comprado.

* **Descrição:** Usado pelo checkbox na interface. Alterna o status do item no banco.
* **Lógica:** Se \`pendente\` -> vira \`comprado\`. Se \`comprado\` -> vira \`pendente\`.
* **Auth:** Requer Login.
* **Parâmetros de URL:**
    * \`id\` (Integer): O ID único do item na tabela \`lista_itens\`.

**Exemplo de Resposta (200 OK):**
\`\`\`json
{
  "status": "success",
  "novo_status": "comprado"
}
\`\`\`

---

### \`POST /update_item\`
Edita as propriedades de um item existente.

* **Descrição:** Usado pelo Modal de Edição (Long Press). Permite corrigir erros de transcrição ou mudar categoria.
* **Auth:** Requer Login.
* **Headers:** \`Content-Type: application/json\`

#### Corpo da Requisição
\`\`\`json
{
  "id": 15,
  "nome": "Pão de Queijo",
  "categoria": "PADARIA"
}
\`\`\`
* **Lógica de Backend:**
    * Normaliza o nome para minúsculas ("pão de queijo").
    * Normaliza a categoria para maiúsculas ("PADARIA").
    * Se a categoria não existir, cria uma nova.
    * Se o produto (nome) não existir, cria um novo produto.

**Exemplo de Resposta (200 OK):**
\`\`\`json
{
  "message": "OK"
}
\`\`\`

---

### \`POST /clear_cart\`
Limpa o carrinho (Arquivamento).

* **Descrição:** Chamado pelo botão "Limpar Carrinho". Não deleta fisicamente.
* **Lógica:** Altera o status de todos os itens \`comprado\` para \`finalizado\`. Itens \`finalizado\` não aparecem mais na Home, mas ficam no banco para histórico futuro.
* **Auth:** Requer Login.

**Exemplo de Resposta (200 OK):**
\`\`\`json
{
  "status": "success"
}
\`\`\`

---

## 🌐 4. Navegação

### \`GET /\`
Página Principal.
* **Retorno:** HTML renderizado (Jinja2) com a lista agrupada por categorias.

### \`GET /login\` e \`POST /login\`
Página de Acesso.
* **GET:** Exibe o formulário.
* **POST:** Processa \`username\` e \`password\`. Redireciona para \`/\` em caso de sucesso.

### \`GET /logout\`
Encerra a sessão.
* **Ação:** Limpa o cookie de sessão e redireciona para \`/login\`.

---

## ✅ 5. Módulo de Tarefas (Tasks) - [NOVO]

### \`POST /tasks/magic\` (Core IA)
Recebe texto natural, classifica prioridade e atribui responsável automaticamente.

* **Descrição:** Endpoint chamado pelo n8n após o roteador de intenção identificar que é uma "Tarefa".
* **Body (JSON):**
    \`\`\`json
    {
      "texto": "Thiago colocar roupas para lavar",
      "remetente": "Thiago"
    }
    \`\`\`
    * *Nota:* O campo \`remetente\` é crucial para a regra de atribuição implícita ("eu vou fazer").

* **Lógica de Atribuição (Backend):**
    1.  **Explícita:** Se o texto contiver "Thiago", "Debora" ou "Nós/Casal".
    2.  **Implícita:** Se não tiver nome, atribui ao \`remetente\`.
    
* **Sucesso (201 Created):**
    \`\`\`json
    {
      "message": "✅ Tarefa atribuída a Thiago: Colocar roupas para lavar (P: Baixa)",
      "task_id": 42
    }
    \`\`\`

### \`POST /tasks/toggle/<id>\`
Conclui ou reabre uma tarefa.
* **Lógica:** Alterna status entre \`pendente\` <-> \`concluido\`.
* **Sucesso (200 OK):** \`{"status": "success", "novo_status": "concluido"}\`

### \`POST /tasks/update\`
Edita uma tarefa existente.
* **Body (JSON):**
    \`\`\`json
    {
      "id": 42,
      "descricao": "Lavar o carro",
      "responsavel": "Casal",
      "prioridade": 3  // 1=Baixa(Verde), 2=Média(Amarela), 3=Alta(Vermelha)
    }
    \`\`\`

---

## 📊 6. Dashboard & Widgets - [NOVO]

### \`GET /api/weather\`
Retorna dados meteorológicos cacheados para o Dashboard.
* **Descrição:** O backend consulta a API externa (OpenWeather/HG) no máximo 1x por hora e salva no banco para evitar rate-limit e latência.
* **Retorno (200 OK):**
    \`\`\`json
    {
      "city": "Itajaí",
      "temp_now": 28,
      "condition": "rain",
      "forecast_weekend": {
        "sat": {"min": 22, "max": 29, "desc": "Sol com nuvens"},
        "sun": {"min": 23, "max": 30, "desc": "Pancadas de chuva"}
      },
      "updated_at": "14:30"
    }
    \`\`\`

### \`GET /api/inspiration\`
Retorna a "Mensagem do Dia".
* **Lógica:** Seleciona aleatoriamente de um banco local ou consulta API externa.
* **Retorno (200 OK):**
    \`\`\`json
    {
      "text": "O sucesso é a soma de pequenos esforços repetidos dia após dia.",
      "author": "Robert Collier"
    }
    \`\`\`

---

## 🌐 7. Navegação e Views

### \`GET /\` (Dashboard)
**[Alteração Planejada]** Passará a renderizar o Dashboard Geral com cards de resumo.

### \`GET /shopping\`
Renderiza a Lista de Compras (o antigo \`/\`).

### \`GET /tasks\`
Renderiza o quadro de Tarefas (Kanban ou Lista agrupada por Responsável).

---

## 8. Webhooks (n8n Router)

O n8n agora atua como um roteador antes de chamar a API.

1.  **Entrada:** Telegram Webhook.
2.  **Classifier:** LLM decide se a intenção é \`SHOPPING\` ou \`TASK\`.
3.  **Route:**
    * Se \`SHOPPING\` -> POST \`/magic\`
    * Se \`TASK\` -> POST \`/tasks/magic\`