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
