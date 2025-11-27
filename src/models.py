
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class Categoria(Base):
    __tablename__ = 'categorias'

    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False, unique=True)

    produtos = relationship("Produto", back_populates="categoria")


class UnidadeMedida(Base):
    __tablename__ = 'unidades_medida'

    id = Column(Integer, primary_key=True)
    nome = Column(String(10), nullable=False, unique=True)
    simbolo = Column(String(5), unique=True)

    produtos_padrao = relationship("Produto", back_populates="unidade_padrao", foreign_keys="Produto.unidade_padrao_id")
    receita_ingredientes_unidade = relationship("ReceitaIngrediente", back_populates="unidade", foreign_keys="ReceitaIngrediente.unidade_id")
    lista_itens_unidade = relationship("ListaItem", back_populates="unidade", foreign_keys="ListaItem.unidade_id")


class Produto(Base):
    __tablename__ = 'produtos'

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    categoria_id = Column(Integer, ForeignKey('categorias.id'))
    unidade_padrao_id = Column(Integer, ForeignKey('unidades_medida.id'))

    categoria = relationship("Categoria", back_populates="produtos")
    unidade_padrao = relationship("UnidadeMedida", back_populates="produtos_padrao", foreign_keys="Produto.unidade_padrao_id")
    receita_ingredientes = relationship("ReceitaIngrediente", back_populates="produto")
    lista_itens = relationship("ListaItem", back_populates="produto")


class Receita(Base):
    __tablename__ = 'receitas'

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    instrucoes = Column(Text)
    adicionado_em = Column(DateTime, default=datetime.datetime.utcnow)

    ingredientes = relationship("ReceitaIngrediente", back_populates="receita")


class ReceitaIngrediente(Base):
    __tablename__ = 'receita_ingredientes'

    receita_id = Column(Integer, ForeignKey('receitas.id'), primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), primary_key=True)
    quantidade = Column(Float, nullable=False)
    unidade_id = Column(Integer, ForeignKey('unidades_medida.id'))

    receita = relationship("Receita", back_populates="ingredientes")
    produto = relationship("Produto", back_populates="receita_ingredientes")
    unidade = relationship("UnidadeMedida", back_populates="receita_ingredientes_unidade", foreign_keys="ReceitaIngrediente.unidade_id")


class TipoLista(Base):
    __tablename__ = 'tipos_lista'

    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False, unique=True)

    lista_itens = relationship("ListaItem", back_populates="tipo_lista")


class ListaItem(Base):
    __tablename__ = 'lista_itens'

    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'))
    tipo_lista_id = Column(Integer, ForeignKey('tipos_lista.id'), default=1) # Default para "Mercado" (assumindo que "Mercado" terá ID 1)
    quantidade = Column(Float, nullable=False)
    unidade_id = Column(Integer, ForeignKey('unidades_medida.id'))
    status = Column(String(20), default='pendente') # 'pendente', 'comprado', 'cancelado'
    adicionado_em = Column(DateTime, default=datetime.datetime.utcnow)
    origem_input = Column(String(100)) # ex: "receita_caponata", "manual_telegram", "sugestao_ia"

    produto = relationship("Produto", back_populates="lista_itens")
    tipo_lista = relationship("TipoLista", back_populates="lista_itens")
    unidade = relationship("UnidadeMedida", back_populates="lista_itens_unidade", foreign_keys="ListaItem.unidade_id")


# Exemplo de como configurar o engine e criar as tabelas (para fins de demonstração)
# DATABASE_URL = "postgresql://user:password@host:port/database"
# engine = create_engine(DATABASE_URL)
# Base.metadata.create_all(engine)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

