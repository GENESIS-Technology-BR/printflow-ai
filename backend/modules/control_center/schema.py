from datetime import datetime

from pydantic import BaseModel


class ControlCenterCompany(BaseModel):
    id: int
    uuid: str
    name: str
    plan: str
    active: bool
    agent_online: bool
    agent_status: str | None
    agent_version: str | None
    agent_last_seen: datetime | None
    active_printers: int
    online_printers: int
    offline_printers: int
    alerts: int


class ControlCenterOverview(BaseModel):
    generated_at: datetime
    companies_total: int
    companies_active: int
    agents_online: int
    active_printers: int
    open_alerts: int
    companies: list[ControlCenterCompany]
