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

    if normalized in {
        "online",
        "ativo",
        "active",
        "idle",
        "printing",
        "warmup",
    }:
        return "online"

    if normalized in {
        "offline",
        "inativo",
        "inactive",
        "error",
        "critical",
    }:
        return "offline"

    return normalized or "unknown"


def integer_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def serialize_printer(printer: Printer) -> dict[str, Any]:
    status = normalize_status(
        getattr(printer, "status", None)
    )

    page_count = integer_value(
        getattr(printer, "page_count", None)
    )

    last_seen = getattr(
        printer,
        "last_seen",
        None,
    )

    active = bool(
        getattr(printer, "active", True)
    )

    if not active:
        status = "inactive"

    health_score = 100
    health_reasons: list[str] = []

    if not active:
        health_score -= 50
        health_reasons.append(
            "Equipamento marcado como inativo."
        )

    if status == "offline":
        health_score -= 40
        health_reasons.append(
            "Impressora está offline."
        )

    elif status == "unknown":
        health_score -= 15
        health_reasons.append(
            "Status da impressora não identificado."
        )

    if page_count is not None and page_count >= 500000:
        health_score -= 10
        health_reasons.append(
            "Contador elevado; avaliar manutenção preventiva."
        )

    if last_seen is not None:
        try:
            now = datetime.now(timezone.utc)

            normalized_last_seen = last_seen

            if normalized_last_seen.tzinfo is None:
                normalized_last_seen = (
                    normalized_last_seen.replace(
                        tzinfo=timezone.utc
                    )
                )

            age_seconds = (
                now - normalized_last_seen
            ).total_seconds()

            if age_seconds > 86400:
                health_score -= 20
                health_reasons.append(
                    "Sem comunicação há mais de 24 horas."
                )

            elif age_seconds > 3600:
                health_score -= 5
                health_reasons.append(
                    "Comunicação atrasada há mais de 1 hora."
                )

        except Exception:
            pass

    health_score = max(
        0,
        min(health_score, 100),
    )

    if health_score >= 85:
        health_status = "excellent"
    elif health_score >= 70:
        health_status = "good"
    elif health_score >= 50:
        health_status = "attention"
    else:
        health_status = "critical"

    if not health_reasons:
        health_reasons.append(
            "Nenhum risco crítico identificado."
        )

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
        "manufacturer": getattr(
            printer,
            "manufacturer",
            None,
        ),
        "model": getattr(printer, "model", None),
        "status": status,
        "source": getattr(printer, "source", None),
        "page_count": page_count,
        "page_count_source": getattr(printer, "page_count_source", None),
        "page_count_confidence": getattr(printer, "page_count_confidence", None),
        "page_count_confirmed": bool(
            getattr(printer, "page_count_confirmed", False)
        ),
        "serial": getattr(printer, "serial", None),
        "serial_source": getattr(printer, "serial_source", None),
        "serial_confidence": getattr(printer, "serial_confidence", None),
        "serial_confirmed": bool(
            getattr(printer, "serial_confirmed", False)
        ),
        "toner_percent": getattr(printer, "toner_percent", None),
        "active": active,
        "last_seen": (
            last_seen.isoformat()
            if last_seen is not None
            else None
        ),
        "created_at": (
            getattr(printer, "created_at", None).isoformat()
            if getattr(printer, "created_at", None)
            else None
        ),
        "health_score": health_score,
        "health_status": health_status,
        "health_reasons": health_reasons,
    }


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    printers = (
        db.query(Printer)
        .filter(Printer.company_id == current_user.company_id)
        .all()
    )
    company = (
        db.query(Company)
        .filter(Company.id == current_user.company_id)
        .first()
    )

    serialized = [
        serialize_printer(printer)
        for printer in printers
    ]

    total = len(serialized)

    online = sum(
        1
        for printer in serialized
        if printer["active"] and printer["status"] == "online"
    )

    offline = sum(
        1
        for printer in serialized
        if printer["active"] and printer["status"] == "offline"
    )

    active = sum(
        1
        for printer in serialized
        if printer["active"]
    )
    monitored = [
        printer for printer in serialized if printer["active"]
    ]

    total_pages = sum(
        printer["page_count"]
        for printer in monitored
        if printer["page_count"] is not None
    )
    inactive = total - active
    unknown = active - online - offline
    page_count_known = sum(
        1 for printer in monitored
        if printer["page_count"] is not None
    )

    alerts = sum(
        1
        for printer in monitored
        if (
            printer["health_score"] < 70
            or printer["status"] == "offline"
        )
    )

    health_average = (
        round(
            sum(
                printer["health_score"]
                for printer in monitored
            ) / active
        )
        if active
        else 100
    )

    manufacturers: dict[str, int] = {}

    for printer in monitored:
        manufacturer = (
            printer["manufacturer"]
            or "Não identificado"
        )

        manufacturers[manufacturer] = (
            manufacturers.get(
                manufacturer,
                0,
            )
            + 1
        )

    agent_last_seen = getattr(company, "agent_last_seen", None)
    agent_online = False
    if agent_last_seen is not None:
        normalized_seen = agent_last_seen
        if normalized_seen.tzinfo is None:
            normalized_seen = normalized_seen.replace(tzinfo=timezone.utc)
        agent_online = (
            datetime.now(timezone.utc) - normalized_seen
        ).total_seconds() <= 1800

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
            "status": getattr(company, "agent_status", None),
            "name": getattr(company, "agent_name", None),
            "version": getattr(company, "agent_version", None),
            "last_seen": (
                agent_last_seen.isoformat()
                if agent_last_seen is not None
                else None
            ),
            "last_error": getattr(company, "agent_last_error", None),
        },
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@router.get("/printers")
def dashboard_printers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    printers = (
        db.query(Printer)
        .filter(Printer.company_id == current_user.company_id)
        .order_by(Printer.id.desc())
        .all()
    )

    return [
        serialize_printer(printer)
        for printer in printers
    ]


@router.get("/printers/{printer_uuid}")
def dashboard_printer_detail(
    printer_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    printer = (
        db.query(Printer)
        .filter(
            Printer.uuid == printer_uuid,
            Printer.company_id == current_user.company_id,
        )
        .first()
    )

    if not printer:
        raise HTTPException(
            status_code=404,
            detail="Impressora não encontrada.",
        )

    return serialize_printer(printer)
