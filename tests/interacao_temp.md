
### **Architect, sua análise:**

A VPS nos dá um disco persistente, o que levanta uma questão importante sobre nossa stack de dados. Além disso, a coexistência com o n8n precisa ser gerenciada de forma robusta. Analise os seguintes pontos:

1.  **Persistência de Dados:** Com um disco persistente, é tecnicamente viável manter o SQLite? Quais são os prós e contras em um ambiente de produção com múltiplos workers, mesmo que de baixo tráfego?
2.  **Coexistência de Serviços:** Qual a sua recomendação para rodar nossa aplicação Flask ao lado do n8n já existente? Valide minha sugestão sobre Docker e explique por que seria a melhor abordagem.
3.  **Artefatos de Orquestração:** Se seguirmos com Docker, a criação de um `Dockerfile` e um `docker-compose.yml` é o caminho correto? Qual o papel de cada um nesse cenário?

---

### **Builder, seu plano de ação:**

Com base na recomendação do Architect, liste os arquivos exatos que você precisará criar ou modificar para "Dockerizar" nossa aplicação e prepará-la para o deploy. Seja específico sobre o propósito de cada arquivo.

---

### **Experience, sua perspectiva de usabilidade:**

O deploy muda a forma como o n8n se comunica com nossa API, eliminando o Ngrok. O usuário final (nós mesmos, no caso) precisará atualizar a configuração.

1.  **Ponto de Conexão:** Como o n8n, rodando na mesma máquina (potencialmente no mesmo Docker Compose), deve se conectar à nossa API Flask? Qual é a nova URL que ele deve usar?
2.  **Redução de Fricção:** Como podemos tornar essa transição o mais simples possível para o usuário que configura o workflow no n8n? A ideia é evitar URLs fixas que podem mudar e facilitar a configuração.

---

Aguardando as análises.

**Alpha**
Gerente de Projeto

---
---

### **Architect (Análise da Arquitetura)**

Alpha, sua análise está correta. A VPS muda o jogo. Aqui estão minhas considerações:

1.  **SQLite vs. PostgreSQL na VPS:**
    *   **Viabilidade:** Sim, tecnicamente **podemos** manter o SQLite. O disco da VPS é persistente, então o arquivo `.db` não será perdido entre reinicializações, ao contrário de alguns ambientes de contêineres efêmeros.
    *   **Recomendação:** **Não recomendo.** O principal problema do SQLite em produção não é a persistência, mas a **concorrência**. Um servidor de produção como o Gunicorn rodará múltiplos *workers* (processos) para lidar com requisições. O SQLite trava o banco de dados inteiro a cada escrita. Com múltiplos workers tentando escrever ao mesmo tempo, encontraremos erros de `database is locked` constantemente. Para nosso caso de uso familiar, poderíamos forçar o Gunicorn a usar um único worker (`--workers 1`), mas isso anula um dos principais benefícios de um servidor de produção.
    *   **Veredito:** A migração para PostgreSQL, mesmo dentro do Docker, é o padrão-ouro para produção. No entanto, para **manter a simplicidade e acelerar o deploy da Sprint 5**, podemos prosseguir com o SQLite, **desde que aceitemos a limitação de rodar com um único worker.**

2.  **Coexistência com n8n (Docker):**
    *   Sua recomendação de **Docker é a melhor abordagem possível**. Rodar Python diretamente na VPS ao lado do n8n é uma receita para o desastre. Teríamos conflitos de versão do Python, bibliotecas do sistema e permissões.
    *   **Docker resolve isso com isolamento total.** Nossa aplicação Flask e suas dependências viverão em um contêiner, e o n8n viverá em outro. Eles não interferem um no outro.

3.  **Artefatos de Orquestração (`Dockerfile` e `docker-compose.yml`):**
    *   Sim, ambos são essenciais.
    *   **`Dockerfile`:** É a **receita de bolo** para construir a imagem da *nossa aplicação*. Ele dirá ao Docker: "Comece com uma imagem base do Python, copie o código da aplicação para dentro, instale as dependências do `requirements.txt` e defina o comando para iniciar o servidor Gunicorn".
    *   **`docker-compose.yml`:** É o **maestro da orquestra**. Ele define os *serviços* que compõem nosso sistema (`app-flask`, `n8n`, talvez um `postgres` no futuro). Ele os conecta em uma rede privada, gerencia volumes de dados persistentes e facilita o início e a parada de todo o ambiente com um único comando (`docker-compose up`).

