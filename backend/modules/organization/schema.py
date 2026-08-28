from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationUnitCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=120,
    )


class OrganizationUnitResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    uuid: str
    name: str
    active: bool
    created_at: datetime


class OrganizationSectorCreate(BaseModel):
    unit_id: int = Field(gt=0)

    name: str = Field(
        min_length=2,
        max_length=120,
    )


class OrganizationSectorResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    uuid: str
    unit_id: int
    name: str
    active: bool
    created_at: datetime
