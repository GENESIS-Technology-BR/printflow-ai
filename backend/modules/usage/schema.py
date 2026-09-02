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


class UsageReportRow(BaseModel):
    printer_uuid: str
    display_name: str
    ip: str | None = None
    hostname: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial: str | None = None
    unit_name: str | None = None
    sector_name: str | None = None
    first_usage_date: date | None = None
    last_usage_date: date | None = None
    opening_page_count: int | None = None
    closing_page_count: int | None = None
    pages_printed: int = 0
    anomaly_count: int = 0
    last_anomaly_type: str | None = None
    cost_per_page: float = 0.0
    estimated_cost: float = 0.0
    cost_source: str = "company"
