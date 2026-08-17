from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PrinterBase(BaseModel):
    ip: str = Field(min_length=7, max_length=45)
    name: str = Field(default="Impressora", min_length=1, max_length=150)
    manufacturer: str | None = None
    model: str | None = None
    status: str = "online"
    source: str = "agent"
    page_count: int | None = None
    serial: str | None = None
    toner_percent: int | None = None
    health_score: int | None = None
    health_status: str | None = None


class PrinterUpsert(PrinterBase):
    agent_token: str = Field(min_length=10)


class PrinterResponse(PrinterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    active: bool
    last_seen: datetime
    created_at: datetime