**Conclusão do Architect:** Recomendo fortemente o uso de `docker-compose` para orquestrar nossa aplicação (definida por um `Dockerfile`) e o serviço do n8n. Para a Sprint 5, aceito manter o SQLite com a ressalva de usar um único worker Gunicorn.

---

### **Builder (Plano de Ação)**

Entendido. Para "Dockerizar" a aplicação e prepará-la para o deploy via Docker Compose, precisarei criar os seguintes arquivos no diretório raiz do projeto:

1.  **`requirements.txt`:** Já existe, mas vou garantir que esteja 100% atualizado com todas as dependências, incluindo o `gunicorn`, que será nosso servidor de produção WSGI.
2.  **`Dockerfile`:** Será um novo arquivo. Ele conterá os passos para construir a imagem da nossa aplicação Flask. As etapas principais serão:
    *   `FROM python:3.11-slim` (Usar uma imagem base leve)
    *   `WORKDIR /app` (Definir o diretório de trabalho dentro do contêiner)
    *   `COPY requirements.txt .` (Copiar o arquivo de dependências)
    *   `RUN pip install --no-cache-dir -r requirements.txt` (Instalar as dependências)
    *   `COPY ./src .` (Copiar todo o nosso código-fonte para o contêiner)
    *   `CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]` (Comando para iniciar a aplicação com Gunicorn).
3.  **`docker-compose.yml`:** O arquivo principal de orquestração. Ele definirá dois serviços:
    *   **`familyos-app`:** Nosso serviço Flask. Ele usará o `Dockerfile` para construir a imagem, mapeará a porta `5000` do contêiner para uma porta na VPS (ex: `8000:5000`) e configurará um volume para que o banco `todo_market.db` seja persistido no disco da VPS.
    *   **`n8n`:** O serviço do n8n. Usaremos a imagem oficial do n8n e também configuraremos um volume para seus dados persistentes.
4.  **`.dockerignore`:** Um arquivo simples para garantir que não copiemos arquivos desnecessários (como `__pycache__`, `.git`, ambientes virtuais) para dentro da imagem Docker, mantendo-a leve e segura.

Com esses quatro arquivos, teremos um ambiente de produção robusto e replicável.

---

### **Experience (Perspectiva de Usabilidade)**

Ótimo. A eliminação do Ngrok simplifica a arquitetura, mas a configuração precisa ser clara.

1.  **Ponto de Conexão (A Nova URL):**
    *   Quando os dois serviços (`familyos-app` e `n8n`) estiverem rodando sob o mesmo `docker-compose`, o Docker cria uma rede interna para eles. Dentro dessa rede, um contêiner pode chamar o outro usando o **nome do serviço como hostname**.
    *   Portanto, a nova URL a ser usada no nó "HTTP Request" do n8n não será um IP público nem `localhost`. Será: `http://familyos-app:5000/magic`. O Docker resolverá `familyos-app` para o IP interno correto do contêiner da nossa aplicação.

2.  **Redução de Fricção (Como Facilitar):**
    *   Hardcodar `http://familyos-app:5000/magic` no n8n funciona, mas não é elegante. A melhor prática é usar **variáveis de ambiente**.
    *   **Minha proposta:** No arquivo `docker-compose.yml`, podemos passar uma variável de ambiente para o serviço do n8n.
        ```yaml
        services:
          n8n:
            image: n8nio/n8n
            environment:
              - FAMILYOS_API_URL=http://familyos-app:5000/magic
            # ... resto da configuração
        ```
    *   **Instrução para o usuário:** Dentro do workflow do n8n, no campo URL do nó "HTTP Request", em vez de digitar a URL, o usuário usará uma **Expressão**: `{{ $env.FAMILYOS_API_URL }}`.
    *   **Vantagens:** Isso desacopla a configuração do n8n da arquitetura. Se um dia mudarmos o nome do serviço ou a porta, só precisamos atualizar o `docker-compose.yml` em um único lugar, sem precisar editar o workflow. É mais limpo, profissional e muito mais fácil de manter.

