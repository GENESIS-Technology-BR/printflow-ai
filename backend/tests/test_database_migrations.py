from sqlalchemy import create_engine, inspect

from backend.app.database.connection import Base
from backend.app.database.migrations import (
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
