from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import (
    get_current_user,
)
from backend.modules.auth.model import User
from backend.modules.organization.model import (
    CompanySector,
    CompanyUnit,
)
from backend.modules.organization.schema import (
    OrganizationNameUpdate,
    OrganizationSectorCreate,
    OrganizationSectorResponse,
    OrganizationUnitCreate,
    OrganizationUnitResponse,
)
from backend.modules.printers.model import Printer


router = APIRouter(
    prefix="/organization",
    tags=["Organization"],
)


def _clean_name(value: str) -> str:
    return " ".join(
        value.strip().split()
    )


def _get_unit(
    db: Session,
    company_id: int,
    unit_id: int,
    *,
    active_only: bool = True,
) -> CompanyUnit:
    query = db.query(
        CompanyUnit
    ).filter(
        CompanyUnit.id == unit_id,
        CompanyUnit.company_id
        == company_id,
    )

    if active_only:
        query = query.filter(
            CompanyUnit.active.is_(True)
        )

    unit = query.first()

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade nao encontrada.",
        )

    return unit


def _get_sector(
    db: Session,
    company_id: int,
    sector_id: int,
    *,
    active_only: bool = True,
) -> CompanySector:
    query = db.query(
        CompanySector
    ).filter(
        CompanySector.id == sector_id,
        CompanySector.company_id
        == company_id,
    )

    if active_only:
        query = query.filter(
            CompanySector.active.is_(True)
        )

    sector = query.first()

    if sector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setor nao encontrado.",
        )

    return sector


@router.get(
    "/units",
    response_model=list[
        OrganizationUnitResponse
    ],
)
def list_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return (
        db.query(CompanyUnit)
        .filter(
            CompanyUnit.company_id
            == current_user.company_id,
            CompanyUnit.active.is_(True),
        )
        .order_by(
            CompanyUnit.name.asc()
        )
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
    current_user: User = Depends(
        get_current_user
    ),
):
    name = _clean_name(
        payload.name
    )

    existing = (
        db.query(CompanyUnit)
        .filter(
            CompanyUnit.company_id
            == current_user.company_id,
            func.lower(
                CompanyUnit.name
            ) == name.lower(),
        )
        .first()
    )

    if existing is not None:

        if existing.active:
            raise HTTPException(
                status_code=
                status.HTTP_409_CONFLICT,
                detail=(
                    "Esta unidade ja esta "
                    "cadastrada."
                ),
            )

        existing.active = True
        existing.name = name

        db.commit()
        db.refresh(existing)

        return existing

    unit = CompanyUnit(
        company_id=
        current_user.company_id,
        name=name,
    )

    db.add(unit)
    db.commit()
    db.refresh(unit)

    return unit


