import os
import datetime

# Define o diretório base (sobe um nível de 'app/' para a raiz do projeto)
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    # --- Segurança e Sessão ---
    SECRET_KEY = os.getenv("SECRET_KEY", "segredo")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = datetime.timedelta(days=30)

    # --- Banco de Dados ---
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Lógica de Construção da URL (Executada ao carregar o arquivo)
    # Usamos uma variável temporária (_db_url) para processar a lógica
    
    _db_url = os.getenv('DATABASE_URL')
        
    if not _db_url:
        # Fallback local apenas para segurança
        # Aponta para: raiz/data/familyos.db
        _db_path = os.path.join(basedir, 'data', 'familyos.db')
        _db_url = f'sqlite:///{_db_path}'

    # Correção para o SQLAlchemy (Postgres requer postgresql://)
    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
            
    # Atribui o resultado final à variável de configuração real
    SQLALCHEMY_DATABASE_URI = _db_url