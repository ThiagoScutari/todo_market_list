from app import app, db, Categoria, UnidadeMedida, TipoLista, User

def resetar_banco():
    with app.app_context():
        # 1. Apaga tudo e recria as tabelas
        print("🗑️  Apagando banco antigo...")
        db.drop_all()
        print("🔨 Criando novas tabelas...")
        db.create_all()

        # 2. Cria Usuário ADMIN
        print("👤 Criando usuário Admin...")
        admin = User(username="admin")
        admin.set_password("admin") # Senha padrão
        db.session.add(admin)

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
        print("🔑 Login Inicial: admin / admin")

if __name__ == "__main__":
    resetar_banco()