from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PRINTER_COLUMNS = {
    "hostname": "VARCHAR(255)",
    "custom_name": "VARCHAR(150)",
    "serial": "VARCHAR(180)",
    "toner_percent": "INTEGER",
    "health_score": "INTEGER",
    "health_status": "VARCHAR(30)",
    "serial_source": "VARCHAR(60)",
    "serial_confidence": "INTEGER",
    "serial_confirmed": "BOOLEAN DEFAULT FALSE",
    "page_count_source": "VARCHAR(60)",
    "page_count_confidence": "INTEGER",
    "page_count_confirmed": "BOOLEAN DEFAULT FALSE",
}

COMPANY_AGENT_COLUMNS = {
    "agent_last_seen": "TIMESTAMP",
    "agent_status": "VARCHAR(30)",
    "agent_name": "VARCHAR(120)",
    "agent_version": "VARCHAR(30)",
    "agent_last_error": "VARCHAR(500)",
}

OPERATIONAL_ALERT_COLUMNS = {
    "acknowledged_at": "TIMESTAMP",
    "acknowledged_by": "INTEGER",
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


def ensure_printer_company_ip_constraint(engine: Engine) -> None:
    """Troca a unicidade global de IP pela unicidade por empresa.

    Em bancos PostgreSQL existentes, remove somente constraints únicas
    formadas exclusivamente por ``ip`` e cria ``(company_id, ip)``.
    Bancos novos já recebem a constraint correta pelo modelo SQLAlchemy.
    """
    inspector = inspect(engine)

    if "printers" not in inspector.get_table_names():
        return

    unique_constraints = inspector.get_unique_constraints("printers")
    composite_exists = any(
        set(item.get("column_names") or []) == {"company_id", "ip"}
        for item in unique_constraints
    )

    if composite_exists:
        return

    if engine.dialect.name != "postgresql":
        print(
            "[PRINTFLOW DB] Constraint por empresa será aplicada "
            "automaticamente em bancos novos."
        )
        return

    global_ip_constraints = [
        item.get("name")
        for item in unique_constraints
        if item.get("column_names") == ["ip"] and item.get("name")
    ]
    quote = engine.dialect.identifier_preparer.quote

    with engine.begin() as connection:
        for constraint_name in global_ip_constraints:
            connection.execute(
                text(
                    "ALTER TABLE printers DROP CONSTRAINT "
                    f"{quote(constraint_name)}"
                )
            )

        connection.execute(
            text(
                "ALTER TABLE printers ADD CONSTRAINT "
                "uq_printers_company_ip UNIQUE (company_id, ip)"
            )
        )

    print(
        "[PRINTFLOW DB] Unicidade de impressora atualizada "
        "para empresa + IP."
    )


def ensure_company_agent_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "companies_v2" not in inspector.get_table_names():
        return
    existing = {
        column["name"]
        for column in inspector.get_columns("companies_v2")
    }
    missing = {
        name: sql_type
        for name, sql_type in COMPANY_AGENT_COLUMNS.items()
        if name not in existing
    }
    with engine.begin() as connection:
        for name, sql_type in missing.items():
            connection.execute(text(
                f"ALTER TABLE companies_v2 ADD COLUMN {name} {sql_type}"
            ))


def ensure_operational_alert_columns(engine: Engine) -> None:
    """Adiciona metadados de reconhecimento sem recriar alertas existentes."""
    inspector = inspect(engine)
    if "operational_alerts" not in inspector.get_table_names():
        return
    existing = {
        column["name"]
        for column in inspector.get_columns("operational_alerts")
    }
    missing = {
        name: sql_type
        for name, sql_type in OPERATIONAL_ALERT_COLUMNS.items()
        if name not in existing
    }
    with engine.begin() as connection:
        for name, sql_type in missing.items():
            connection.execute(text(
                f"ALTER TABLE operational_alerts ADD COLUMN {name} {sql_type}"
            ))


def clean_descriptive_printer_serials(engine: Engine) -> None:
    """Remove descrições de modelo historicamente gravadas como serial."""
    inspector = inspect(engine)
    if "printers" not in inspector.get_table_names():
        return

    columns = {
        column["name"] for column in inspector.get_columns("printers")
    }
    required = {
        "serial",
        "serial_source",
        "serial_confidence",
        "serial_confirmed",
    }
    if not required.issubset(columns):
        return

    with engine.begin() as connection:
        result = connection.execute(text("""
            UPDATE printers
               SET serial = NULL,
                   serial_source = NULL,
                   serial_confidence = NULL,
                   serial_confirmed = FALSE
             WHERE serial IS NOT NULL
               AND (
                    LOWER(serial) LIKE '% zpl%'
                 OR LOWER(serial) LIKE '% technologies%'
                 OR LOWER(serial) LIKE '%203dpi%'
                 OR LOWER(serial) LIKE '%300dpi%'
                 OR LOWER(serial) LIKE '%600dpi%'
               )
        """))

    if result.rowcount:
        print(
            "[PRINTFLOW DB] Seriais descritivos removidos: "
            f"{result.rowcount}."
        )
