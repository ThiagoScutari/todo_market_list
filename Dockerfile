# --- ESTÁGIO 1: Imagem Base ---
# Usamos Python 3.11 na versão 'slim' (mais leve, baseada em Debian)
FROM python:3.11-slim

# Define a pasta de trabalho dentro do container
WORKDIR /app

# --- ESTÁGIO 2: Dependências do Sistema ---
# Instala compiladores básicos (gcc) necessários para algumas libs Python
# O comando 'rm -rf' limpa o cache do apt para deixar a imagem pequena
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# --- ESTÁGIO 3: Dependências Python ---
# Copia apenas o arquivo de requisitos primeiro (para aproveitar cache do Docker)
COPY requirements.txt .
# Instala as bibliotecas sem salvar cache do pip (economiza espaço)
RUN pip install --no-cache-dir -r requirements.txt

# --- ESTÁGIO 4: Código Fonte ---
# Copia todo o conteúdo da pasta 'src' local para '/app/src' no container
COPY src/ ./src/

# Define variável de ambiente para o Flask localizar o aplicativo
ENV FLASK_APP=src/app.py

# --- ESTÁGIO 5: Inicialização ---
# Inicia o servidor Gunicorn:
# -w 1: Um processo worker (suficiente para uso familiar)
# -b 0.0.0.0:5000: Escuta em todas as interfaces na porta 5000
# --access-logfile -: Envia logs de acesso para o terminal (stdout)
# --error-logfile -: Envia logs de erro para o terminal (stderr)
# --log-level info: Define nível de detalhe dos logs
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "src.app:app"]
