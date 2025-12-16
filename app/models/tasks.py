import datetime
from app.extensions import db

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    responsavel = db.Column(db.String(50)) # Thiago, Debora, Casal
    prioridade = db.Column(db.Integer, default=1) # 1=Baixa, 2=Media, 3=Alta
    status = db.Column(db.String(20), default='pendente')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    calendar_id = db.Column(db.String(100), nullable=True)
    parent_id = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20)) # 'needsAction' ou 'completed'
    usuario = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)