from calendar import monthrange
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer

from .model import PrinterUsageDaily
from .reporting import build_excel_report, consolidate_usage
from .pdf_reporting import build_pdf_report
from .schema import DailyUsageResponse, UsageReportRow
from .service import reporting_date

router = APIRouter(prefix="/usage", tags=["Usage"])


def _report_scope_label(rows: list[dict], printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None) -> str:
    parts: list[str] = []
    if unit_name: parts.append(f"Unidade: {unit_name}")
    if sector_name: parts.append(f"Setor: {sector_name}")
    if printer_uuid:
        selected = next((row for row in rows if row.get("printer_uuid") == printer_uuid), None)
        parts.append(f"Impressora: {selected.get('display_name') if selected else printer_uuid}")
    return " · ".join(parts) or "Parque completo"


def _resolve_period(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    report_today = reporting_date(); end = end_date or report_today; start = start_date or (end - timedelta(days=30))
    if start > end: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Data inicial nao pode ser maior que a final.")
    if (end - start).days > 366: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O periodo maximo por consulta e de 366 dias.")
    return start, end


def _usage_query(db: Session, company_id: int, start: date, end: date, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None):
    query = db.query(PrinterUsageDaily).filter(PrinterUsageDaily.company_id == company_id, PrinterUsageDaily.usage_date >= start, PrinterUsageDaily.usage_date <= end)
    if printer_uuid: query = query.filter(PrinterUsageDaily.printer_uuid == printer_uuid)
    if unit_name: query = query.filter(PrinterUsageDaily.unit_name == unit_name)
    if sector_name: query = query.filter(PrinterUsageDaily.sector_name == sector_name)
    return query.order_by(PrinterUsageDaily.usage_date.asc(), PrinterUsageDaily.printer_id.asc())


def _current_printers(db: Session, company_id: int, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None) -> list[Printer]:
    query = db.query(Printer).filter(Printer.company_id == company_id, Printer.active.is_(True))
    if printer_uuid: query = query.filter(Printer.uuid == printer_uuid)
    if unit_name: query = query.filter(Printer.unit_name == unit_name)
    if sector_name: query = query.filter(Printer.sector_name == sector_name)
    return query.order_by(Printer.name.asc()).all()


def _active_history(history: list[PrinterUsageDaily], printers: list[Printer]) -> list[PrinterUsageDaily]:
    allowed_uuids = {printer.uuid for printer in printers}
    return [row for row in history if row.printer_uuid in allowed_uuids]


def _merge_historical_printers(
    db: Session,
    company_id: int,
    current_printers: list[Printer],
    history: list[PrinterUsageDaily],
) -> list[Printer]:
    history_uuids = {
        row.printer_uuid
        for row in history
        if row.printer_uuid
    }
    if not history_uuids:
        return current_printers

    historical_printers = (
        db.query(Printer)
        .filter(
            Printer.company_id == company_id,
            Printer.uuid.in_(history_uuids),
        )
        .all()
    )

    merged = {
        printer.uuid: printer
        for printer in current_printers
        if printer.uuid
    }
    for printer in historical_printers:
        if printer.uuid:
            merged[printer.uuid] = printer

    return sorted(
        merged.values(),
        key=lambda printer: (printer.name or "").lower(),
    )


def _is_guerra_excluded_printer(printer: Printer) -> bool:
    ip = (printer.ip or "").strip()
    text = f"{printer.manufacturer or ''} {printer.model or ''} {printer.name or ''} {printer.custom_name or ''} {printer.hostname or ''}".lower()
    return (
        ip == "10.2.128.31"
        or "deskjet 2700" in text
        or any(marker in text for marker in ("zebra", "zt230", "zpl"))
    )


def _exclude_commercial_printers_for_company(company: Company | None, printers: list[Printer]) -> list[Printer]:
    """Aplica exclusoes comerciais especificas do contrato da Guerra."""
    company_name = (company.name if company else "").strip().lower()
    if "guerra" not in company_name:
        return printers
    return [printer for printer in printers if not _is_guerra_excluded_printer(printer)]


def _fixed_cost_for_period(monthly_cost: float, start: date, end: date) -> float:
    """Cobra o valor contratual fechado uma vez por mes calendario no periodo."""
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return round(max(monthly_cost, 0.0) * months, 2)


def _apply_cost_models(rows: list[dict], printers: list[Printer], start: date, end: date) -> list[dict]:
    printer_map = {printer.uuid: printer for printer in printers}
    for row in rows:
        printer = printer_map.get(row["printer_uuid"])
        if not printer: continue
        if _is_guerra_excluded_printer(printer):
            row["cost_per_page"] = 0.0; row["estimated_cost"] = 0.0; row["cost_source"] = "not_applicable"; continue
        if (printer.cost_model or "per_page") == "fixed_monthly" and printer.fixed_monthly_cost is not None:
            row["cost_per_page"] = 0.0; row["estimated_cost"] = _fixed_cost_for_period(float(printer.fixed_monthly_cost), start, end); row["cost_source"] = "fixed_monthly"
    return rows


def _validate_report_filters(db: Session, company_id: int, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None) -> None:
    if printer_uuid and db.query(Printer.id).filter(Printer.company_id == company_id, Printer.uuid == printer_uuid, Printer.active.is_(True)).first() is None: raise HTTPException(status_code=404, detail="Impressora nao encontrada para esta empresa.")
    if unit_name and db.query(Printer.id).filter(Printer.company_id == company_id, Printer.unit_name == unit_name, Printer.active.is_(True)).first() is None: raise HTTPException(status_code=404, detail="Unidade nao encontrada para esta empresa.")
    if sector_name and db.query(Printer.id).filter(Printer.company_id == company_id, Printer.sector_name == sector_name, Printer.active.is_(True)).first() is None: raise HTTPException(status_code=404, detail="Setor nao encontrado para esta empresa.")


def _report_data(db: Session, current_user: User, start: date, end: date, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None):
    _validate_report_filters(db, current_user.company_id, printer_uuid, unit_name, sector_name)
    history = _usage_query(
        db,
        current_user.company_id,
        start,
        end,
        printer_uuid,
        unit_name,
        sector_name,
    ).all()
    printers = _current_printers(
        db,
        current_user.company_id,
        printer_uuid,
        unit_name,
        sector_name,
    )
    printers = _merge_historical_printers(
        db,
        current_user.company_id,
        printers,
        history,
    )
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    printers = _exclude_commercial_printers_for_company(company, printers)
    history = _active_history(history, printers)
    default_cost = (company.default_bw_cost_per_page or company.default_cost_per_page) if company else 0
    rows = consolidate_usage(history, printers, default_cost)
    return _apply_cost_models(rows, printers, start, end), history


def _report_rows(db: Session, current_user: User, start: date, end: date, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None) -> list[dict]:
    rows, _ = _report_data(db, current_user, start, end, printer_uuid, unit_name, sector_name); return rows


@router.get("/daily", response_model=list[DailyUsageResponse])
def list_daily_usage(start_date: date | None = None, end_date: date | None = None, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start, end = _resolve_period(start_date, end_date)
    _validate_report_filters(db, current_user.company_id, printer_uuid, unit_name, sector_name)
    rows = _usage_query(
        db,
        current_user.company_id,
        start,
        end,
        printer_uuid,
        unit_name,
        sector_name,
    ).all()
    printers = _current_printers(
        db,
        current_user.company_id,
        printer_uuid,
        unit_name,
        sector_name,
    )
    printers = _merge_historical_printers(
        db,
        current_user.company_id,
        printers,
        rows,
    )
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    printers = _exclude_commercial_printers_for_company(company, printers)
    rows = _active_history(rows, printers)
    return [DailyUsageResponse(usage_date=u.usage_date, printer_uuid=u.printer_uuid, ip=u.ip, name=u.name, custom_name=u.custom_name, hostname=u.hostname, manufacturer=u.manufacturer, model=u.model, serial=u.serial, unit_name=u.unit_name, sector_name=u.sector_name, opening_page_count=u.opening_page_count, closing_page_count=u.closing_page_count, pages_printed=u.pages_printed, anomaly_count=u.anomaly_count, last_anomaly_type=u.last_anomaly_type, first_seen_at=u.first_seen_at, last_seen_at=u.last_seen_at) for u in rows]


@router.get("/report", response_model=list[UsageReportRow])
def usage_report(start_date: date | None = None, end_date: date | None = None, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start, end = _resolve_period(start_date, end_date); return _report_rows(db, current_user, start, end, printer_uuid, unit_name, sector_name)


@router.get("/export.xlsx")
def export_usage_excel(start_date: date | None = None, end_date: date | None = None, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start, end = _resolve_period(start_date, end_date); rows, history = _report_data(db, current_user, start, end, printer_uuid, unit_name, sector_name); company = db.query(Company).filter(Company.id == current_user.company_id).first(); company_name = company.name if company else "Empresa"
    content = build_excel_report(
        company_name,
        start,
        end,
        rows,
        history,
        report_scope=_report_scope_label(rows, printer_uuid, unit_name, sector_name),
        bw_rate=float(company.default_bw_cost_per_page or company.default_cost_per_page or 0) if company else 0.0,
        color_rate=float(company.default_color_cost_per_page or 0) if company else 0.0,
    ); filename = f"printflow-relatorio-{start.isoformat()}-{end.isoformat()}.xlsx"
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/export.pdf")
def export_usage_pdf(start_date: date | None = None, end_date: date | None = None, printer_uuid: str | None = None, unit_name: str | None = None, sector_name: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start, end = _resolve_period(start_date, end_date); rows, _ = _report_data(db, current_user, start, end, printer_uuid, unit_name, sector_name); company = db.query(Company).filter(Company.id == current_user.company_id).first(); company_name = company.name if company else "Empresa"
    content = build_pdf_report(
        company_name,
        start,
        end,
        rows,
        report_scope=_report_scope_label(rows, printer_uuid, unit_name, sector_name),
        bw_rate=float(company.default_bw_cost_per_page or company.default_cost_per_page or 0) if company else 0.0,
        color_rate=float(company.default_color_cost_per_page or 0) if company else 0.0,
    ); filename = f"printflow-relatorio-{start.isoformat()}-{end.isoformat()}.pdf"
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
