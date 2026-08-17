from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PRINTER_COLUMNS = {
    "serial": "VARCHAR(180)",
    "toner_percent": "INTEGER",
    "health_score": "INTEGER",
    "health_status": "VARCHAR(30)",
}


def ensure_printer_columns(engine: Engine) -> None:
    """
    Garante que a tabela printers possua as colunas
    adicionadas pelo PRINTFLOW Motor V2.

    A rotina é idempotente:
    - não apaga dados;
    - não recria a tabela;
    - adiciona somente colunas ausentes.
    """

    inspector = inspect(engine)

    if "printers" not in inspector.get_table_names():
        print(
            "[PRINTFLOW DB] Tabela printers ainda não existe. "
            "Nenhuma migração necessária."
        )
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("printers")
    }

    missing_columns = {
        name: sql_type
        for name, sql_type in PRINTER_COLUMNS.items()
        if name not in existing_columns
    }

    if not missing_columns:
        print(
            "[PRINTFLOW DB] Motor V2: banco já atualizado."
        )
        return

    with engine.begin() as connection:
        for column_name, column_type in missing_columns.items():
            print(
                f"[PRINTFLOW DB] Criando coluna: "
                f"{column_name} ({column_type})"
            )

            connection.execute(
                text(
                    f"ALTER TABLE printers "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )

    print(
        "[PRINTFLOW DB] Migração Motor V2 concluída."
    )
