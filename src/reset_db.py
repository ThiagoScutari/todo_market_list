import os
from werkzeug.security import generate_password_hash
from app import app, db, User, Categoria, UnidadeMedida, Task, Reminder

# Tenta carregar dotenv localmente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def reset():
    print("🔧 Iniciando Reset do Banco de Dados...")
    
    # Validação de Segurança: Se não tiver URL, para tudo.
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("❌ ERRO CRÍTICO: 'DATABASE_URL' não encontrada no ambiente.")

    print(f"📡 Conectando ao Banco de Dados...") 

    with app.app_context():
        db.drop_all()
        print("🗑️  Tabelas antigas removidas.")
        
        db.create_all()
        print("✨ Novas tabelas criadas.")

        print("👤 Criando usuários padrão...")
        
        # --- CORREÇÃO DE SEGURANÇA AQUI ---
        # Não usamos fallback. Se não estiver no .env, o script DEVE falhar.
        user1 = os.getenv('ADMIN_USER_1')
        pass1 = os.getenv('ADMIN_PASS_1')
        
        user2 = os.getenv('ADMIN_USER_2')
        pass2 = os.getenv('ADMIN_PASS_2')

        if not all([user1, pass1, user2, pass2]):
            raise ValueError("❌ ERRO DE SEGURANÇA: As variáveis ADMIN_USER/PASS não foram definidas no .env!")

        # Gera o Hash (Criptografia)
        db.session.add(User(username=user1, password_hash=generate_password_hash(pass1)))
        db.session.add(User(username=user2, password_hash=generate_password_hash(pass2)))

        # 4. Cria Categorias
        print("📂 Criando categorias...")
        cats = ['HORTIFRÚTI', 'PADARIA', 'CARNES', 'LIMPEZA', 'BEBIDAS', 'OUTROS', 'LATICÍNIOS', 'HIGIENE PESSOAL', 'VEGETAIS', 'AUTOMÓVEL']
        for c in cats: 
            db.session.add(Categoria(nome=c))

        # 5. Cria Unidades
        print("📏 Criando unidades...")
        unidades = [
            ('unidade', 'un'), ('quilograma', 'kg'), ('grama', 'g'),
            ('litro', 'L'), ('pacote', 'pct'), ('caixa', 'cx'), ('vez', 'vez')
        ]
        for nome, simbolo in unidades:
            db.session.add(UnidadeMedida(nome=nome, simbolo=simbolo))

        db.session.commit()
        print("✅ SUCESSO! Banco populado com senhas criptografadas.")

if __name__ == "__main__":
    reset()