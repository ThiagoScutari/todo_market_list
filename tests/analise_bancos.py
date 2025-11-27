import sqlite3
from pprint import pprint

# Caminhos dos bancos
SRC = r"D:\langchain\memoria_v10_rag.db"
DST = r"D:\langchain\projects\todo_market_list\src\memoria_v10_rag.db"

def connect(path):
    return sqlite3.connect(path)

def count_records(conn, table):
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]

def check_integrity(conn):
    cur = conn.execute("PRAGMA integrity_check;")
    return cur.fetchone()[0]

def get_schema(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table});")
    return cur.fetchall()

def get_all_rows(conn, table):
    cur = conn.execute(f"SELECT * FROM {table}")
    return cur.fetchall()

def diff_lists(src_list, dst_list):
    """Retorna registros que estão no SRC e não estão no DST."""
    return [row for row in src_list if row not in dst_list]

def main():
    print("="*80)
    print("🔍 ANALISANDO BANCOS SQLITE")
    print("="*80)

    conn_src = connect(SRC)
    conn_dst = connect(DST)

    # ----------------------------------------------------------------------
    # 1. Contagem de registros
    # ----------------------------------------------------------------------
    print("\n📌 CONTAGEM DE REGISTROS\n")

    src_checkpoints = count_records(conn_src, "checkpoints")
    src_writes = count_records(conn_src, "writes")
    dst_checkpoints = count_records(conn_dst, "checkpoints")
    dst_writes = count_records(conn_dst, "writes")

    print(f"SRC checkpoints: {src_checkpoints}")
    print(f"SRC writes: {src_writes}")
    print(f"DST checkpoints: {dst_checkpoints}")
    print(f"DST writes: {dst_writes}")

    # ----------------------------------------------------------------------
    # 2. Verificação de integridade
    # ----------------------------------------------------------------------
    print("\n📌 VERIFICAÇÃO DE INTEGRIDADE\n")

    print(f"SRC integrity_check → {check_integrity(conn_src)}")
    print(f"DST integrity_check → {check_integrity(conn_dst)}")

    # ----------------------------------------------------------------------
    # 3. Schema das tabelas
    # ----------------------------------------------------------------------
    print("\n📌 SCHEMA DAS TABELAS (SRC)\n")
    print("checkpoints:")
    pprint(get_schema(conn_src, "checkpoints"))
    print("\nwrites:")
    pprint(get_schema(conn_src, "writes"))

    print("\n📌 SCHEMA DAS TABELAS (DST)\n")
    print("checkpoints:")
    pprint(get_schema(conn_dst, "checkpoints"))
    print("\nwrites:")
    pprint(get_schema(conn_dst, "writes"))

    # ----------------------------------------------------------------------
    # 4. DIFF ENTRE OS BANCOS
    # ----------------------------------------------------------------------
    print("\n📌 COMPARAÇÃO DE REGISTROS (DIFF)\n")

    src_cp = get_all_rows(conn_src, "checkpoints")
    dst_cp = get_all_rows(conn_dst, "checkpoints")

    src_wr = get_all_rows(conn_src, "writes")
    dst_wr = get_all_rows(conn_dst, "writes")

    diff_cp = diff_lists(src_cp, dst_cp)
    diff_wr = diff_lists(src_wr, dst_wr)

    print(f"Registros de checkpoints que existem no SRC e NÃO existem no DST: {len(diff_cp)}")
    print(f"Registros de writes que existem no SRC e NÃO existem no DST: {len(diff_wr)}")

    # Mostrar alguns exemplos (até 5)
    print("\nExemplos de diffs (até 5 por tabela):")
    print("\ncheckpoints diff sample:")
    pprint(diff_cp[:5])

    print("\nwrites diff sample:")
    pprint(diff_wr[:5])

    # ----------------------------------------------------------------------
    # 5. Dry-run da fusão (simulação)
    # ----------------------------------------------------------------------
    print("\n📌 DRY-RUN DO MERGE (simulação, nada é gravado)\n")

    print(f"→ Se fizéssemos o merge agora, seriam inseridos:")
    print(f"  - {len(diff_cp)} registros em checkpoints")
    print(f"  - {len(diff_wr)} registros em writes")

    print("\nNenhum dado foi modificado. Este é um DRY-RUN seguro.")
    print("="*80)

    conn_src.close()
    conn_dst.close()


if __name__ == "__main__":
    main()
