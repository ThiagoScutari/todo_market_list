# 🔐 Guia de Configuração de Ambiente (Docker & .env)

Este documento detalha como configurar as variáveis sensíveis do projeto FamilyOS para garantir segurança e funcionamento correto no Docker.

## 1. Onde fica o arquivo?
O arquivo de configuração deve se chamar \`.env\` e deve estar localizado na **raiz do projeto de infraestrutura**, ao lado do arquivo \`docker-compose.yml\`.

**Caminho Padrão:** \`/opt/n8n-traefik/.env\`

---

## 2. Estrutura do Arquivo .env
O arquivo deve conter as seguintes chaves. Copie o modelo abaixo e preencha com seus dados reais.

\`\`\`bash
# --- CONFIGURAÇÕES GERAIS ---
TZ=America/Sao_Paulo

# --- SEGURANÇA FLASK ---
# Gere uma chave aleatória para assinar os cookies de sessão
SECRET_KEY=sua_chave_secreta_aqui

# --- BANCO DE DADOS ---
# Caminho interno do container (NÃO ALTERAR se usar o padrão do docker-compose)
DATABASE_URL=sqlite:////app/data/familyos.db

# --- INTELIGÊNCIA ARTIFICIAL (GOOGLE GEMINI) ---
# Obtenha sua chave em: https://aistudio.google.com/
GOOGLE_API_KEY=sua_chave_do_google_aqui
\`\`\`

---

## 3. Como o Docker lê essas variáveis?
No arquivo \`docker-compose.yml\`, as variáveis são passadas para o container usando a sintaxe \`\${VARIAVEL}\`.

**Exemplo no docker-compose.yml:**
\`\`\`yaml
  familyos-app:
    environment:
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - SECRET_KEY=\${SECRET_KEY}
\`\`\`

Isso diz ao Docker: *"Pegue o valor que está no arquivo .env do host e injete dentro do container com o mesmo nome"*.

---

## 4. Comandos de Manutenção

### 4.1 Verificar se o Docker está lendo o arquivo
Antes de subir o container, você pode testar se o Docker consegue "enxergar" as variáveis:

\`\`\`bash
cd /opt/n8n-traefik
docker compose config
\`\`\`
*Se o comando exibir o YAML com as chaves preenchidas (ex: GOOGLE_API_KEY=AIza...), está funcionando.*

### 4.2 Aplicar alterações
Sempre que você editar o arquivo \`.env\`, é necessário recriar o container para que as novas variáveis entrem em vigor:

\`\`\`bash
cd /opt/n8n-traefik
docker compose down
docker compose up -d familyos-app
\`\`\`

---

## 5. Solução de Problemas

* **Erro "IA Off" ou "Config IA Falhou":** Significa que a \`GOOGLE_API_KEY\` está vazia ou incorreta dentro do container. Verifique se o nome da variável no \`.env\` é exatamente igual ao do \`docker-compose.yml\`.
* **Arquivo .env não existe:** O Docker usará valores vazios, causando falhas na aplicação.

## 6. Entendendo a Infraestrutura (Dockerfile)

O arquivo \`Dockerfile\` foi construído utilizando boas práticas de **Multi-Stage Build** para manter a imagem leve e segura. Abaixo, a explicação detalhada de cada bloco:

### 6.1 A Base (Estágio 1)
\`\`\`dockerfile
FROM python:3.11-slim
\`\`\`
* Usamos a versão **slim** do Python (baseada em Debian) porque ela contém apenas o essencial para rodar o Python, resultando em uma imagem muito menor e com menos vulnerabilidades de segurança que a versão *full*.

### 6.2 Dependências do Sistema (Estágio 2)
\`\`\`dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
\`\`\`
* Instalamos o **gcc** (compilador C) porque algumas bibliotecas Python (como SQLAlchemy ou drivers de banco) precisam compilar componentes nativos durante a instalação.
* Limpamos o cache do \`apt\` logo em seguida para não inflar o tamanho da imagem final.

### 6.3 Dependências Python (Estágio 3)
\`\`\`dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
\`\`\`
* Copiamos **apenas** o \`requirements.txt\` primeiro.
* **Por que?** O Docker usa cache de camadas. Se você mudar uma linha no código fonte (\`app.py\`), o Docker *não* precisará baixar todas as bibliotecas de novo, pois o \`requirements.txt\` não mudou. Isso acelera o deploy de minutos para segundos.

### 6.4 O Código Fonte (Estágio 4)
\`\`\`dockerfile
COPY src/ ./src/
ENV FLASK_APP=src/app.py
\`\`\`
* Aqui copiamos o código da aplicação.
* Definimos a variável de ambiente para o Flask saber onde está o "cérebro" do app.

### 6.5 Inicialização e Logs (Estágio 5)
\`\`\`dockerfile
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "src.app:app"]
\`\`\`
* **Gunicorn:** É o servidor de produção (o Flask sozinho não aguenta tráfego real).
* **-w 1:** Um "worker". Como é para uso familiar, 1 processo economiza memória RAM da VPS.
* **--access-logfile -**: O traço (\`-\`) manda os logs para a saída padrão (stdout). **Isso é crucial** para que o comando \`docker logs\` funcione e possamos debugar erros.

```plaintext
## 6. Entendendo a Infraestrutura (Dockerfile)

