from app import app, db, User, Categoria, UnidadeMedida, TipoLista

def resetar_banco():
    print(f"🔧 Configuração de Banco: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    with app.app_context():
        # Apaga e recria
        db.drop_all()
        db.create_all()
        
        # Cria Usuários
        user_thiago = User(username='thiago', password_hash='2904')
        user_debora = User(username='debora', password_hash='1712')
        db.session.add(user_thiago)
        db.session.add(user_debora)
        
        # Cria Categorias Básicas
        cats = ['Hortifrúti', 'Padaria', 'Carnes', 'Limpeza', 'Bebidas', 'Outros']
        for c in cats:
            db.session.add(Categoria(nome=c.upper())) # Força upper conforme sua regra
            
        # Cria Unidades
        unidades = [
            {'nome': 'unidade', 'simbolo': 'un'},
            {'nome': 'quilograma', 'simbolo': 'kg'},
            {'nome': 'grama', 'simbolo': 'g'},
            {'nome': 'litro', 'simbolo': 'L'},
            {'nome': 'pacote', 'simbolo': 'pct'}
        ]
        for u in unidades:
            db.session.add(UnidadeMedida(nome=u['nome'], simbolo=u['simbolo']))

        db.session.commit()
        print("✅ Banco resetado e populado com sucesso!")

if __name__ == "__main__":
    resetar_banco()