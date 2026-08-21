from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.modules.alerts.model import OperationalAlert
from backend.modules.auth.model import User
from backend.modules.printers.model import Printer


def _normalized_seen(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def desired_alerts(printer: Printer, item: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    printer_key = str(printer.uuid or printer.id)
    name = item["name"]

    def add(category: str, severity: str, title: str, description: str) -> None:
        alerts.append({
            "event_key": f"printer:{printer_key}:{category}",
            "category": category,
            "severity": severity,
            "title": title,
            "description": description,
        })

    if not item["active"] or item["status"] == "offline":
        description = (
            f"Sem comunicação no endereço {item['ip']}."
            if item["ip"] else "Equipamento sem comunicação."
        )
        add("offline", "critical", f"{name} está offline", description)

    if item["health_score"] < 50:
        add("health", "critical", f"Saúde crítica: {name}", item["health_reasons"][0])
    elif item["health_score"] < 70:
        add("health", "warning", f"Atenção: {name}", item["health_reasons"][0])

    page_count = item["page_count"]
    if page_count is not None and page_count >= 500000:
        add(
            "page_count", "warning", f"Contador elevado: {name}",
            "Avaliar manutenção preventiva e vida útil do equipamento.",
        )

    toner = item["toner_percent"]
    if toner is not None and toner <= 15:
        add(
            "toner", "critical" if toner <= 5 else "warning",
            f"Toner baixo: {name}",
            f"Suprimento em {toner}%. Planejar reposição.",
        )

    last_seen = _normalized_seen(getattr(printer, "last_seen", None))
    if item["active"] and last_seen is not None:
        if (datetime.now(timezone.utc) - last_seen).total_seconds() > 86400:
            add(
                "stale", "warning", f"Coleta atrasada: {name}",
                "Sem atualização de inventário nas últimas 24 horas.",
            )

    return alerts


def reconcile_company_alerts(
    db: Session,
    company_id: int,
    serializer: Callable[[Printer], dict[str, Any]],
) -> list[OperationalAlert]:
    now = datetime.now(timezone.utc)
    printers = db.query(Printer).filter(Printer.company_id == company_id).all()
    desired: dict[str, tuple[Printer, dict[str, str]]] = {}
    for printer in printers:
        for item in desired_alerts(printer, serializer(printer)):
            desired[item["event_key"]] = (printer, item)

    open_alerts = db.query(OperationalAlert).filter(
        OperationalAlert.company_id == company_id,
        OperationalAlert.status.in_(("open", "acknowledged")),
    ).all()
    open_by_key = {alert.event_key: alert for alert in open_alerts}

    for event_key, (printer, item) in desired.items():
        alert = open_by_key.get(event_key)
        if alert is None:
            db.add(OperationalAlert(
                company_id=company_id,
                printer_id=printer.id,
                event_key=event_key,
                category=item["category"],
                severity=item["severity"],
                title=item["title"],
                description=item["description"],
                status="open",
                opened_at=now,
                last_seen_at=now,
            ))
        else:
            alert.severity = item["severity"]
            alert.title = item["title"]
            alert.description = item["description"]
            alert.last_seen_at = now

    for event_key, alert in open_by_key.items():
        if event_key not in desired:
            alert.status = "resolved"
            alert.resolved_at = now

    db.commit()
    return db.query(OperationalAlert).filter(
        OperationalAlert.company_id == company_id
    ).order_by(OperationalAlert.opened_at.desc(), OperationalAlert.id.desc()).all()


def serialize_alert(alert: OperationalAlert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "printer_id": alert.printer_id,
        "event_key": alert.event_key,
        "category": alert.category,
        "severity": alert.severity,
        "title": alert.title,
        "description": alert.description,
        "status": alert.status,
        "opened_at": alert.opened_at.isoformat(),
        "last_seen_at": alert.last_seen_at.isoformat(),
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "acknowledged_at": (
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        ),
        "acknowledged_by": alert.acknowledged_by,
    }


def acknowledge_alert(
    db: Session,
    company_id: int,
    alert_id: int,
    user_id: int,
) -> OperationalAlert | None:
    """Reconhece um alerta ativo pertencente à empresa autenticada."""
    user_exists = db.query(User.id).filter(
        User.id == user_id,
        User.company_id == company_id,
        User.active.is_(True),
    ).first()
    if user_exists is None:
        return None
    alert = db.query(OperationalAlert).filter(
        OperationalAlert.id == alert_id,
        OperationalAlert.company_id == company_id,
        OperationalAlert.status.in_(("open", "acknowledged")),
    ).first()
    if alert is None:
        return None
    if alert.status == "open":
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id
        db.commit()
        db.refresh(alert)
    return alert
