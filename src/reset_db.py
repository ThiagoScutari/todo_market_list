import os
from app import app, db, Categoria, UnidadeMedida, TipoLista, User

def resetar_banco():
    with app.app_context():
        # --- NOVO: Garante que o diretório de dados exista ---
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            print(f"📂 Criando diretório de dados em: {db_dir}")
            os.makedirs(db_dir)

        # 1. Apaga tudo e recria as tabelas
        print("🗑️  Apagando banco antigo...")
        db.drop_all()
        print("🔨 Criando novas tabelas...")
        db.create_all()

        # 2. Cria Usuários Fixos
        print("👤 Criando usuários 'thiago' e 'debora'...")
        # NOTA: Em um ambiente real, as senhas seriam hasheadas.
        # Para esta sprint, estamos usando texto plano conforme solicitado.
        user_thiago = User(username='thiago', password_hash='2904')
        user_debora = User(username='debora', password_hash='1712')
        
        db.session.add(user_thiago)
        db.session.add(user_debora)

        # 3. Insere Dados Iniciais (Seed)
        print("🌱 Semeando dados...")
        
        # Categorias Sugeridas no Prompt
        categorias = [
            'Hortifrúti', 'Padaria', 'Carnes', 'Limpeza', 'Bebidas', 
            'Churrasco', 'Laticínios', 'Outros'
        ]
        for c in categorias:
            db.session.add(Categoria(nome=c))

        # Unidades
        unidades = [
            {'nome': 'quilograma', 'simbolo': 'kg'},
            {'nome': 'grama', 'simbolo': 'g'},
            {'nome': 'litro', 'simbolo': 'L'},
            {'nome': 'mililitro', 'simbolo': 'ml'},
            {'nome': 'unidade', 'simbolo': 'un'},
            {'nome': 'pacote', 'simbolo': 'pct'},
            {'nome': 'caixa', 'simbolo': 'cx'}
        ]
        for u in unidades:
            db.session.add(UnidadeMedida(nome=u['nome'], simbolo=u['simbolo']))

        # Tipos de Lista
        tipos = ['Mercado', 'Farmácia', 'Casa']
        for t in tipos:
            db.session.add(TipoLista(nome=t))

        db.session.commit()
        print("✅ Banco de dados recriado com sucesso!")
        print("🔑 Usuários criados: thiago (senha: 2904), debora (senha: 1712)")

if __name__ == "__main__":
    resetar_banco()
