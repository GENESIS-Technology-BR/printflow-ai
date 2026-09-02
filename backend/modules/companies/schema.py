from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    document: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)
    plan: str | None = None
    default_cost_per_page: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        decimal_places=4,
    )
    active: bool | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    document: str | None
    city: str | None
    state: str | None
    plan: str
    default_cost_per_page: Decimal
    agent_token: str
    active: bool
    created_at: datetime
