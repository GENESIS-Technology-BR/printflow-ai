from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.connection import Base
from backend.modules.alerts.model import OperationalAlert
from backend.modules.alerts.service import acknowledge_alert, reconcile_company_alerts
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.organization.model import CompanySector, CompanyUnit
from backend.modules.dashboard.router import serialize_printer
from backend.modules.printers.model import Printer


def _database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'alerts.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _company(company_id: int, token: str) -> Company:
    return Company(
        id=company_id,
        uuid=f"company-{company_id}",
        name=f"Empresa {company_id}",
        agent_token=token,
    )


def test_alert_is_opened_once_and_resolved_when_condition_clears(tmp_path):
    db = _database(tmp_path)
    db.add(_company(1, "a" * 43))
    printer = Printer(
        company_id=1,
        uuid="printer-1",
        ip="10.0.0.10",
        name="Canon Financeiro",
        status="online",
        toner_percent=5,
    )
    db.add(printer)
    db.commit()

    first = reconcile_company_alerts(db, 1, serialize_printer)
    second = reconcile_company_alerts(db, 1, serialize_printer)
    open_toner = [item for item in second if item.category == "toner"]

    assert len(open_toner) == 1
    assert open_toner[0].severity == "critical"
    assert open_toner[0].status == "open"
    assert len(first) == len(second)

    printer.toner_percent = 80
    db.commit()
    resolved = reconcile_company_alerts(db, 1, serialize_printer)
    toner = next(item for item in resolved if item.category == "toner")
    assert toner.status == "resolved"
    assert toner.resolved_at is not None


def test_alert_reconciliation_is_isolated_by_company(tmp_path):
    db = _database(tmp_path)
    db.add_all([_company(1, "a" * 43), _company(2, "b" * 43)])
    db.add_all([
        Printer(
            company_id=1,
            uuid="printer-a",
            ip="10.0.0.10",
            name="Printer A",
            status="offline",
        ),
        Printer(
            company_id=2,
            uuid="printer-b",
            ip="10.0.0.10",
            name="Printer B",
            status="offline",
        ),
    ])
    db.commit()

    alerts = reconcile_company_alerts(db, 1, serialize_printer)

    assert alerts
    assert {item.company_id for item in alerts} == {1}
    assert db.query(OperationalAlert).filter(
        OperationalAlert.company_id == 2
    ).count() == 0


def test_low_toner_warning_becomes_critical_without_duplicate(tmp_path):
    db = _database(tmp_path)
    db.add(_company(1, "a" * 43))
    printer = Printer(
        company_id=1,
        uuid="printer-1",
        ip="10.0.0.11",
        name="Canon",
        status="online",
        toner_percent=12,
    )
    db.add(printer)
    db.commit()

    reconcile_company_alerts(db, 1, serialize_printer)
    printer.toner_percent = 3
    db.commit()
    alerts = reconcile_company_alerts(db, 1, serialize_printer)

    toner = [item for item in alerts if item.category == "toner"]
    assert len(toner) == 1
    assert toner[0].severity == "critical"


def test_acknowledged_alert_stays_active_and_resolves_with_condition(tmp_path):
    db = _database(tmp_path)
    company = _company(1, "a" * 43)
    user = User(company_id=1, name="Operador", email="ops@example.com", password_hash="x")
    printer = Printer(
        company_id=1,
        uuid="printer-ack",
        ip="10.0.0.12",
        name="Canon Operacional",
        status="online",
        toner_percent=4,
    )
    db.add_all([company, user, printer])
    db.commit()

    alert = next(
        item for item in reconcile_company_alerts(db, 1, serialize_printer)
        if item.category == "toner"
    )
    acknowledged = acknowledge_alert(db, 1, alert.id, user.id)

    assert acknowledged is not None
    assert acknowledged.status == "acknowledged"
    assert acknowledged.acknowledged_at is not None
    assert acknowledged.acknowledged_by == user.id

    reconciled = reconcile_company_alerts(db, 1, serialize_printer)
    active = next(item for item in reconciled if item.id == alert.id)
    assert active.status == "acknowledged"

    printer.toner_percent = 80
    db.commit()
    resolved = reconcile_company_alerts(db, 1, serialize_printer)
    closed = next(item for item in resolved if item.id == alert.id)
    assert closed.status == "resolved"
    assert closed.resolved_at is not None


def test_acknowledge_is_idempotent_and_isolated_by_company(tmp_path):
    db = _database(tmp_path)
    db.add_all([_company(1, "a" * 43), _company(2, "b" * 43)])
    user = User(company_id=1, name="Operador A", email="ops-a@example.com", password_hash="x")
    user_b = User(company_id=2, name="Operador B", email="ops-b@example.com", password_hash="x")
    printer = Printer(
        company_id=2,
        uuid="printer-company-2",
        ip="10.0.0.22",
        name="Printer B",
        status="offline",
    )
    db.add_all([user, user_b, printer])
    db.commit()
    alert = reconcile_company_alerts(db, 2, serialize_printer)[0]

    assert acknowledge_alert(db, 1, alert.id, user.id) is None
    assert acknowledge_alert(db, 2, alert.id, user.id) is None
    first = acknowledge_alert(db, 2, alert.id, user_b.id)
    acknowledged_at = first.acknowledged_at
    second = acknowledge_alert(db, 2, alert.id, user_b.id)

    assert second.id == first.id
    assert second.acknowledged_at == acknowledged_at


def test_inactive_printer_does_not_generate_operational_alert(tmp_path):
    db = _database(tmp_path)
    db.add(_company(1, "a" * 43))

    printer = Printer(
        company_id=1,
        uuid="printer-inactive",
        ip="10.0.0.99",
        name="Printer desativada",
        status="offline",
        active=False,
        toner_percent=2,
    )

    db.add(printer)
    db.commit()

    alerts = reconcile_company_alerts(
        db,
        1,
        serialize_printer,
    )

    active_alerts = [
        item
        for item in alerts
        if item.status in ("open", "acknowledged")
    ]

    assert active_alerts == []
