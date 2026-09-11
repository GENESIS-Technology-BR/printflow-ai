from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PRINTER_COLUMNS = {
    "hostname": "VARCHAR(255)", "custom_name": "VARCHAR(150)", "unit_name": "VARCHAR(120)",
    "sector_name": "VARCHAR(120)", "unit_id": "INTEGER", "sector_id": "INTEGER",
    "serial": "VARCHAR(180)", "toner_percent": "INTEGER", "health_score": "INTEGER",
    "health_status": "VARCHAR(30)", "serial_source": "VARCHAR(60)", "serial_confidence": "INTEGER",
    "serial_confirmed": "BOOLEAN DEFAULT FALSE", "page_count_source": "VARCHAR(60)",
    "page_count_confidence": "INTEGER", "page_count_confirmed": "BOOLEAN DEFAULT FALSE",
    "cost_per_page": "NUMERIC(10,4)", "cost_model": "VARCHAR(30) DEFAULT 'per_page' NOT NULL",
    "fixed_monthly_cost": "NUMERIC(12,2)",
}

COMPANY_AGENT_COLUMNS = {
    "agent_last_seen": "TIMESTAMP", "agent_status": "VARCHAR(30)", "agent_name": "VARCHAR(120)",
    "agent_version": "VARCHAR(30)", "agent_last_error": "VARCHAR(500)",
    "default_cost_per_page": "NUMERIC(10,4) DEFAULT 0 NOT NULL",
}
OPERATIONAL_ALERT_COLUMNS = {"acknowledged_at": "TIMESTAMP", "acknowledged_by": "INTEGER"}
USER_SECURITY_COLUMNS = {"session_version": "INTEGER DEFAULT 0 NOT NULL", "password_reset_version": "INTEGER DEFAULT 0 NOT NULL"}


def _ensure_columns(engine: Engine, table: str, definitions: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns(table)}
    with engine.begin() as connection:
        for name, sql_type in definitions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


def ensure_printer_columns(engine: Engine) -> None:
    _ensure_columns(engine, "printers", PRINTER_COLUMNS)


def ensure_company_agent_columns(engine: Engine) -> None:
    _ensure_columns(engine, "companies_v2", COMPANY_AGENT_COLUMNS)


def ensure_operational_alert_columns(engine: Engine) -> None:
    _ensure_columns(engine, "operational_alerts", OPERATIONAL_ALERT_COLUMNS)


def ensure_user_security_columns(engine: Engine) -> None:
    _ensure_columns(engine, "users_v2", USER_SECURITY_COLUMNS)


def ensure_printer_company_ip_constraint(engine: Engine) -> None:
    inspector = inspect(engine)
    if "printers" not in inspector.get_table_names():
        return
    unique_constraints = inspector.get_unique_constraints("printers")
    if any(set(item.get("column_names") or []) == {"company_id", "ip"} for item in unique_constraints):
        return
    if engine.dialect.name != "postgresql":
        return
    global_ip_constraints = [item.get("name") for item in unique_constraints if item.get("column_names") == ["ip"] and item.get("name")]
    quote = engine.dialect.identifier_preparer.quote
    with engine.begin() as connection:
        for constraint_name in global_ip_constraints:
            connection.execute(text("ALTER TABLE printers DROP CONSTRAINT " + quote(constraint_name)))
        connection.execute(text("ALTER TABLE printers ADD CONSTRAINT uq_printers_company_ip UNIQUE (company_id, ip)"))


def clean_descriptive_printer_serials(engine: Engine) -> None:
    inspector = inspect(engine)
    if "printers" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("printers")}
    required = {"serial", "serial_source", "serial_confidence", "serial_confirmed"}
    if not required.issubset(columns):
        return
    with engine.begin() as connection:
        connection.execute(text("""
            UPDATE printers SET serial = NULL, serial_source = NULL,
                serial_confidence = NULL, serial_confirmed = FALSE
            WHERE serial IS NOT NULL AND (
                LOWER(serial) LIKE '% zpl%' OR LOWER(serial) LIKE '% technologies%'
                OR LOWER(serial) LIKE '%203dpi%' OR LOWER(serial) LIKE '%300dpi%'
                OR LOWER(serial) LIKE '%600dpi%')
        """))