---

**Visão Técnica - Sprint 5 (Deploy em Produção na VPS)**

**1. Objetivo Arquitetural:**
Migrar o ambiente de desenvolvimento local (Flask + Ngrok) para um ambiente de produção unificado e persistente na VPS da HostGator, utilizando Docker e Docker Compose para orquestração de serviços. Isso eliminará a dependência do Ngrok e do computador local, garantindo disponibilidade 24/7.

**2. Arquitetura de Orquestração (`docker-compose.yml`):**
A espinha dorsal do deploy será um arquivo `docker-compose.yml` que definirá e conectará dois serviços principais:

*   **Serviço `familyos-app` (Nosso Backend):**
    *   **Build:** Será construído a partir de um `Dockerfile` local.
    *   **Rede:** Operará na rede interna do Docker Compose, sendo acessível aos outros contêineres pelo hostname `familyos-app`.
    *   **Portas:** A porta interna `5000` do contêiner (onde o Gunicorn escuta) será mapeada para a porta `8000` da VPS. O acesso externo se dará por `http://<IP_DA_VPS>:8000`.

*   **Serviço `n8n` (Automação):**
    *   **Build:** Utilizará a imagem oficial `n8nio/n8n`.
    *   **Rede:** Operará na mesma rede, permitindo a comunicação direta com o `familyos-app`.
    *   **Portas:** A porta padrão `5678` do n8n será mapeada para a porta `5678` da VPS.

**3. Estratégia de Dados (SQLite com Concorrência Controlada):**
*   **Banco de Dados:** Para simplificar e acelerar o deploy, **manteremos o SQLite**.
*   **Mitigação de Risco:** O principal risco do SQLite em produção (`database is locked`) será mitigado configurando o servidor WSGI (Gunicorn) para operar com **um único worker** (`--workers 1`). Isso serializa as requisições de escrita, sendo uma solução aceitável para o baixo volume de tráfego esperado.
*   **Persistência:** A persistência do arquivo `todo_market.db` será garantida através de um **volume Docker**. O diretório `src` dentro do contêiner será mapeado para um diretório no host da VPS (ex: `/root/familyos/src`), garantindo que o arquivo do banco de dados sobreviva a reinicializações e recriações do contêiner.

**4. Containerização da Aplicação (`Dockerfile`):**
A imagem da nossa aplicação será definida por um `Dockerfile` com os seguintes passos técnicos:
1.  **Base Image:** `FROM python:3.11-slim` para manter a imagem leve.
2.  **Working Directory:** `WORKDIR /app` para organizar os arquivos dentro do contêiner.
3.  **Cache de Dependências:** Copiar `requirements.txt` primeiro e executar `pip install` em um passo separado. Isso aproveita o cache de camadas do Docker, acelerando builds futuros se apenas o código-fonte for alterado.
4.  **Código-Fonte:** Copiar o diretório `src` para o `WORKDIR`.
5.  **Comando de Execução (Entrypoint):** Utilizar `CMD` para iniciar a aplicação via **Gunicorn**, não o servidor de desenvolvimento do Flask. O comando será: `gunicorn --workers 1 --bind 0.0.0.0:5000 app:app`.
    *   `--bind 0.0.0.0:5000`: Essencial para que o Gunicorn aceite conexões de fora do contêiner (da rede Docker).

**5. Configuração e Comunicação Inter-Serviços:**
*   **Endpoint da API:** O n8n não usará mais uma URL pública do Ngrok. A comunicação será interna na rede Docker. A URL a ser configurada no nó "HTTP Request" do n8n será `http://familyos-app:5000/magic`.
*   **Desacoplamento via Variáveis de Ambiente:** Para evitar hardcoding e facilitar a manutenção, a URL da API será passada para o contêiner do n8n através de uma variável de ambiente no `docker-compose.yml`:


   👉 Acionar Builder? (s/n): n

