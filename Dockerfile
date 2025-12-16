# --- ESTÁGIO 1: Imagem Base ---
FROM python:3.11-slim

WORKDIR /app

# --- ESTÁGIO 2: Dependências ---
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copia requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- ESTÁGIO 3: Código Fonte (A MUDANÇA ESTÁ AQUI) ---
# Antes copiávamos apenas 'src/'. Agora copiamos TUDO (.) para dentro de /app
# Isso inclui: app/, run.py, config.py, etc.
COPY . .

# Variável de ambiente atualizada
ENV FLASK_APP=run.py

# --- ESTÁGIO 4: Inicialização ---
# Mudamos de 'src.app:app' para 'run:app'
# 'run' é o arquivo run.py e 'app' é a variável criada dentro dele
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "run:app"]