import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
import datetime

# Configuração do Banco
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = 'sqlite:///' + os.path.join(basedir, 'todo_market.db')
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# --- DEFINIÇÃO DOS MODELOS (Atualizado com coluna 'usuario') ---

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50), unique=True, nullable=False)

class UnidadeMedida(Base):
    __tablename__ = 'unidades_medida'
    id = Column(Integer, primary_key=True)
    nome = Column(String(20), unique=True, nullable=False)
    simbolo = Column(String(5), unique=True, nullable=False)

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    unidade_padrao_id = Column(Integer, ForeignKey('unidades_medida.id'), nullable=True)

class TipoLista(Base):
    __tablename__ = 'tipos_lista'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False, unique=True)

class ListaItem(Base):
    __tablename__ = 'lista_itens'
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'))
    tipo_lista_id = Column(Integer, ForeignKey('tipos_lista.id'), default=1)
    quantidade = Column(Float, nullable=False)
    unidade_id = Column(Integer, ForeignKey('unidades_medida.id'))
    
    # --- AQUI ESTÁ A NOVA COLUNA ---
    usuario = Column(String(50)) 
    
    status = Column(String(20), default='pendente')
    adicionado_em = Column(DateTime, default=datetime.datetime.utcnow)
    origem_input = Column(String(100))

# --- SCRIPT DE INICIALIZAÇÃO ---

def seed_database():
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Recria as tabelas
        Base.metadata.drop_all(engine) # Apaga tudo antigo
        Base.metadata.create_all(engine) # Cria tudo novo com a coluna 'usuario'
        
        # Seed Inicial
        categorias = ['Hortifrúti', 'Padaria', 'Carnes', 'Limpeza', 'Outros']
        for c in categorias:
            session.add(Categoria(nome=c))
            
        unidades = [
            {'nome': 'quilograma', 'simbolo': 'kg'},
            {'nome': 'grama', 'simbolo': 'g'},
            {'nome': 'litro', 'simbolo': 'L'},
            {'nome': 'unidade', 'simbolo': 'un'},
            {'nome': 'pacote', 'simbolo': 'pct'}
        ]
        for u in unidades:
            session.add(UnidadeMedida(nome=u['nome'], simbolo=u['simbolo']))
            
        tipos = ['Mercado', 'Farmácia', 'Casa']
        for t in tipos:
            session.add(TipoLista(nome=t))
            
        session.commit()
        print("✅ Banco de dados recriado com a coluna 'usuario'!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()