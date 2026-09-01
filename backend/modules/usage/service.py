from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.modules.printers.model import Printer

from .model import PrinterUsageDaily


@dataclass(frozen=True)
class CounterDelta:
    pages: int
    anomaly_type: str | None = None


def calculate_counter_delta(
    previous_count: int,
    current_count: int,
) -> CounterDelta:
    """Calcula consumo sem permitir producao negativa."""
    if previous_count < 0 or current_count < 0:
        raise ValueError("Contadores nao podem ser negativos.")

    if current_count < previous_count:
        return CounterDelta(
            pages=0,
            anomaly_type="counter_decrease",
        )

    return CounterDelta(
        pages=current_count - previous_count,
    )


def reporting_date(
    observed_at: datetime | None = None,
) -> date:
    """Converte UTC para a data operacional usada nos relatorios."""
    moment = observed_at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    report_tz = timezone(
        timedelta(hours=settings.report_utc_offset_hours)
    )
    return moment.astimezone(report_tz).date()


def record_daily_printer_usage(
    db: Session,
    printer: Printer,
    observed_at: datetime | None = None,
) -> PrinterUsageDaily | None:
    """Consolida uma unica linha diaria por impressora.

    O Agent pode reportar a cada poucos minutos, mas o banco mantem apenas
    um registro por impressora/dia. O volume e acumulado por deltas de
    contador. Quedas de contador nunca geram consumo negativo: sao marcadas
    como anomalia e a leitura menor vira a nova referencia do segmento.
    """
    if (
        printer.id is None
        or printer.company_id is None
        or printer.page_count is None
        or printer.page_count < 0
    ):
        return None

    moment = observed_at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)

    day = reporting_date(moment)
    current_count = int(printer.page_count)

    usage = (
        db.query(PrinterUsageDaily)
        .filter(
            PrinterUsageDaily.company_id == printer.company_id,
            PrinterUsageDaily.printer_id == printer.id,
            PrinterUsageDaily.usage_date == day,
        )
        .first()
    )

    if usage is None:
        previous = (
            db.query(PrinterUsageDaily)
            .filter(
                PrinterUsageDaily.company_id == printer.company_id,
                PrinterUsageDaily.printer_id == printer.id,
                PrinterUsageDaily.usage_date < day,
            )
            .order_by(PrinterUsageDaily.usage_date.desc())
            .first()
        )

        opening_count = current_count
        pages_printed = 0
        anomaly_count = 0
        last_anomaly_type = None

        if previous is not None:
            delta = calculate_counter_delta(
                previous.closing_page_count,
                current_count,
            )
            if delta.anomaly_type is None:
                opening_count = previous.closing_page_count
                pages_printed = delta.pages
            else:
                anomaly_count = 1
                last_anomaly_type = delta.anomaly_type

        usage = PrinterUsageDaily(
            company_id=printer.company_id,
            printer_id=printer.id,
            usage_date=day,
            printer_uuid=printer.uuid,
            ip=printer.ip,
            name=printer.name,
            custom_name=printer.custom_name,
            hostname=printer.hostname,
            manufacturer=printer.manufacturer,
            model=printer.model,
            serial=printer.serial,
            unit_name=printer.unit_name,
            sector_name=printer.sector_name,
            opening_page_count=opening_count,
            closing_page_count=current_count,
            pages_printed=pages_printed,
            anomaly_count=anomaly_count,
            last_anomaly_type=last_anomaly_type,
            first_seen_at=moment,
            last_seen_at=moment,
            created_at=moment,
            updated_at=moment,
        )
        db.add(usage)
        return usage

    delta = calculate_counter_delta(
        usage.closing_page_count,
        current_count,
    )

    if delta.anomaly_type is None:
        usage.pages_printed += delta.pages
    else:
        usage.anomaly_count += 1
        usage.last_anomaly_type = delta.anomaly_type

    usage.closing_page_count = current_count
    usage.last_seen_at = moment
    usage.updated_at = moment

    return usage