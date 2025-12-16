from flask_login import UserMixin
from werkzeug.security import check_password_hash
from app.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    def check_password(self, password):
        # Preservando sua lógica original de senhas legadas/simples
        if self.password_hash in ['2904', '1712']: 
            return self.password_hash == password
        return check_password_hash(self.password_hash, password)

class WeatherCache(db.Model):
    __tablename__ = 'weather_cache'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(50))
    data_json = db.Column(db.Text) # JSON string da API externa
    last_updated = db.Column(db.DateTime)