from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PrinterBase(BaseModel):
    ip: str = Field(min_length=7, max_length=45)
    name: str = Field(default="Impressora", min_length=1, max_length=150)
    hostname: str | None = Field(default=None, max_length=255)
    manufacturer: str | None = None
    model: str | None = None
    status: str = "online"
    source: str = "agent"
    page_count: int | None = Field(default=None, ge=0)
    page_count_source: str | None = Field(default=None, max_length=60)
    page_count_confidence: int | None = Field(default=None, ge=0, le=100)
    page_count_confirmed: bool = False
    serial: str | None = None
    serial_source: str | None = Field(default=None, max_length=60)
    serial_confidence: int | None = Field(default=None, ge=0, le=100)
    serial_confirmed: bool = False
    toner_percent: int | None = Field(default=None, ge=0, le=100)
    health_score: int | None = Field(default=None, ge=0, le=100)
    health_status: str | None = None


class PrinterUpsert(PrinterBase):
    agent_token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class PrinterResponse(PrinterBase):
    model_config = ConfigDict(from_attributes=True)

    custom_name: str | None = None
    unit_name: str | None = None
    sector_name: str | None = None
    unit_id: int | None = None
    sector_id: int | None = None
    cost_per_page: Decimal | None = None

    id: int
    uuid: str
    active: bool
    last_seen: datetime
    created_at: datetime


class PrinterCustomNameUpdate(BaseModel):
    custom_name: str | None = Field(
        default=None,
        max_length=150,
    )


class PrinterOrganizationUpdate(BaseModel):
    unit_name: str | None = Field(
        default=None,
        max_length=120,
    )

    sector_name: str | None = Field(
        default=None,
        max_length=120,
    )


class PrinterCostUpdate(BaseModel):
    cost_per_page: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        decimal_places=4,
    )


class AgentHeartbeat(BaseModel):
    agent_token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    agent_name: str = Field(min_length=1, max_length=120)
    agent_version: str = Field(min_length=1, max_length=30)
    status: str = Field(pattern="^(starting|running|healthy|error)$")
    error: str | None = Field(default=None, max_length=500)
    inventory_complete: bool = False
    observed_printer_ips: list[str] = Field(default_factory=list, max_length=4096)
