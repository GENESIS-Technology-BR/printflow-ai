from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer
from backend.modules.usage.model import PrinterUsageDaily
from backend.modules.usage.router import (
    _current_printers,
    _report_rows,
    _usage_query,
    _validate_report_filters,
)


@pytest.fixture()
def tenant_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        company_a = Company(name="Empresa A", active=True)
        company_b = Company(name="Empresa B", active=True)
        db.add_all([company_a, company_b])
        db.flush()

        user_a = User(
            company_id=company_a.id,
            name="Admin A",
            email="admin-a@printflow.local",
            password_hash="test",
            role="admin",
            active=True,
        )
        user_b = User(
            company_id=company_b.id,
            name="Admin B",
            email="admin-b@printflow.local",
            password_hash="test",
            role="admin",
            active=True,
        )
        printer_a = Printer(
            company_id=company_a.id,
            uuid="printer-a",
            ip="10.0.0.10",
            name="HP A",
            unit_name="Matriz",
            sector_name="Financeiro",
            active=True,
        )
        printer_b = Printer(
            company_id=company_b.id,
            uuid="printer-b",
            ip="10.0.0.10",
            name="Ricoh B",
            unit_name="Filial",
            sector_name="RH",
            active=True,
        )
        db.add_all([user_a, user_b, printer_a, printer_b])
        db.flush()

        for company, printer, name in (
            (company_a, printer_a, "HP A"),
            (company_b, printer_b, "Ricoh B"),
        ):
            db.add(
                PrinterUsageDaily(
                    company_id=company.id,
                    printer_id=printer.id,
                    usage_date=date(2026, 9, 9),
                    printer_uuid=printer.uuid,
                    ip=printer.ip,
                    name=name,
                    opening_page_count=100,
                    closing_page_count=125,
                    pages_printed=25,
                    anomaly_count=0,
                    first_seen_at=printer.created_at,
                    last_seen_at=printer.created_at,
                )
            )
        db.commit()
        yield db, company_a, company_b, user_a, user_b
    finally:
        db.close()


def test_usage_query_never_crosses_company_boundary(tenant_db) -> None:
    db, company_a, _, _, _ = tenant_db
    rows = _usage_query(
        db, company_a.id, date(2026, 9, 1), date(2026, 9, 30)
    ).all()

    assert len(rows) == 1
    assert rows[0].company_id == company_a.id
    assert rows[0].printer_uuid == "printer-a"


def test_current_printers_never_crosses_company_boundary(tenant_db) -> None:
    db, company_a, _, _, _ = tenant_db
    rows = _current_printers(db, company_a.id)

    assert [row.uuid for row in rows] == ["printer-a"]


def test_report_rows_are_isolated_by_authenticated_company(tenant_db) -> None:
    db, company_a, company_b, user_a, user_b = tenant_db

    rows_a = _report_rows(
        db, user_a, date(2026, 9, 1), date(2026, 9, 30)
    )
    rows_b = _report_rows(
        db, user_b, date(2026, 9, 1), date(2026, 9, 30)
    )

    assert {row["printer_uuid"] for row in rows_a} == {"printer-a"}
    assert {row["printer_uuid"] for row in rows_b} == {"printer-b"}
    assert company_a.id != company_b.id


def test_foreign_printer_filter_fails_closed(tenant_db) -> None:
    db, company_a, _, _, _ = tenant_db

    with pytest.raises(HTTPException) as exc:
        _validate_report_filters(
            db,
            company_a.id,
            printer_uuid="printer-b",
        )

    assert exc.value.status_code == 404


def test_foreign_unit_and_sector_filters_fail_closed(tenant_db) -> None:
    db, company_a, _, _, _ = tenant_db

    with pytest.raises(HTTPException):
        _validate_report_filters(db, company_a.id, unit_name="Filial")

    with pytest.raises(HTTPException):
        _validate_report_filters(db, company_a.id, sector_name="RH")
