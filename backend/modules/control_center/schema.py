from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ControlCenterCompany(BaseModel):
    id: int
    uuid: str
    name: str
    plan: str
    active: bool
    agent_online: bool
    agent_stale: bool
    agent_communication_state: str
    agent_status: str | None
    agent_version: str | None
    agent_last_seen: datetime | None
    onboarding_state: str = "created"
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
    pilots_ready: int
    companies_needing_attention: int
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


class ControlCenterClientUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    active: bool
    created_at: datetime


class ControlCenterClientUserCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ControlCenterClientUserStatusUpdate(BaseModel):
    active: bool


class ControlCenterPreviewSession(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_minutes: int
    company_id: int
    company_uuid: str
    company_name: str
    user_id: int
    user_name: str
    user_email: str
