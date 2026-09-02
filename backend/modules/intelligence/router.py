from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.dashboard.router import serialize_printer
from backend.modules.printers.model import Printer
from backend.modules.usage.model import PrinterUsageDaily

from .service import build_intelligence


router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["Intelligence"],
)


@router.get("/overview")
def intelligence_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    printers = (
        db.query(Printer)
        .filter(Printer.company_id == current_user.company_id)
        .all()
    )
    start_date = date.today() - timedelta(days=20)
    history = (
        db.query(PrinterUsageDaily)
        .filter(
            PrinterUsageDaily.company_id == current_user.company_id,
            PrinterUsageDaily.usage_date >= start_date,
        )
        .order_by(PrinterUsageDaily.usage_date.asc())
        .all()
    )
    return build_intelligence(
        [serialize_printer(printer) for printer in printers],
        history,
    )
