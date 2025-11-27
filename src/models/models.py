from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50), unique=True, nullable=False)
    produtos = relationship("Produto", back_populates="categoria")

class UnidadeMedida(Base):
    __tablename__ = 'unidades_medida'
    id = Column(Integer, primary_key=True)
    nome = Column(String(20), unique=True, nullable=False)
    simbolo = Column(String(5), unique=True, nullable=False)
    produtos = relationship("Produto", back_populates="unidade_padrao")

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    unidade_padrao_id = Column(Integer, ForeignKey('unidades_medida.id'), nullable=True)
    
    categoria = relationship("Categoria", back_populates="produtos")
    unidade_padrao = relationship("UnidadeMedida", back_populates="produtos")
    lista_itens = relationship("ListaItem", back_populates="produto")

class TipoLista(Base):
    __tablename__ = 'tipos_lista'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False, unique=True)
    lista_itens = relationship("ListaItem", back_populates="tipo_lista")

class ListaItem(Base):
    __tablename__ = 'lista_itens'
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'))
    tipo_lista_id = Column(Integer, ForeignKey('tipos_lista.id'), default=1)
    quantidade = Column(Float, nullable=False)
    unidade_id = Column(Integer, ForeignKey('unidades_medida.id'))
    
    # --- A COLUNA QUE FALTAVA ---
    usuario = Column(String(50)) 
    
    status = Column(String(20), default='pendente')
    adicionado_em = Column(DateTime, default=datetime.datetime.utcnow)
    origem_input = Column(String(100))

    produto = relationship("Produto", back_populates="lista_itens")
    tipo_lista = relationship("TipoLista", back_populates="lista_itens")
    unidade = relationship("UnidadeMedida")