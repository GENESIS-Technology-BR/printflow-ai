from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User

from .model import PrinterUsageDaily
from .schema import DailyUsageResponse
from .service import reporting_date


router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/daily", response_model=list[DailyUsageResponse])
def list_daily_usage(
    start_date: date | None = None,
    end_date: date | None = None,
    printer_uuid: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Entrega a base diaria que alimentara Excel/PDF na proxima etapa."""
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

    query = db.query(PrinterUsageDaily).filter(
        PrinterUsageDaily.company_id == current_user.company_id,
        PrinterUsageDaily.usage_date >= start,
        PrinterUsageDaily.usage_date <= end,
    )

    if printer_uuid:
        query = query.filter(
            PrinterUsageDaily.printer_uuid == printer_uuid
        )

    rows = (
        query.order_by(
            PrinterUsageDaily.usage_date.desc(),
            PrinterUsageDaily.printer_id.asc(),
        )
        .all()
    )

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