------------------------------------------------------------
👤 Você: Alpha, descoberta crucial: A VPS já roda n8n com Docker e Traefik. Mudança de estratégia: Vamos integrar nosso app no docker-compose.yml existente.Architect: Analise o cenário. Precisamos adicionar um serviço familyos-app no docker-compose. Como configurar as labels do Traefik para que ele responda em um subdomínio (ex: api.thiagoscutari.com.br ou path /api)?Builder: Crie os arquivos locais (Dockerfile, requirements.txt) para que eu possa subir para a VPS e fazer o build lá. Não crie um docker-compose novo, apenas o trecho de código (snippet) para eu adicionar no existente.Experience: Como vamos testar isso? Precisaremos apontar o DNS (subdomínio) na Hostgator?

   📢 [SISTEMA]: Debate...
🤖 Alpha: Entendido. Descoberta crucial que otimiza nossa estratégia. Integrar a uma stack existente com Traefik é um cenário de produção ideal.

Equipe, mudança de plano. A Sprint 5 agora é sobre **integração com a infraestrutura existente na VPS**. Vamos aproveitar o Traefik para exposição segura e profissional da nossa API.

---

### **Architect, sua análise:**

O cenário mudou para melhor. Traefik é um reverse proxy moderno que se integra nativamente com Docker, o que simplifica enormemente a nossa vida.

1.  **Análise do Cenário:** Traefik funciona "escutando" os eventos do Docker. Quando um novo contêiner é iniciado com *labels* específicas, o Traefik automaticamente o detecta e cria as rotas necessárias para direcionar o tráfego da internet para ele, incluindo a gestão de certificados SSL (HTTPS) via Let's Encrypt.
2.  **Configuração via Labels:** Para integrar nosso serviço `familyos-app`, não mexeremos na configuração do Traefik diretamente. Em vez disso, adicionaremos um conjunto de `labels` à definição do nosso serviço no `docker-compose.yml` existente. Essas labels são as instruções que o Traefik lê.

    **Para expor em um subdomínio (ex: `api.thiagoscutari.com.br`):** Esta é a abordagem **recomendada**, pois é mais limpa e escalável. As labels seriam:

    ```yaml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.familyos.rule=Host(`api.thiagoscutari.com.br`)"
      - "traefik.http.routers.familyos.entrypoints=websecure"
      - "traefik.http.tls.certresolver=myresolver" # 'myresolver' é o nome comum do resolvedor Let's Encrypt, pode variar.
      - "traefik.http.services.familyos.loadbalancer.server.port=5000" # Informa ao Traefik que nosso app roda na porta 5000 DENTRO do container.
    ```

    **Para expor em um path (ex: `.../api`):** Menos comum para APIs, mas possível. A label `rule` mudaria:

    ```yaml
    # Alternativa:
    - "traefik.http.routers.familyos.rule=Host(`www.thiagoscutari.com.br`) && PathPrefix(`/api`)"
    ```

**Veredito do Architect:** Devemos usar a abordagem de subdomínio. É o padrão da indústria para APIs. O Builder deve preparar o snippet do `docker-compose` com as labels para o subdomínio.

---

### **Builder, seus artefatos:**

Entendido. Não criarei um `docker-compose.yml` novo. Prepararei os arquivos para o build e o snippet para ser inserido no arquivo existente na VPS.

**1. Arquivo: `requirements.txt`** (Para ser colocado na raiz do projeto `familyos`)

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.30
python-dotenv==1.0.1
langchain-google-genai==1.0.6
gunicorn==22.0.0
```

**2. Arquivo: `Dockerfile`** (Para ser colocado na raiz do projeto `familyos`)

```dockerfile
# Usar uma imagem base leve de Python
FROM python:3.11-slim

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiar o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código-fonte da aplicação
COPY ./src .

# Expor a porta que o Gunicorn vai usar
EXPOSE 5000

