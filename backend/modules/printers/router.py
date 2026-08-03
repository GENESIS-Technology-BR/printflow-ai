from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import PrinterResponse, PrinterUpsert

router = APIRouter(prefix="/printers", tags=["Printers"])


@router.get("", response_model=list[PrinterResponse])
def list_printers(db: Session = Depends(get_db)):
    return db.query(Printer).order_by(Printer.id.desc()).all()


@router.post("/agent", response_model=PrinterResponse, status_code=status.HTTP_200_OK)
def receive_agent_data(payload: PrinterUpsert, db: Session = Depends(get_db)):
    printer = db.query(Printer).filter(Printer.ip == payload.ip).first()

    if printer is None:
        printer = Printer(ip=payload.ip)
        db.add(printer)

    printer.name = payload.name
    printer.manufacturer = payload.manufacturer
    printer.model = payload.model
    printer.status = payload.status
    printer.source = payload.source
    printer.page_count = payload.page_count
    printer.active = True
    printer.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(printer)
    return printer
