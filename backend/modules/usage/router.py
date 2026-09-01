from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer

from .model import PrinterUsageDaily
from .reporting import build_excel_report, build_pdf_report, consolidate_usage
from .schema import DailyUsageResponse, UsageReportRow
from .service import reporting_date


router = APIRouter(prefix="/usage", tags=["Usage"])


def _resolve_period(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    report_today = reporting_date()
    end = end_date or report_today
    start = start_date or (end - timedelta(days=30))

    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Data inicial nao pode ser maior que a final.",
        )

    if (end - start).days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O periodo maximo por consulta e de 366 dias.",
        )

    return start, end


def _usage_query(
    db: Session,
    company_id: int,
    start: date,
    end: date,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
):
    query = db.query(PrinterUsageDaily).filter(
        PrinterUsageDaily.company_id == company_id,
        PrinterUsageDaily.usage_date >= start,
        PrinterUsageDaily.usage_date <= end,
    )
    if printer_uuid:
        query = query.filter(PrinterUsageDaily.printer_uuid == printer_uuid)
    if unit_name:
        query = query.filter(PrinterUsageDaily.unit_name == unit_name)
    if sector_name:
        query = query.filter(PrinterUsageDaily.sector_name == sector_name)

    return query.order_by(
        PrinterUsageDaily.usage_date.asc(),
        PrinterUsageDaily.printer_id.asc(),
    )


def _current_printers(
    db: Session,
    company_id: int,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
) -> list[Printer]:
    query = db.query(Printer).filter(
        Printer.company_id == company_id,
        Printer.active.is_(True),
    )
    if printer_uuid:
        query = query.filter(Printer.uuid == printer_uuid)
    if unit_name:
        query = query.filter(Printer.unit_name == unit_name)
    if sector_name:
        query = query.filter(Printer.sector_name == sector_name)
    return query.order_by(Printer.name.asc()).all()


def _report_rows(
    db: Session,
    current_user: User,
    start: date,
    end: date,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
) -> list[dict]:
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
    return consolidate_usage(history, printers)


@router.get("/daily", response_model=list[DailyUsageResponse])
def list_daily_usage(
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start, end = _resolve_period(start_date, end_date)
    rows = _usage_query(
        db,
        current_user.company_id,
        start,
        end,
        printer_uuid,
        unit_name,
        sector_name,
    ).all()

    return [
        DailyUsageResponse(
            usage_date=usage.usage_date,
            printer_uuid=usage.printer_uuid,
            ip=usage.ip,
            name=usage.name,
            custom_name=usage.custom_name,
            hostname=usage.hostname,
            manufacturer=usage.manufacturer,
            model=usage.model,
            serial=usage.serial,
            unit_name=usage.unit_name,
            sector_name=usage.sector_name,
            opening_page_count=usage.opening_page_count,
            closing_page_count=usage.closing_page_count,
            pages_printed=usage.pages_printed,
            anomaly_count=usage.anomaly_count,
            last_anomaly_type=usage.last_anomaly_type,
            first_seen_at=usage.first_seen_at,
            last_seen_at=usage.last_seen_at,
        )
        for usage in rows
    ]


@router.get("/report", response_model=list[UsageReportRow])
def usage_report(
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start, end = _resolve_period(start_date, end_date)
    return _report_rows(
        db, current_user, start, end,
        printer_uuid, unit_name, sector_name,
    )


@router.get("/export.xlsx")
def export_usage_excel(
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start, end = _resolve_period(start_date, end_date)
    rows = _report_rows(
        db, current_user, start, end,
        printer_uuid, unit_name, sector_name,
    )
    history = _usage_query(
        db, current_user.company_id, start, end,
        printer_uuid, unit_name, sector_name,
    ).all()
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company_name = company.name if company else "Empresa"
    content = build_excel_report(company_name, start, end, rows, history)
    filename = f"printflow-relatorio-{start.isoformat()}-{end.isoformat()}.xlsx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.pdf")
def export_usage_pdf(
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    unit_name: str | None = None,
    sector_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start, end = _resolve_period(start_date, end_date)
    rows = _report_rows(
        db, current_user, start, end,
        printer_uuid, unit_name, sector_name,
    )
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company_name = company.name if company else "Empresa"
    content = build_pdf_report(company_name, start, end, rows)
    filename = f"printflow-relatorio-{start.isoformat()}-{end.isoformat()}.pdf"

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