O arquivo \`Dockerfile\` foi construído utilizando boas práticas de **Multi-Stage Build** para manter a imagem leve e segura. Abaixo, a explicação detalhada de cada bloco:

### 6.1 A Base (Estágio 1)
\`\`\`dockerfile
FROM python:3.11-slim
\`\`\`
* Usamos a versão **slim** do Python (baseada em Debian) porque ela contém apenas o essencial para rodar o Python, resultando em uma imagem muito menor e com menos vulnerabilidades de segurança que a versão *full*.

### 6.2 Dependências do Sistema (Estágio 2)
\`\`\`dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
\`\`\`
* Instalamos o **gcc** (compilador C) porque algumas bibliotecas Python (como SQLAlchemy ou drivers de banco) precisam compilar componentes nativos durante a instalação.
* Limpamos o cache do \`apt\` logo em seguida para não inflar o tamanho da imagem final.

### 6.3 Dependências Python (Estágio 3)
\`\`\`dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
\`\`\`
* Copiamos **apenas** o \`requirements.txt\` primeiro.
* **Por que?** O Docker usa cache de camadas. Se você mudar uma linha no código fonte (\`app.py\`), o Docker *não* precisará baixar todas as bibliotecas de novo, pois o \`requirements.txt\` não mudou. Isso acelera o deploy de minutos para segundos.

### 6.4 O Código Fonte (Estágio 4)
\`\`\`dockerfile
COPY src/ ./src/
ENV FLASK_APP=src/app.py
\`\`\`
* Aqui copiamos o código da aplicação.
* Definimos a variável de ambiente para o Flask saber onde está o "cérebro" do app.

### 6.5 Inicialização e Logs (Estágio 5)
\`\`\`dockerfile
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "src.app:app"]
\`\`\`
* **Gunicorn:** É o servidor de produção (o Flask sozinho não aguenta tráfego real).
* **-w 1:** Um "worker". Como é para uso familiar, 1 processo economiza memória RAM da VPS.
* **--access-logfile -**: O traço (\`-\`) manda os logs para a saída padrão (stdout). **Isso é crucial** para que o comando \`docker logs\` funcione e possamos debugar erros.
EOF
```

## 7. Entendendo o Orquestrador (Docker Compose)

O arquivo \`docker-compose.yml\` define como todos os serviços (Traefik, n8n, Banco de Dados e nosso App) conversam entre si. Abaixo, a explicação focada no bloco do **FamilyOS**:

### 7.1 Definição do Serviço
\`\`\`yaml
  familyos-app:
    container_name: familyos_app
    build: ./familyos
    restart: always
\`\`\`
* **container_name:** Define um nome fixo para facilitar o uso de comandos (ex: \`docker logs familyos_app\`).
* **build:** Indica que a imagem deve ser construída a partir da pasta \`./familyos\` (onde está o Dockerfile), em vez de baixar da internet.
* **restart: always:** Se o app falhar ou o servidor reiniciar, o Docker tenta subir ele de novo automaticamente.

### 7.2 Comando de Execução (Logs e Debug)
\`\`\`yaml
    command: gunicorn -w 1 -b 0.0.0.0:5000 --access-logfile - --error-logfile - --log-level info src.app:app
\`\`\`
* Este comando substitui o padrão do Dockerfile para garantir que os **logs** (de acesso e de erro) sejam enviados para o terminal do Docker (\`stdout\`), permitindo que você veja o que está acontecendo com \`docker logs\`.

### 7.3 Variáveis de Ambiente (Segurança)
\`\`\`yaml
    environment:
      - SECRET_KEY=\${SECRET_KEY}
      - DATABASE_URL=\${DATABASE_URL}
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - TZ=\${TZ}
\`\`\`
* Aqui ocorre a mágica da segurança. O Docker lê as variáveis do arquivo \`.env\` (do host) e as injeta dentro do container. O código Python lê essas variáveis internas, nunca expondo as chaves no código fonte.

### 7.4 Persistência de Dados (Volumes)
\`\`\`yaml
    volumes:
      - ./familyos/src:/app/src
      - ./familyos/data:/app/data
\`\`\`
* **src:** Mapeia o código fonte. Isso permite que você edite um arquivo Python na VPS e a alteração reflita no container (após restart).
* **data:** **CRÍTICO.** Mapeia o banco de dados SQLite. Garante que, se você destruir o container, sua lista de compras continua salva na pasta \`familyos/data\` da VPS.

### 7.5 Rede e Roteamento (Traefik)
\`\`\`yaml
    networks:
      - app_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.familyos.rule=Host(\`api.thiagoscutari.com.br\`)"
      - "traefik.http.routers.familyos.entrypoints=websecure"
      - "traefik.http.routers.familyos.tls.certresolver=le"
      - "traefik.http.services.familyos.loadbalancer.server.port=5000"
\`\`\`
* Coloca o app na mesma rede do Traefik e define as regras para que, quando alguém acessar \`api.thiagoscutari.com.br\`, o Traefik saiba que deve encaminhar a requisição para este container na porta 5000, já cuidando do certificado SSL (HTTPS) automaticamente.
