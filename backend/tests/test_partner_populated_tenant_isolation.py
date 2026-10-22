"""Regression: populated partner portfolios must never leak another tenant's data."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.connection import Base
from backend.app.database import models as registered_models  # noqa: F401
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.partners.model import Partner, PartnerMembership
from backend.modules.printers.model import Printer
from backend.modules.partners.router import (
    partner_company_printers,
    partner_company_overview,
    partner_portfolio_summary,
    my_partner_companies,
)


def test_populated_printer_fleets_are_isolated_across_partners():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            partner_a = Partner(name="Parceiro A")
            partner_b = Partner(name="Parceiro B")
            db.add_all([partner_a, partner_b])
            db.flush()
            company_a = Company(name="Cliente A", partner_id=partner_a.id)
            company_b = Company(name="Cliente B", partner_id=partner_b.id)
            db.add_all([company_a, company_b])
            db.flush()
            user = User(
                company_id=company_a.id, name="Operador A",
                email="partner-isolation@example.test", password_hash="test",
                role="client",
            )
            db.add(user)
            db.flush()
            db.add(PartnerMembership(
                partner_id=partner_a.id, user_id=user.id, role="partner_viewer",
            ))
            db.add_all([
                Printer(company_id=company_a.id, ip="192.0.2.10", name="Printer A", status="online"),
                Printer(company_id=company_b.id, ip="192.0.2.20", name="Printer B", status="offline"),
            ])
            db.flush()

            companies = my_partner_companies(user=user, db=db)
            assert [row["id"] for row in companies] == [company_a.id]

            printers = partner_company_printers(company_a.id, user=user, db=db)
            assert len(printers) == 1
            assert printers[0]["ip"] == "192.0.2.10"

            overview = partner_company_overview(company_a.id, user=user, db=db)
            assert overview["total_active_printers"] == 1
            assert overview["online_printers"] == 1
            assert overview["offline_printers"] == 0

            portfolio = partner_portfolio_summary(user=user, db=db)
            assert portfolio["companies"] == 1
            assert portfolio["active_printers"] == 1
            assert portfolio["online_printers"] == 1
            assert portfolio["offline_printers"] == 0

            for endpoint in (partner_company_printers, partner_company_overview):
                with pytest.raises(HTTPException) as exc:
                    endpoint(company_b.id, user=user, db=db)
                assert exc.value.status_code == 403
    finally:
        engine.dispose()