# Comando para iniciar a aplicação em produção com Gunicorn
# --workers 1 é crucial para evitar problemas de concorrência com o SQLite
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]
```

**3. Snippet para `docker-compose.yml` existente:**

Alpha, este é o trecho de código que você (ou quem tiver acesso à VPS) deve adicionar à seção `services:` do `docker-compose.yml` que já está rodando.

```yaml
# --- INÍCIO DO SNIPPET PARA ADICIONAR ---

  familyos-app:
    build: ./familyos # IMPORTANTE: O Dockerfile e requirements.txt devem estar dentro de uma pasta 'familyos' ao lado do docker-compose.yml
    restart: unless-stopped
    volumes:
      - ./familyos/src:/app/src # Mapeia a pasta src para persistir o banco de dados SQLite
    networks:
      - traefik_default # IMPORTANTE: Use o nome da rede que o Traefik e o n8n já usam
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.familyos.rule=Host(`api.thiagoscutari.com.br`)" # <- Mudar para o subdomínio desejado
      - "traefik.http.routers.familyos.entrypoints=websecure"
      - "traefik.http.tls.certresolver=myresolver" # <- Confirmar o nome do certresolver
      - "traefik.http.services.familyos.loadbalancer.server.port=5000"

# --- FIM DO SNIPPET ---
```

---

### **Experience, seu plano de testes:**

A integração com Traefik e DNS torna o teste mais direto e realista.

1.  **Configuração de DNS:** Sim, o primeiro passo, que pode ser feito em paralelo, é **apontar o subdomínio para a VPS**. Na zona de DNS da HostGator para o domínio `thiagoscutari.com.br`, precisamos criar um **Registro A**:
    *   **Tipo:** `A`
    *   **Nome/Host:** `api` (ou o subdomínio escolhido)
    *   **Valor/Aponta para:** `<O_ENDEREÇO_IP_PÚBLICO_DA_VPS>`
    *   **TTL:** Pode deixar o padrão (ex: 14400).
    *   *Nota: A propagação do DNS pode levar de alguns minutos a algumas horas.*

2.  **Plano de Teste (Passo a Passo):**
    *   **Passo 1 (Deploy):** Após subir os arquivos para a VPS e adicionar o snippet ao `docker-compose.yml`, rodar o comando `docker-compose up -d --build familyos-app` no terminal da VPS.
    *   **Passo 2 (Verificação de Logs):** Imediatamente rodar `docker-compose logs -f familyos-app` para garantir que o Gunicorn iniciou sem erros e a aplicação está rodando.
    *   **Passo 3 (Verificação do Traefik):** Acessar o dashboard do Traefik (se estiver exposto). Lá, devemos ver um novo "Router" e "Service" chamado `familyos`, e ambos devem estar com o status verde/saudável.
    *   **Passo 4 (Teste de Endpoint):** Quando o DNS propagar, usar uma ferramenta como Postman ou `curl` para fazer uma requisição `POST` para `https://api.thiagoscutari.com.br/magic`. Devemos receber uma resposta de sucesso (ou um erro 400 de JSON inválido), mas **não** um erro 404 (Not Found) ou 502 (Bad Gateway).
    *   **Passo 5 (Teste End-to-End):** Atualizar o nó "HTTP Request" no workflow do n8n para a nova URL pública (`https://api.thiagoscutari.com.br/magic`). Enviar uma mensagem de áudio no Telegram e verificar se o item é adicionado à lista acessando a interface web (`http://<IP_DA_VPS>:8000`). Este é o teste final de validação.
🤖 Architect: Com certeza. Esta é a visão técnica consolidada para a integração da aplicação no ambiente de produção existente com Docker e Traefik.

---

**Visão Técnica - Sprint 5 (Integração com Infraestrutura de Produção)**

**1. Objetivo Arquitetural:**
Integrar a aplicação `FamilyOS` como um novo serviço (`familyos-app`) dentro do `docker-compose.yml` existente na VPS. O objetivo é expor a API de forma segura e profissional através do reverse proxy Traefik, utilizando um subdomínio dedicado (ex: `api.thiagoscutari.com.br`) com SSL (HTTPS) gerenciado automaticamente.

**2. Artefatos de Deploy:**
Dois arquivos de configuração são necessários na VPS, dentro de um diretório `familyos/` adjacente ao arquivo `docker-compose.yml`:

*   **`requirements.txt`:** Define as dependências Python exatas, incluindo `gunicorn` como o servidor WSGI de produção.
*   **`Dockerfile`:** Contém a receita para construir a imagem Docker da aplicação. As etapas chave são:
    *   Utiliza uma imagem base leve (`python:3.11-slim`).
    *   Instala as dependências a partir do `requirements.txt`.
    *   Copia o código-fonte da aplicação (`./src`) para o diretório `/app` do contêiner.
    *   Define o comando de execução `CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]`. A diretiva `--workers 1` é uma mitigação de risco deliberada para evitar problemas de concorrência com o banco de dados SQLite. O `--bind 0.0.0.0:5000` é essencial para que o serviço seja acessível de fora do contêiner (pela rede Docker).

