from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Instanciamos as extensões vazias.
# Elas serão conectadas ao app depois, via db.init_app(app)
db = SQLAlchemy()
login_manager = LoginManager()