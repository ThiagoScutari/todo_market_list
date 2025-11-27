import sqlite3
import shutil
import datetime

SRC = r"D:\langchain\memoria_v10_rag.db"
DST = r"D:\langchain\projects\todo_market_list\src\memoria_v10_rag.db"


def backup_database(dst_path):
    """Cria um backup seguro antes da migração."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{dst_path}.backup_{timestamp}.db"
    shutil.copy2(dst_path, backup_path)
    print(f"📀 Backup criado em: {backup_path}")
    return backup_path


def migrate():
    print("🚀 INICIANDO MERGE ENTRE OS BANCOS...\n")

    # Criar backup antes de qualquer operação
    backup_database(DST)

    conn_src = sqlite3.connect(SRC)
    conn_dst = sqlite3.connect(DST)

    # ----------------------------------------------------------------------
    # Copiar checkpoints
    # ----------------------------------------------------------------------
    print("📌 Copiando registros da tabela 'checkpoints'...")

    src_rows = conn_src.execute("SELECT * FROM checkpoints").fetchall()
    dst_rows = conn_dst.execute("SELECT * FROM checkpoints").fetchall()

    new_rows = [row for row in src_rows if row not in dst_rows]

    print(f" → Encontrados {len(new_rows)} novos registros.")

    if new_rows:
        conn_dst.executemany(
            "INSERT INTO checkpoints VALUES (?, ?, ?, ?, ?, ?, ?)", new_rows
        )
        conn_dst.commit()
        print(" ✔ Registros de 'checkpoints' inseridos com sucesso!\n")
    else:
        print(" ✔ Nenhum registro novo para inserir.\n")

    # ----------------------------------------------------------------------
    # Copiar writes
    # ----------------------------------------------------------------------
    print("📌 Copiando registros da tabela 'writes'...")

    src_rows = conn_src.execute("SELECT * FROM writes").fetchall()
    dst_rows = conn_dst.execute("SELECT * FROM writes").fetchall()

    new_rows = [row for row in src_rows if row not in dst_rows]

    print(f" → Encontrados {len(new_rows)} novos registros.")

    if new_rows:
        conn_dst.executemany(
            "INSERT INTO writes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", new_rows
        )
        conn_dst.commit()
        print(" ✔ Registros de 'writes' inseridos com sucesso!\n")
    else:
        print(" ✔ Nenhum registro novo para inserir.\n")

    # Finalização
    conn_src.close()
    conn_dst.close()

    print("🎉 MERGE FINALIZADO COM SUCESSO!")
    print("Tudo pronto! Você agora tem os 9 + 9 registros no banco do projeto.")


if __name__ == "__main__":
    migrate()