**3. Integração com Docker Compose e Traefik:**
A integração é realizada adicionando um novo serviço ao `docker-compose.yml` existente. A comunicação com o Traefik é configurada exclusivamente através de `labels` do Docker.

*   **Definição do Serviço (`familyos-app`):**
    *   `build: ./familyos`: Instrução para o Docker Compose construir a imagem a partir do `Dockerfile` no diretório especificado.
    *   `restart: unless-stopped`: Política de reinicialização para garantir que o serviço se recupere de falhas ou reinicializações do servidor.
    *   `volumes: ['./familyos/src:/app/src']`: Mapeamento de volume crítico que persiste o arquivo `todo_market.db` no disco do host, garantindo a durabilidade dos dados.
    *   `networks: ['traefik_default']`: Conecta o contêiner à rede virtual do Traefik, permitindo que o Traefik descubra e se comunique com o serviço. O nome da rede (`traefik_default`) deve corresponder ao da configuração existente.

*   **Configuração do Traefik via Labels:**
    *   `traefik.enable=true`: Ativa a gestão deste contêiner pelo Traefik.
    *   `traefik.http.routers.familyos.rule=Host(\`api.thiagoscutari.com.br\`)`: Define a regra de roteamento. O Traefik direcionará o tráfego para este serviço somente se o cabeçalho `Host` da requisição corresponder ao subdomínio especificado.
    *   `traefik.http.routers.familyos.entrypoints=websecure`: Associa o roteador ao ponto de entrada `websecure`, que geralmente corresponde à porta 443 (HTTPS).
    *   `traefik.http.tls.certresolver=myresolver`: Instrui o Traefik a obter e gerenciar automaticamente um certificado SSL/TLS para este subdomínio usando o resolvedor de certificados configurado (geralmente Let's Encrypt).
    *   `traefik.http.services.familyos.loadbalancer.server.port=5000`: Informa ao Traefik para qual porta, *dentro do contêiner*, o tráfego deve ser encaminhado.

**4. Fluxo de Rede de uma Requisição (End-to-End):**
1.  **DNS:** Uma requisição para `https://api.thiagoscutari.com.br/magic` é feita. O DNS resolve o subdomínio para o endereço IP público da VPS.
2.  **Traefik (Entrypoint):** A requisição chega à VPS na porta 443. O Traefik, que está escutando nesta porta (`websecure` entrypoint), a intercepta.
3.  **Traefik (Routing):** O Traefik analisa o cabeçalho `Host` da requisição. Ele encontra uma correspondência com a regra definida nas labels do serviço `familyos-app`.
4.  **Traefik (Service Forwarding):** O Traefik encaminha a requisição, através da rede interna do Docker, para o endereço IP interno do contêiner `familyos-app` na porta `5000`.
5.  **Gunicorn/Flask (Application):** O Gunicorn, escutando na porta `5000` dentro do contêiner, recebe a requisição e a passa para a aplicação Flask para processamento. A resposta segue o caminho inverso.

**5. Estratégia de Teste e Validação:**
1.  **Configuração de DNS:** Criar um **Registro A** no painel de controle do domínio, apontando o subdomínio `api` para o IP da VPS.
2.  **Deploy:** Executar `docker-compose up -d --build familyos-app` na VPS para construir a imagem e iniciar o novo serviço.
3.  **Verificação de Logs:** Monitorar os logs do contêiner com `docker-compose logs -f familyos-app` para confirmar a inicialização bem-sucedida do Gunicorn.
4.  **Validação do Endpoint:** Utilizar `curl` ou Postman para fazer uma requisição `POST` para `https://api.thiagoscutari.com.br/magic` e verificar se uma resposta HTTP 2xx ou 4xx é recebida (indicando que a aplicação está respondendo).
5.  **Teste de Integração:** Atualizar o workflow do n8n para usar a nova URL pública e executar um teste completo, desde o envio de uma mensagem no Telegram até a verificação do item na interface web.