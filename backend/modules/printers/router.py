from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.organization.model import CompanySector, CompanyUnit
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import (
    AgentHeartbeat,
    PrinterCostUpdate,
    PrinterCustomNameUpdate,
    PrinterOrganizationUpdate,
    PrinterResponse,
    PrinterSerialUpdate,
    PrinterUpsert,
)
from backend.modules.usage.service import record_daily_printer_usage


router = APIRouter(prefix="/printers", tags=["Printers"])


# Regra comercial temporaria da Guerra: impressoras Zebra permanecem no
# inventario/Agent, mas nao devem ser expostas no portal do cliente.
GUERRA_COMPANY_ID = 1


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
        "energy saver",
        "sleep mode",
        "power save",
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


def _merge_page_count(
    current_value: int | None,
    current_confidence: int | None,
    incoming_value: int | None,
    incoming_confidence: int | None,
    incoming_confirmed: bool,
) -> tuple[int | None, int | None, bool]:
    """Mantem contador monotonicamente crescente sem bloquear total confirmado."""
    if incoming_value is None:
        return current_value, current_confidence, False

    if current_value is not None and incoming_value < current_value:
        return current_value, current_confidence, False

    if current_value is not None and incoming_value == current_value:
        return current_value, current_confidence, False

    # Um total fisico confirmado pelo Agent pode corrigir um valor historico
    # menor mesmo quando a confianca antiga era artificialmente mais alta.
    if incoming_confirmed:
        return incoming_value, incoming_confidence, True

    value, confidence, updated = _merge_trusted(
        current_value,
        current_confidence,
        incoming_value,
        incoming_confidence,
    )
    return value, confidence, updated


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
    query = db.query(Printer).filter(
        Printer.company_id == current_user.company_id
    )
    if current_user.company_id == GUERRA_COMPANY_ID:
        query = query.filter(
            ~func.coalesce(Printer.manufacturer, "").ilike("%zebra%"),
            ~func.coalesce(Printer.model, "").ilike("%zebra%"),
            ~func.coalesce(Printer.name, "").ilike("%zebra%"),
        )
    return query.order_by(Printer.id.desc()).all()


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

    if payload.status in {"healthy", "slow"} and payload.inventory_complete:
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
    printer.hostname = _merge_optional(
        printer.hostname,
        _clean_text(payload.hostname),
    )
    printer.manufacturer = _merge_optional(
        printer.manufacturer, _clean_text(payload.manufacturer)
    )
    printer.model = _merge_optional(
        printer.model, _clean_text(payload.model)
    )
    printer.status = payload.status
    printer.source = payload.source
    page_count, page_confidence, page_updated = _merge_page_count(
        printer.page_count,
        printer.page_count_confidence,
        payload.page_count,
        payload.page_count_confidence,
        payload.page_count_confirmed,
    )
    if page_updated:
        printer.page_count = page_count
        printer.page_count_confidence = page_confidence
        printer.page_count_source = _clean_text(payload.page_count_source)
        printer.page_count_confirmed = payload.page_count_confirmed

    current_serial = _valid_serial(printer.serial)
    if printer.serial is not None and current_serial is None:
        printer.serial = None
        printer.serial_confidence = None
        printer.serial_source = None
        printer.serial_confirmed = False

    # Um serial confirmado manualmente e a fonte autoritativa. O Agent pode
    # continuar reportando candidatos, mas nao deve sobrescrever a confirmacao.
    manual_serial_locked = (
        printer.serial_confirmed
        and printer.serial_source == "manual"
        and _valid_serial(printer.serial) is not None
    )
    if not manual_serial_locked:
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

    if page_updated and printer.page_count is not None:
        db.flush()
        record_daily_printer_usage(
            db,
            printer,
            observed_at=printer.last_seen,
        )

    db.commit()
    db.refresh(printer)

    return printer


