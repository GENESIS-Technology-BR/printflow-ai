from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from ..printers.model import Printer


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)


def normalize_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"online", "ativo", "active", "idle", "printing", "warmup"}:
        return "online"
    if normalized in {"offline", "inativo", "inactive", "error", "critical"}:
        return "offline"
    return normalized or "unknown"


def integer_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _age_seconds(last_seen: datetime | None) -> float | None:
    if last_seen is None:
        return None
    try:
        normalized = last_seen
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - normalized).total_seconds())
    except Exception:
        return None


def serialize_printer(printer: Printer) -> dict[str, Any]:
    status = normalize_status(getattr(printer, "status", None))
    page_count = integer_value(getattr(printer, "page_count", None))
    cost_per_page = getattr(printer, "cost_per_page", None)
    last_seen = getattr(printer, "last_seen", None)
    stored_active = bool(getattr(printer, "active", True))
    age_seconds = _age_seconds(last_seen)

    recently_seen_online = (
        age_seconds is not None
        and age_seconds <= 600
        and status == "online"
    )
    active = stored_active or recently_seen_online

    if recently_seen_online:
        status = "online"
    elif not active:
        status = "inactive"

    health_score = 100
    health_reasons: list[str] = []

    if not active:
        health_score -= 50
        health_reasons.append("Equipamento marcado como inativo e sem comunicação online recente.")

    if status == "offline":
        health_score -= 40
        health_reasons.append("Impressora está offline.")
    elif status == "unknown":
        health_score -= 15
        health_reasons.append("Status da impressora não identificado.")

    if age_seconds is not None:
        if age_seconds > 86400:
            health_score -= 20
            health_reasons.append("Sem comunicação há mais de 24 horas.")
        elif age_seconds > 3600:
            health_score -= 5
            health_reasons.append("Comunicação atrasada há mais de 1 hora.")

    health_score = max(0, min(health_score, 100))
    if health_score >= 85:
        health_status = "excellent"
    elif health_score >= 70:
        health_status = "good"
    elif health_score >= 50:
        health_status = "attention"
    else:
        health_status = "critical"

    if not health_reasons:
        health_reasons.append("Nenhum risco crítico identificado.")

    return {
        "id": getattr(printer, "id", None),
        "uuid": getattr(printer, "uuid", None),
        "ip": getattr(printer, "ip", None),
        "name": getattr(printer, "name", "Impressora"),
        "hostname": getattr(printer, "hostname", None),
        "custom_name": getattr(printer, "custom_name", None),
        "unit_name": getattr(printer, "unit_name", None),
        "sector_name": getattr(printer, "sector_name", None),
        "unit_id": getattr(printer, "unit_id", None),
        "sector_id": getattr(printer, "sector_id", None),
        "manufacturer": getattr(printer, "manufacturer", None),
        "model": getattr(printer, "model", None),
        "status": status,
        "source": getattr(printer, "source", None),
        "page_count": page_count,
        "page_count_source": getattr(printer, "page_count_source", None),
        "page_count_confidence": getattr(printer, "page_count_confidence", None),
        "page_count_confirmed": bool(getattr(printer, "page_count_confirmed", False)),
        "cost_per_page": float(cost_per_page) if cost_per_page is not None else None,
        "serial": getattr(printer, "serial", None),
        "serial_source": getattr(printer, "serial_source", None),
        "serial_confidence": getattr(printer, "serial_confidence", None),
        "serial_confirmed": bool(getattr(printer, "serial_confirmed", False)),
        "toner_percent": getattr(printer, "toner_percent", None),
        "active": active,
        "last_seen": last_seen.isoformat() if last_seen is not None else None,
        "created_at": getattr(printer, "created_at", None).isoformat() if getattr(printer, "created_at", None) else None,
        "health_score": health_score,
        "health_status": health_status,
        "health_reasons": health_reasons,
    }


def _is_label_printer(printer: Printer) -> bool:
    text = " ".join(
        str(value or "")
        for value in (
            getattr(printer, "manufacturer", None),
            getattr(printer, "model", None),
            getattr(printer, "name", None),
            getattr(printer, "custom_name", None),
        )
    ).lower()
    return any(marker in text for marker in ("zebra", "zt230", "zpl", "ztc "))


def _company_inventory(db: Session, company_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retorna inventário visível e parque monitorado conforme regra comercial da empresa."""
    printers = db.query(Printer).filter(Printer.company_id == company_id).all()
    company = db.query(Company).filter(Company.id == company_id).first()
    if company and "guerra" in (company.name or "").strip().lower():
        printers = [printer for printer in printers if not _is_label_printer(printer)]
    serialized = [serialize_printer(printer) for printer in printers]
    monitored = [printer for printer in serialized if printer["active"]]
    return serialized, monitored


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    serialized, monitored = _company_inventory(db, current_user.company_id)
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    total = len(serialized)
    active = len(monitored)
    online = sum(1 for printer in monitored if printer["status"] == "online")
    offline = sum(1 for printer in monitored if printer["status"] == "offline")
    total_pages = sum(printer["page_count"] for printer in monitored if printer["page_count"] is not None)
    inactive = total - active
    unknown = active - online - offline
    page_count_known = sum(1 for printer in monitored if printer["page_count"] is not None)
    alerts = sum(1 for printer in monitored if printer["health_score"] < 70 or printer["status"] == "offline")
    health_average = round(sum(printer["health_score"] for printer in monitored) / active) if active else 100

    manufacturers: dict[str, int] = {}
    for printer in monitored:
        manufacturer = printer["manufacturer"] or "Não identificado"
        manufacturers[manufacturer] = manufacturers.get(manufacturer, 0) + 1

    agent_last_seen = getattr(company, "agent_last_seen", None)
    agent_online = False
    agent_stale = False
    agent_age_seconds: int | None = None
    agent_communication_state = "never_seen"
    age = _age_seconds(agent_last_seen)
    if age is not None:
        agent_age_seconds = int(age)
        if agent_age_seconds <= 600:
            agent_online = True
            agent_communication_state = "healthy"
        elif agent_age_seconds <= 1800:
            agent_stale = True
            agent_communication_state = "stale"
        else:
            agent_communication_state = "offline"

    return {
        "total_printers": total,
        "active_printers": active,
        "inactive_printers": inactive,
        "online": online,
        "offline": offline,
        "unknown": unknown,
        "alerts": alerts,
        "total_pages": total_pages,
        "page_count_known": page_count_known,
        "page_count_unknown": active - page_count_known,
        "health_average": health_average,
        "manufacturers": manufacturers,
        "agent": {
            "online": agent_online,
            "stale": agent_stale,
            "communication_state": agent_communication_state,
            "age_seconds": agent_age_seconds,
            "status": getattr(company, "agent_status", None),
            "name": getattr(company, "agent_name", None),
            "version": getattr(company, "agent_version", None),
            "last_seen": agent_last_seen.isoformat() if agent_last_seen is not None else None,
            "last_error": getattr(company, "agent_last_error", None),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/printers")
def dashboard_printers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    _, monitored = _company_inventory(db, current_user.company_id)
    return sorted(monitored, key=lambda printer: int(printer.get("id") or 0), reverse=True)


@router.get("/printers/{printer_uuid}")
def dashboard_printer_detail(printer_uuid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    printer = db.query(Printer).filter(Printer.uuid == printer_uuid, Printer.company_id == current_user.company_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Impressora não encontrada.")
    return serialize_printer(printer)