from flask import Flask
from app.config import Config
from app.extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Inicializa as Extensões
    db.init_app(app)
    login_manager.init_app(app)
    
    # Define qual é a rota de login (usaremos o blueprint 'auth')
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Faça login para acessar o FamilyOS."
    login_manager.login_message_category = "warning"

    # 2. Configura o User Loader (Essencial para o Flask-Login)
    # Importamos aqui dentro para evitar ciclo de importação
    from app.models.core import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 3. Registro de Blueprints (Rotas)
    
    from app.routes.auth_bp import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.main_bp import main_bp
    app.register_blueprint(main_bp)

    from app.routes.api_bp import api_bp
    app.register_blueprint(api_bp)

    from app.routes.webhook_bp import webhook_bp
    app.register_blueprint(webhook_bp)

    return app