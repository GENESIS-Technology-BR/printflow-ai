from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
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


def integer_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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

    if page_count >= 500000:
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
        "manufacturer": getattr(
            printer,
            "manufacturer",
            None,
        ),
        "model": getattr(printer, "model", None),
        "status": status,
        "source": getattr(printer, "source", None),
        "page_count": page_count,
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
) -> dict[str, Any]:
    printers = db.query(Printer).all()

    serialized = [
        serialize_printer(printer)
        for printer in printers
    ]

    total = len(serialized)

    online = sum(
        1
        for printer in serialized
        if printer["status"] == "online"
    )

    offline = sum(
        1
        for printer in serialized
        if printer["status"] == "offline"
    )

    unknown = total - online - offline

    active = sum(
        1
        for printer in serialized
        if printer["active"]
    )

    total_pages = sum(
        printer["page_count"]
        for printer in serialized
    )

    alerts = sum(
        1
        for printer in serialized
        if (
            printer["health_score"] < 70
            or printer["status"] == "offline"
        )
    )

    health_average = (
        round(
            sum(
                printer["health_score"]
                for printer in serialized
            ) / total
        )
        if total
        else 100
    )

    manufacturers: dict[str, int] = {}

    for printer in serialized:
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

    return {
        "total_printers": total,
        "active_printers": active,
        "online": online,
        "offline": offline,
        "unknown": unknown,
        "alerts": alerts,
        "total_pages": total_pages,
        "health_average": health_average,
        "manufacturers": manufacturers,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@router.get("/printers")
def dashboard_printers(
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    printers = (
        db.query(Printer)
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
) -> dict[str, Any]:
    printer = (
        db.query(Printer)
        .filter(Printer.uuid == printer_uuid)
        .first()
    )

    if not printer:
        raise HTTPException(
            status_code=404,
            detail="Impressora não encontrada.",
        )

    return serialize_printer(printer)
