import os
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db

# Importamos os Models novos para que o SQLAlchemy saiba que eles existem
from app.models.core import User
from app.models.shopping import Categoria, UnidadeMedida
from app.models.tasks import Task, Reminder

# Tenta carregar dotenv localmente (caso rode script solto)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def reset():
    print("🔧 Iniciando Reset do Banco de Dados (v3 Modular)...")
    
    # Validação de Segurança Básica
    if not os.getenv("DATABASE_URL"):
        print("⚠️  AVISO: DATABASE_URL não encontrada, usando configuração do create_app...")

    # Instancia o App usando a Factory (Igual ao run.py)
    app = create_app()

    print(f"📡 Conectando ao ambiente configurado...") 

    # Entra no contexto da aplicação para ter acesso ao 'db'
    with app.app_context():
        # Drop All: Apaga tudo
        db.drop_all()
        print("🗑️  Tabelas antigas removidas.")
        
        # Create All: Cria tudo baseado nos imports dos models acima
        db.create_all()
        print("✨ Novas tabelas criadas.")

        print("👤 Criando usuários padrão...")
        
        # Carrega credenciais do .env
        user1 = os.getenv('ADMIN_USER_1')
        pass1 = os.getenv('ADMIN_PASS_1')
        user2 = os.getenv('ADMIN_USER_2')
        pass2 = os.getenv('ADMIN_PASS_2')

        # Se não tiver no .env, cria usuários de fallback (DEV apenas) ou lança erro
        if not all([user1, pass1, user2, pass2]):
            print("❌ ERRO: Variáveis ADMIN_USER/PASS não definidas no .env")
            print("ℹ️  Dica: Adicione ADMIN_USER_1=thiago e ADMIN_PASS_1=1234 no .env")
            return

        # Criação dos Usuários
        u1 = User(username=user1, password_hash=generate_password_hash(pass1))
        u2 = User(username=user2, password_hash=generate_password_hash(pass2))
        
        db.session.add(u1)
        db.session.add(u2)

        # 4. Cria Categorias
        print("📂 Criando categorias...")
        cats = ['HORTIFRÚTI', 'PADARIA', 'CARNES', 'LIMPEZA', 'BEBIDAS', 'OUTROS', 'LATICÍNIOS', 'HIGIENE PESSOAL', 'VEGETAIS', 'AUTOMÓVEL']
        for c in cats: 
            # Verifica se já existe para não duplicar (redundância segura)
            if not Categoria.query.filter_by(nome=c).first():
                db.session.add(Categoria(nome=c))

        # 5. Cria Unidades
        print("📏 Criando unidades...")
        unidades = [
            ('unidade', 'un'), ('quilograma', 'kg'), ('grama', 'g'),
            ('litro', 'L'), ('pacote', 'pct'), ('caixa', 'cx'), ('vez', 'vez')
        ]
        for nome, simbolo in unidades:
             if not UnidadeMedida.query.filter_by(nome=nome).first():
                db.session.add(UnidadeMedida(nome=nome, simbolo=simbolo))

        db.session.commit()
        print("✅ SUCESSO! Banco resetado e populado.")

if __name__ == "__main__":
    # Confirmação de segurança para não rodar sem querer
    confirm = input("⚠️  ATENÇÃO: Isso vai APAGAR TODOS OS DADOS do banco. Digite 'reset' para confirmar: ")
    if confirm == "reset":
        reset()
    else:
        print("Operação cancelada.")
