rom app import app, db, User, Categoria, UnidadeMedida

def reset():
    print("🔧 Iniciando Reset do Banco de Dados...")
    with app.app_context():
        # 1. Limpa tudo
        db.drop_all()
        db.create_all()

        # 2. Cria Usuários
        print("👤 Criando usuários...")
        db.session.add(User(username='thiago', password_hash='2904'))
        db.session.add(User(username='debora', password_hash='1712'))

        # 3. Cria Categorias Padrão
        print("📂 Criando categorias...")
        cats = ['HORTIFRÚTI', 'PADARIA', 'CARNES', 'LIMPEZA', 'BEBIDAS', 'OUTROS']
        for c in cats: db.session.add(Categoria(nome=c))

        # 4. Cria Unidades
        print("📏 Criando unidades...")
        db.session.add(UnidadeMedida(nome='unidade', simbolo='un'))
        db.session.add(UnidadeMedida(nome='quilograma', simbolo='kg'))
        db.session.add(UnidadeMedida(nome='grama', simbolo='g'))
        db.session.add(UnidadeMedida(nome='litro', simbolo='L'))

        db.session.commit()
        print("✅ SUCESSO! Banco resetado e populado.")

if __name__ == "__main__":
    reset()