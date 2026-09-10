import hmac
import os
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.alerts.model import OperationalAlert
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer
from backend.modules.dashboard.router import serialize_printer
from backend.modules.control_center.router import (
    _agent_communication,
    _commercial_readiness,
    _onboarding_progress,
    _onboarding_state,
)
from backend.modules.integration.openapi_spec import INTEGRATION_OPENAPI
from backend.modules.usage.router import (
    _current_printers,
    _resolve_period,
    _usage_query,
    _validate_report_filters,
)
from backend.modules.usage.reporting import consolidate_usage

router = APIRouter(prefix="/integration", tags=["Integration"])


def _integration_key() -> str:
    key = os.getenv("PRINTFLOW_INTEGRATION_KEY", "").strip()
    if len(key) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração desabilitada",
        )
    return key


def require_integration_key(
    x_printflow_integration_key: str = Header(
        ...,
        alias="X-Printflow-Integration-Key",
    ),
) -> None:
    expected = _integration_key()
    if not hmac.compare_digest(x_printflow_integration_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial de integração inválida",
        )


def _find_company(db: Session, company_uuid: str) -> Company:
    company = db.query(Company).filter(Company.uuid == company_uuid).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company


def _company_snapshot(db: Session, company: Company) -> dict:
    active_query = db.query(Printer).filter(
        Printer.company_id == company.id,
        Printer.active.is_(True),
    )
    active_printers = active_query.count()
    online_printers = active_query.filter(Printer.status == "online").count()
    offline_printers = active_query.filter(Printer.status == "offline").count()
    alerts = db.query(OperationalAlert).filter(
        OperationalAlert.company_id == company.id,
        OperationalAlert.status.in_(("open", "acknowledged")),
    ).count()

    agent_online, agent_stale, communication = _agent_communication(company)
    onboarding = _onboarding_state(company, active_printers, communication)
    onboarding_progress, next_action = _onboarding_progress(onboarding)
    readiness_score, commercial_ready, blockers = _commercial_readiness(
        company,
        onboarding,
        communication,
        active_printers,
        alerts,
    )

    return {
        "uuid": company.uuid,
        "name": company.name,
        "plan": company.plan,
        "active": company.active,
        "agent": {
            "online": agent_online,
            "stale": agent_stale,
            "communication_state": communication,
            "status": company.agent_status,
            "name": company.agent_name,
            "version": company.agent_version,
            "last_seen": (
                company.agent_last_seen.isoformat()
                if company.agent_last_seen is not None
                else None
            ),
            "last_error": company.agent_last_error,
        },
        "printers": {
            "active": active_printers,
            "online": online_printers,
            "offline": offline_printers,
        },
        "alerts_open": alerts,
        "onboarding": {
            "state": onboarding,
            "progress": onboarding_progress,
            "next_action": next_action,
        },
        "commercial": {
            "readiness_score": readiness_score,
            "ready": commercial_ready,
            "blockers": blockers,
        },
    }


def _organization_snapshot(db: Session, company: Company) -> dict:
    printers = db.query(Printer).filter(
        Printer.company_id == company.id,
        Printer.active.is_(True),
    ).all()
    units: dict[str, int] = {}
    sectors: dict[str, int] = {}
    unassigned = 0
    for printer in printers:
        if printer.unit_name:
            units[printer.unit_name] = units.get(printer.unit_name, 0) + 1
        if printer.sector_name:
            sectors[printer.sector_name] = sectors.get(printer.sector_name, 0) + 1
        if not printer.unit_name and not printer.sector_name:
            unassigned += 1
    return {
        "company_uuid": company.uuid,
        "units": [
            {"name": name, "printers": count}
            for name, count in sorted(units.items())
        ],
        "sectors": [
            {"name": name, "printers": count}
            for name, count in sorted(sectors.items())
        ],
        "unassigned_printers": unassigned,
    }


def _usage_report_rows(
    db: Session,
    company: Company,
    start_date: date | None,
    end_date: date | None,
    printer_uuid: str | None,
    unit_name: str | None,
    sector_name: str | None,
) -> dict:
    start, end = _resolve_period(start_date, end_date)
    _validate_report_filters(
        db,
        company.id,
        printer_uuid,
        unit_name,
        sector_name,
    )
    history = _usage_query(
        db,
        company.id,
        start,
        end,
        printer_uuid,
        unit_name,
        sector_name,
    ).all()
    printers = _current_printers(
        db,
        company.id,
        printer_uuid,
        unit_name,
        sector_name,
    )
    rows = consolidate_usage(
        history,
        printers,
        company.default_cost_per_page or 0,
    )
    return {
        "company_uuid": company.uuid,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "filters": {
            "printer_uuid": printer_uuid,
            "unit_name": unit_name,
            "sector_name": sector_name,
        },
        "rows": rows,
        "totals": {
            "printers": len(rows),
            "pages_printed": sum(int(row.get("pages_printed") or 0) for row in rows),
            "estimated_cost": round(
                sum(float(row.get("estimated_cost") or 0) for row in rows),
                2,
            ),
            "anomalies": sum(int(row.get("anomaly_count") or 0) for row in rows),
        },
    }


