"""Synthetic persistence contract; never starts the application lifespan."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.connection import Base
from backend.app.database import models  # noqa: F401
from backend.modules.companies.model import Company
from backend.modules.printers.router import list_printers, receive_agent_data
from backend.modules.printers.schema import PrinterUpsert
from backend.modules.usage.model import PrinterUsageDaily


def test_27_synthetic_printers_persist_without_duplicates_or_tenant_leakage():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            company = Company(name="Synthetic fleet", agent_token="A" * 43)
            other = Company(name="Other synthetic tenant", agent_token="B" * 43)
            db.add_all([company, other])
            db.commit()
            for counter in (1000, 1125, 900):
                for index in range(1, 28):
                    receive_agent_data(PrinterUpsert(
                        agent_token="A" * 43,
                        ip=f"192.0.2.{index}",
                        name=f"Synthetic printer {index}",
                        page_count=counter,
                        page_count_confidence=95,
                        page_count_confirmed=True,
                    ), db=db)
            printers = list_printers(db=db, current_user=SimpleNamespace(company_id=company.id))
            assert len(printers) == 27
            assert all(printer.page_count == 1125 for printer in printers)
            assert all(printer.active for printer in printers)
            history = db.query(PrinterUsageDaily).all()
            assert len(history) == 27
            assert all(row.company_id == company.id for row in history)
            assert list_printers(db=db, current_user=SimpleNamespace(company_id=other.id)) == []
            with pytest.raises(HTTPException) as error:
                receive_agent_data(PrinterUpsert(agent_token="C" * 43, ip="192.0.2.1"), db=db)
            assert error.value.status_code == 401
    finally:
        engine.dispose()