@router.patch(
    "/units/{unit_id}",
    response_model=OrganizationUnitResponse,
)
def update_unit(
    unit_id: int,
    payload: OrganizationNameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    unit = _get_unit(
        db,
        current_user.company_id,
        unit_id,
    )

    new_name = _clean_name(
        payload.name
    )

    duplicate = (
        db.query(CompanyUnit)
        .filter(
            CompanyUnit.company_id
            == current_user.company_id,
            CompanyUnit.id != unit.id,
            func.lower(
                CompanyUnit.name
            ) == new_name.lower(),
        )
        .first()
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=
            status.HTTP_409_CONFLICT,
            detail=(
                "Ja existe outra unidade "
                "com este nome."
            ),
        )

    old_name = unit.name

    if old_name != new_name:

        printers = (
            db.query(Printer)
            .filter(
                Printer.company_id
                == current_user.company_id,
                Printer.unit_name
                == old_name,
            )
            .all()
        )

        for printer in printers:
            printer.unit_name = (
                new_name
            )

        unit.name = new_name

    db.commit()
    db.refresh(unit)

    return unit


@router.delete(
    "/units/{unit_id}",
    response_model=OrganizationUnitResponse,
)
def deactivate_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    unit = _get_unit(
        db,
        current_user.company_id,
        unit_id,
    )

    active_sectors = (
        db.query(CompanySector)
        .filter(
            CompanySector.company_id
            == current_user.company_id,
            CompanySector.unit_id
            == unit.id,
            CompanySector.active.is_(True),
        )
        .count()
    )

    printers = (
        db.query(Printer)
        .filter(
            Printer.company_id
            == current_user.company_id,
            Printer.unit_name
            == unit.name,
        )
        .count()
    )

    if active_sectors or printers:

        details = []

        if active_sectors:
            details.append(
                f"{active_sectors} setor(es)"
            )

        if printers:
            details.append(
                f"{printers} impressora(s)"
            )

        raise HTTPException(
            status_code=
            status.HTTP_409_CONFLICT,
            detail=(
                "Nao e possivel desativar "
                "esta unidade enquanto ela "
                "possuir "
                + " e ".join(details)
                + " vinculados."
            ),
        )

    unit.active = False

    db.commit()
    db.refresh(unit)

    return unit


@router.get(
    "/sectors",
    response_model=list[
        OrganizationSectorResponse
    ],
)
def list_sectors(
    unit_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
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
            CompanySector.unit_id
            == unit_id
        )

    return (
        query
        .order_by(
            CompanySector.name.asc()
        )
        .all()
    )


@router.post(
    "/sectors",
    response_model=
    OrganizationSectorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sector(
    payload: OrganizationSectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    unit = _get_unit(
        db,
        current_user.company_id,
        payload.unit_id,
    )

    name = _clean_name(
        payload.name
    )

    existing = (
        db.query(CompanySector)
        .filter(
            CompanySector.company_id
            == current_user.company_id,
            CompanySector.unit_id
            == unit.id,
            func.lower(
                CompanySector.name
            ) == name.lower(),
        )
        .first()
    )

    if existing is not None:

        if existing.active:
            raise HTTPException(
                status_code=
                status.HTTP_409_CONFLICT,
                detail=(
                    "Este setor ja esta "
                    "cadastrado nesta unidade."
                ),
            )

        existing.active = True
        existing.name = name

        db.commit()
        db.refresh(existing)

        return existing

    sector = CompanySector(
        company_id=
        current_user.company_id,
        unit_id=unit.id,
        name=name,
    )

    db.add(sector)
    db.commit()
    db.refresh(sector)

    return sector


@router.patch(
    "/sectors/{sector_id}",
    response_model=
    OrganizationSectorResponse,
)
def update_sector(
    sector_id: int,
    payload: OrganizationNameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    sector = _get_sector(
        db,
        current_user.company_id,
        sector_id,
    )

    unit = _get_unit(
        db,
        current_user.company_id,
        sector.unit_id,
    )

    new_name = _clean_name(
        payload.name
    )

    duplicate = (
        db.query(CompanySector)
        .filter(
            CompanySector.company_id
            == current_user.company_id,
            CompanySector.unit_id
            == unit.id,
            CompanySector.id
            != sector.id,
            func.lower(
                CompanySector.name
            ) == new_name.lower(),
        )
        .first()
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=
            status.HTTP_409_CONFLICT,
            detail=(
                "Ja existe outro setor "
                "com este nome nesta unidade."
            ),
        )

    old_name = sector.name

    if old_name != new_name:

        printers = (
            db.query(Printer)
            .filter(
                Printer.company_id
                == current_user.company_id,
                Printer.unit_name
                == unit.name,
                Printer.sector_name
                == old_name,
            )
            .all()
        )

        for printer in printers:
            printer.sector_name = (
                new_name
            )

        sector.name = new_name

    db.commit()
    db.refresh(sector)

    return sector


@router.delete(
    "/sectors/{sector_id}",
    response_model=
    OrganizationSectorResponse,
)
def deactivate_sector(
    sector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    sector = _get_sector(
        db,
        current_user.company_id,
        sector_id,
    )

    unit = _get_unit(
        db,
        current_user.company_id,
        sector.unit_id,
    )

    printers = (
        db.query(Printer)
        .filter(
            Printer.company_id
            == current_user.company_id,
            Printer.unit_name
            == unit.name,
            Printer.sector_name
            == sector.name,
        )
        .count()
    )

    if printers:
        raise HTTPException(
            status_code=
            status.HTTP_409_CONFLICT,
            detail=(
                "Nao e possivel desativar "
                "este setor enquanto ele "
                f"possuir {printers} "
                "impressora(s) vinculada(s)."
            ),
        )

    sector.active = False

    db.commit()
    db.refresh(sector)

    return sector
