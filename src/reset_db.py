from app import app, db, User, Categoria, UnidadeMedida

def reset():
    print("🔧 Iniciando Reset do Banco de Dados...")
    
    # Garante que o app saiba onde está o banco (lendo do .env via app.py)
    print(f"📡 Conectando em: {app.config['SQLALCHEMY_DATABASE_URI']}")

    with app.app_context():
        # 1. Limpa tudo (Dropa tabelas antigas se existirem)
        db.drop_all()
        
        # 2. Cria a estrutura nova (Schema)
        db.create_all()

        # 3. Cria Usuários
        print("👤 Criando usuários...")
        # Adicionando usuários com as senhas combinadas
        db.session.add(User(username='thiago', password_hash='2904'))
        db.session.add(User(username='debora', password_hash='1712'))

        # 4. Cria Categorias Padrão
        print("📂 Criando categorias...")
        cats = ['HORTIFRÚTI', 'PADARIA', 'CARNES', 'LIMPEZA', 'BEBIDAS', 'OUTROS', 'LATICÍNIOS', 'HIGIENE PESSOAL']
        for c in cats: 
            db.session.add(Categoria(nome=c))

        # 5. Cria Unidades de Medida
        print("📏 Criando unidades...")
        db.session.add(UnidadeMedida(nome='unidade', simbolo='un'))
        db.session.add(UnidadeMedida(nome='quilograma', simbolo='kg'))
        db.session.add(UnidadeMedida(nome='grama', simbolo='g'))
        db.session.add(UnidadeMedida(nome='litro', simbolo='L'))
        db.session.add(UnidadeMedida(nome='pacote', simbolo='pct'))
        db.session.add(UnidadeMedida(nome='caixa', simbolo='cx'))

        db.session.commit()
        print("✅ SUCESSO! Banco Postgres resetado e populado.")

if __name__ == "__main__":
    reset()