@router.post("/maintenance/uppercase-custom-names")
def uppercase_custom_names(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Normaliza nomes personalizados somente no tenant autenticado."""
    if current_user.role not in {"admin", "owner", "superadmin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operacao restrita a administradores.",
        )

    printers = (
        db.query(Printer)
        .filter(
            Printer.company_id == current_user.company_id,
            Printer.custom_name.isnot(None),
        )
        .all()
    )
    updated = 0
    for printer in printers:
        normalized = _clean_text(printer.custom_name)
        normalized = normalized.upper() if normalized else None
        if printer.custom_name != normalized:
            printer.custom_name = normalized
            updated += 1

    db.commit()
    return {"status": "ok", "updated": updated}


@router.patch(
    "/{printer_uuid}/custom-name",
    response_model=PrinterResponse,
)
def update_printer_custom_name(
    printer_uuid: str,
    payload: PrinterCustomNameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    printer = (
        db.query(Printer)
        .filter(
            Printer.uuid == printer_uuid,
            Printer.company_id == current_user.company_id,
        )
        .first()
    )

    if printer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Impressora nao encontrada.",
        )

    custom_name = _clean_text(payload.custom_name)
    printer.custom_name = custom_name.upper() if custom_name else None
    db.commit()
    db.refresh(printer)
    return printer


@router.patch(
    "/{printer_uuid}/serial",
    response_model=PrinterResponse,
)
def update_printer_serial(
    printer_uuid: str,
    payload: PrinterSerialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    printer = (
        db.query(Printer)
        .filter(
            Printer.uuid == printer_uuid,
            Printer.company_id == current_user.company_id,
        )
        .first()
    )
    if printer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Impressora nao encontrada.",
        )

    serial = _valid_serial(payload.serial)
    if serial is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Numero de serie invalido.",
        )

    printer.serial = serial
    printer.serial_source = "manual"
    printer.serial_confidence = 100
    printer.serial_confirmed = True
    db.commit()
    db.refresh(printer)
    return printer


@router.patch(
    "/{printer_uuid}/cost",
    response_model=PrinterResponse,
)
def update_printer_cost(
    printer_uuid: str,
    payload: PrinterCostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    printer = (
        db.query(Printer)
        .filter(
            Printer.uuid == printer_uuid,
            Printer.company_id == current_user.company_id,
        )
        .first()
    )
    if printer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Impressora nao encontrada.",
        )

    printer.cost_model = payload.cost_model
    if payload.cost_model == "fixed_monthly":
        printer.fixed_monthly_cost = payload.fixed_monthly_cost
        printer.cost_per_page = None
    else:
        printer.cost_per_page = payload.cost_per_page
        printer.fixed_monthly_cost = None
    db.commit()
    db.refresh(printer)
    return printer


@router.patch(
    "/{printer_uuid}/organization",
    response_model=PrinterResponse,
)
def update_printer_organization(
    printer_uuid: str,
    payload: PrinterOrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    printer = (
        db.query(Printer)
        .filter(
            Printer.uuid == printer_uuid,
            Printer.company_id == current_user.company_id,
        )
        .first()
    )

    if printer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Impressora nao encontrada.",
        )

    unit_name = _clean_text(payload.unit_name)
    sector_name = _clean_text(payload.sector_name)

    if unit_name is None:
        if sector_name is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selecione uma unidade antes do setor.",
            )

        printer.unit_id = None
        printer.sector_id = None
        printer.unit_name = None
        printer.sector_name = None

    else:
        unit = (
            db.query(CompanyUnit)
            .filter(
                CompanyUnit.company_id == current_user.company_id,
                CompanyUnit.name == unit_name,
                CompanyUnit.active.is_(True),
            )
            .first()
        )

        if unit is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unidade inválida ou inativa.",
            )

        printer.unit_id = unit.id
        printer.unit_name = unit.name

        if sector_name is None:
            printer.sector_id = None
            printer.sector_name = None
        else:
            sector = (
                db.query(CompanySector)
                .filter(
                    CompanySector.company_id == current_user.company_id,
                    CompanySector.unit_id == unit.id,
                    CompanySector.name == sector_name,
                    CompanySector.active.is_(True),
                )
                .first()
            )

            if sector is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Setor inválido para a unidade selecionada.",
                )

            printer.sector_id = sector.id
            printer.sector_name = sector.name

    db.commit()
    db.refresh(printer)
    return printer
