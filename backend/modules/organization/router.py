from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.organization.model import (
    CompanySector,
    CompanyUnit,
)
from backend.modules.organization.schema import (
    OrganizationSectorCreate,
    OrganizationSectorResponse,
    OrganizationUnitCreate,
    OrganizationUnitResponse,
)


router = APIRouter(
    prefix="/organization",
    tags=["Organization"],
)


def _clean_name(value: str) -> str:
    return " ".join(value.strip().split())


@router.get(
    "/units",
    response_model=list[OrganizationUnitResponse],
)
def list_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CompanyUnit)
        .filter(
            CompanyUnit.company_id
            == current_user.company_id,
            CompanyUnit.active.is_(True),
        )
        .order_by(CompanyUnit.name.asc())
        .all()
    )


@router.post(
    "/units",
    response_model=OrganizationUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_unit(
    payload: OrganizationUnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = _clean_name(payload.name)

    existing = (
        db.query(CompanyUnit)
        .filter(
            CompanyUnit.company_id
            == current_user.company_id,
            func.lower(CompanyUnit.name)
            == name.lower(),
            CompanyUnit.active.is_(True),
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta unidade ja esta cadastrada.",
        )

    unit = CompanyUnit(
        company_id=current_user.company_id,
        name=name,
    )

    db.add(unit)
    db.commit()
    db.refresh(unit)

    return unit


@router.get(
    "/sectors",
    response_model=list[OrganizationSectorResponse],
)
def list_sectors(
    unit_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(CompanySector)
        .filter(
            CompanySector.company_id
            == current_user.company_id,
            CompanySector.active.is_(True),
        )
    )

    if unit_id is not None:
        query = query.filter(
            CompanySector.unit_id == unit_id
        )

    return (
        query
        .order_by(CompanySector.name.asc())
        .all()
    )


@router.post(
    "/sectors",
    response_model=OrganizationSectorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sector(
    payload: OrganizationSectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    unit = (
        db.query(CompanyUnit)
        .filter(
            CompanyUnit.id == payload.unit_id,
            CompanyUnit.company_id
            == current_user.company_id,
            CompanyUnit.active.is_(True),
        )
        .first()
    )

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade nao encontrada.",
        )

    name = _clean_name(payload.name)

    existing = (
        db.query(CompanySector)
        .filter(
            CompanySector.company_id
            == current_user.company_id,
            CompanySector.unit_id == unit.id,
            func.lower(CompanySector.name)
            == name.lower(),
            CompanySector.active.is_(True),
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este setor ja esta cadastrado nesta unidade.",
        )

    sector = CompanySector(
        company_id=current_user.company_id,
        unit_id=unit.id,
        name=name,
    )

    db.add(sector)
    db.commit()
    db.refresh(sector)

    return sector
