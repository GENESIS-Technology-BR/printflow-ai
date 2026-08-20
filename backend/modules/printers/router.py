from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import (
    AgentHeartbeat,
    PrinterResponse,
    PrinterUpsert,
)


router = APIRouter(prefix="/printers", tags=["Printers"])


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _valid_serial(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None

    normalized = cleaned.lower()
    description_markers = (
        " zpl",
        " printer",
        " technologies",
        "203dpi",
        "300dpi",
        "600dpi",
    )
    if any(marker in normalized for marker in description_markers):
        return None
    return cleaned


def _merge_optional(current, incoming):
    return current if incoming is None else incoming


def _merge_trusted(
    current_value,
    current_confidence: int | None,
    incoming_value,
    incoming_confidence: int | None,
) -> tuple[object, int | None, bool]:
    if incoming_value is None:
        return current_value, current_confidence, False
    if current_value is None:
        return incoming_value, incoming_confidence, True
    if incoming_confidence is None:
        return current_value, current_confidence, False
    if current_confidence is None or incoming_confidence >= current_confidence:
        return incoming_value, incoming_confidence, True
    return current_value, current_confidence, False


def _reconcile_inventory(
    printers: list[Printer], observed_printer_ips: list[str]
) -> tuple[int, int]:
    observed_ips = {
        ip.strip()
        for ip in observed_printer_ips
        if ip and ip.strip()
    }
    active = 0
    inactive = 0
    for printer in printers:
        printer.active = printer.ip in observed_ips
        if printer.active:
            active += 1
        else:
            inactive += 1
    return active, inactive


@router.get("", response_model=list[PrinterResponse])
def list_printers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Printer)
        .filter(Printer.company_id == current_user.company_id)
        .order_by(Printer.id.desc())
        .all()
    )


@router.post(
    "/agent/heartbeat",
    status_code=status.HTTP_200_OK,
)
def receive_agent_heartbeat(
    payload: AgentHeartbeat,
    db: Session = Depends(get_db),
):
    company = (
        db.query(Company)
        .filter(
            Company.agent_token == payload.agent_token,
            Company.active.is_(True),
        )
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent Token inválido.",
        )

    company.agent_last_seen = datetime.now(timezone.utc)
    company.agent_status = payload.status
    company.agent_name = payload.agent_name
    company.agent_version = payload.agent_version
    company.agent_last_error = _clean_text(payload.error)

    # A lista só é autoritativa quando o Agent conclui todo o ciclo. Isso
    # preserva a frota anterior em falhas parciais, desligamentos e timeouts.
    if payload.status == "healthy" and payload.inventory_complete:
        company_printers = (
            db.query(Printer)
            .filter(Printer.company_id == company.id)
            .all()
        )
        _reconcile_inventory(
            company_printers,
            payload.observed_printer_ips,
        )
    db.commit()

    return {"status": "received"}


@router.post(
    "/agent",
    response_model=PrinterResponse,
    status_code=status.HTTP_200_OK,
)
def receive_agent_data(
    payload: PrinterUpsert,
    db: Session = Depends(get_db),
):
    company = (
        db.query(Company)
        .filter(
            Company.agent_token == payload.agent_token,
            Company.active.is_(True),
        )
        .first()
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent Token inválido.",
        )

    printer = (
        db.query(Printer)
        .filter(
            Printer.company_id == company.id,
            Printer.ip == payload.ip,
        )
        .first()
    )

    if printer is None:
        printer = Printer(
            company_id=company.id,
            ip=payload.ip,
        )
        db.add(printer)

    printer.name = payload.name
    printer.manufacturer = _merge_optional(
        printer.manufacturer, _clean_text(payload.manufacturer)
    )
    printer.model = _merge_optional(
        printer.model, _clean_text(payload.model)
    )
    printer.status = payload.status
    printer.source = payload.source
    page_count, page_confidence, page_updated = _merge_trusted(
        printer.page_count,
        printer.page_count_confidence,
        payload.page_count,
        payload.page_count_confidence,
    )
    if page_updated:
        printer.page_count = page_count
        printer.page_count_confidence = page_confidence
        printer.page_count_source = _clean_text(payload.page_count_source)
        printer.page_count_confirmed = payload.page_count_confirmed

    serial, serial_confidence, serial_updated = _merge_trusted(
        printer.serial,
        printer.serial_confidence,
        _valid_serial(payload.serial),
        payload.serial_confidence,
    )
    if serial_updated:
        printer.serial = serial
        printer.serial_confidence = serial_confidence
        printer.serial_source = _clean_text(payload.serial_source)
        printer.serial_confirmed = payload.serial_confirmed
    printer.toner_percent = _merge_optional(
        printer.toner_percent, payload.toner_percent
    )
    printer.health_score = _merge_optional(
        printer.health_score, payload.health_score
    )
    printer.health_status = _merge_optional(
        printer.health_status, _clean_text(payload.health_status)
    )
    printer.active = True
    printer.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(printer)

    return printer
