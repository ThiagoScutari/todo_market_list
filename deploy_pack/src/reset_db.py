from app import app, db, Categoria, UnidadeMedida, TipoLista

def resetar_banco():
    with app.app_context():
        # 1. Apaga tudo e recria as tabelas baseadas no app.py
        print("🗑️  Apagando banco antigo...")
        db.drop_all()
        print("🔨 Criando novas tabelas...")
        db.create_all()

        # 2. Insere Dados Iniciais (Seed)
        print("🌱 Semeando dados...")
        
        # Categorias
        categorias = ['Hortifrúti', 'Padaria', 'Carnes', 'Limpeza', 'Bebidas', 'Mercearia', 'Outros']
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
        print("✅ Banco de dados recriado e populado com sucesso!")

if __name__ == "__main__":
    resetar_banco()