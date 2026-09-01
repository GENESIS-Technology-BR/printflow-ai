from datetime import date, datetime

from pydantic import BaseModel


class DailyUsageResponse(BaseModel):
    usage_date: date
    printer_uuid: str
    ip: str
    name: str
    custom_name: str | None = None
    hostname: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial: str | None = None
    unit_name: str | None = None
    sector_name: str | None = None
    opening_page_count: int
    closing_page_count: int
    pages_printed: int
    anomaly_count: int
    last_anomaly_type: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime