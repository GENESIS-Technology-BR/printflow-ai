from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


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



class ControlCenterClientCreate(BaseModel):
    company_name: str = Field(
        min_length=2,
        max_length=180,
    )
    responsible_name: str = Field(
        min_length=3,
        max_length=120,
    )
    email: EmailStr


class ControlCenterClientCreated(BaseModel):
    company_id: int
    company_uuid: str
    company_name: str
    plan: str
    user_id: int
    responsible_name: str
    email: str
    temporary_password: str
    agent_token: str
