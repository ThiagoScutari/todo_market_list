FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala Python Libs - esta etapa é cacheadada separadamente
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO o conteúdo da pasta src local para /app/src no container
COPY src/ ./src/

# Define variáveis de ambiente
ENV FLASK_APP=src/app.py
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "src/app.py"]