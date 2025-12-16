from app import create_app
from app.extensions import db

app = create_app()

if __name__ == "__main__":
    # Garante que as tabelas existam antes de rodar
    # (Isso substitui o db.create_all() que ficava no final do seu arquivo antigo)
    with app.app_context():
        db.create_all()
        print("✅ Banco de dados verificado/inicializado.")

    print("🚀 FamilyOS v3.0 (Modular) iniciando...")
    app.run(host="0.0.0.0", port=5000, debug=True)