from sqlalchemy import create_engine, inspect, text

from backend.app.database.connection import Base
from backend.app.database.migrations import (
    clean_descriptive_printer_serials,
    ensure_company_agent_columns,
    ensure_printer_company_ip_constraint,
)
from backend.modules.auth.model import User  # noqa: F401
from backend.modules.companies.model import Company  # noqa: F401
from backend.modules.printers.model import Printer  # noqa: F401


def test_new_database_uses_company_ip_constraint(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    Base.metadata.create_all(engine)

    ensure_printer_company_ip_constraint(engine)
    ensure_company_agent_columns(engine)

    constraints = inspect(engine).get_unique_constraints("printers")
    assert any(
        set(item["column_names"]) == {"company_id", "ip"}
        for item in constraints
    )

    columns = {
        item["name"] for item in inspect(engine).get_columns("printers")
    }
    assert {
        "serial_source",
        "serial_confidence",
        "serial_confirmed",
        "page_count_source",
        "page_count_confidence",
        "page_count_confirmed",
    }.issubset(columns)

    company_columns = {
        item["name"]
        for item in inspect(engine).get_columns("companies_v2")
    }
    assert {
        "agent_last_seen",
        "agent_status",
        "agent_name",
        "agent_version",
        "agent_last_error",
    }.issubset(company_columns)


def test_cleanup_removes_only_descriptive_serials(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cleanup.db'}")
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO companies_v2 "
            "(id, uuid, name, plan, agent_token, active, created_at) "
            "VALUES (1, 'company-1', 'PRINTFLOW', 'pilot', "
            "'0123456789012345678901234567890123456789', 1, CURRENT_TIMESTAMP)"
        ))
        connection.execute(text("""
            INSERT INTO printers
                (uuid, company_id, ip, name, status, source,
                 page_count_confirmed, serial, serial_source,
                 serial_confidence, serial_confirmed, active,
                 last_seen, created_at)
            VALUES
                ('printer-1', 1, '10.0.0.10', 'Zebra', 'online', 'agent', 0,
                 'ZTC ZT230-203dpi ZPL',
                 'printer-mib', 95, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                ('printer-2', 1, '10.0.0.11', 'Canon', 'online', 'agent', 0,
                 'KNDK09992',
                 'snmp-primary', 95, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """))

    clean_descriptive_printer_serials(engine)
    clean_descriptive_printer_serials(engine)

    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT ip, serial, serial_source, serial_confidence, "
            "serial_confirmed FROM printers ORDER BY ip"
        )).mappings().all()

    assert rows[0]["serial"] is None
    assert rows[0]["serial_source"] is None
    assert rows[0]["serial_confidence"] is None
    assert not rows[0]["serial_confirmed"]
    assert rows[1]["serial"] == "KNDK09992"