@router.get("/openapi.json", include_in_schema=False)
def integration_openapi() -> dict:
    """Schema público da integração; os dados permanecem protegidos pela chave."""
    return INTEGRATION_OPENAPI


@router.get("/status", dependencies=[Depends(require_integration_key)])
def integration_status(db: Session = Depends(get_db)) -> dict:
    companies = db.query(Company).all()
    printers = db.query(Printer).filter(Printer.active.is_(True)).count()
    alerts = db.query(OperationalAlert).filter(
        OperationalAlert.status.in_(("open", "acknowledged"))
    ).count()
    agents_online = sum(1 for company in companies if _agent_communication(company)[0])

    return {
        "application": "Printflow Integration API",
        "mode": "read_only",
        "status": "healthy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companies": len(companies),
        "agents_online": agents_online,
        "active_printers": printers,
        "open_alerts": alerts,
    }


@router.get("/companies", dependencies=[Depends(require_integration_key)])
def list_companies(db: Session = Depends(get_db)) -> list[dict]:
    companies = db.query(Company).order_by(Company.name.asc()).all()
    return [_company_snapshot(db, company) for company in companies]


@router.get("/companies/{company_uuid}", dependencies=[Depends(require_integration_key)])
def get_company(company_uuid: str, db: Session = Depends(get_db)) -> dict:
    return _company_snapshot(db, _find_company(db, company_uuid))


@router.get(
    "/companies/{company_uuid}/printers",
    dependencies=[Depends(require_integration_key)],
)
def list_company_printers(company_uuid: str, db: Session = Depends(get_db)) -> list[dict]:
    company = _find_company(db, company_uuid)
    printers = db.query(Printer).filter(
        Printer.company_id == company.id
    ).order_by(Printer.id.desc()).all()
    return [serialize_printer(printer) for printer in printers]


@router.get(
    "/companies/{company_uuid}/users",
    dependencies=[Depends(require_integration_key)],
)
def list_company_users(company_uuid: str, db: Session = Depends(get_db)) -> list[dict]:
    company = _find_company(db, company_uuid)
    users = db.query(User).filter(User.company_id == company.id).order_by(User.name.asc()).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "active": user.active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


@router.get(
    "/companies/{company_uuid}/alerts",
    dependencies=[Depends(require_integration_key)],
)
def list_company_alerts(company_uuid: str, db: Session = Depends(get_db)) -> list[dict]:
    company = _find_company(db, company_uuid)
    alerts = db.query(OperationalAlert).filter(
        OperationalAlert.company_id == company.id,
        OperationalAlert.status.in_(("open", "acknowledged")),
    ).order_by(OperationalAlert.last_seen_at.desc()).limit(100).all()
    return [
        {
            "id": alert.id,
            "printer_id": alert.printer_id,
            "category": alert.category,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "status": alert.status,
            "opened_at": alert.opened_at.isoformat() if alert.opened_at else None,
            "last_seen_at": alert.last_seen_at.isoformat() if alert.last_seen_at else None,
        }
        for alert in alerts
    ]


@router.get(
    "/companies/{company_uuid}/organization",
    dependencies=[Depends(require_integration_key)],
)
def get_company_organization(company_uuid: str, db: Session = Depends(get_db)) -> dict:
    return _organization_snapshot(db, _find_company(db, company_uuid))


@router.get(
    "/companies/{company_uuid}/usage/report",
    dependencies=[Depends(require_integration_key)],
)
def get_company_usage_report(
    company_uuid: str,
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return _usage_report_rows(
        db,
        _find_company(db, company_uuid),
        start_date,
        end_date,
        printer_uuid,
        unit_name,
        sector_name,
    )


@router.get(
    "/companies/{company_uuid}/usage/daily",
    dependencies=[Depends(require_integration_key)],
)
def get_company_daily_usage(
    company_uuid: str,
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    company = _find_company(db, company_uuid)
    start, end = _resolve_period(start_date, end_date)
    _validate_report_filters(
        db,
        company.id,
        printer_uuid,
        unit_name,
        sector_name,
    )
    rows = _usage_query(
        db,
        company.id,
        start,
        end,
        printer_uuid,
        unit_name,
        sector_name,
    ).all()
    return [
        {
            "usage_date": row.usage_date.isoformat(),
            "printer_uuid": row.printer_uuid,
            "ip": row.ip,
            "name": row.name,
            "custom_name": row.custom_name,
            "hostname": row.hostname,
            "manufacturer": row.manufacturer,
            "model": row.model,
            "serial": row.serial,
            "unit_name": row.unit_name,
            "sector_name": row.sector_name,
            "opening_page_count": row.opening_page_count,
            "closing_page_count": row.closing_page_count,
            "pages_printed": row.pages_printed,
            "anomaly_count": row.anomaly_count,
            "last_anomaly_type": row.last_anomaly_type,
            "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        }
        for row in rows
    ]
