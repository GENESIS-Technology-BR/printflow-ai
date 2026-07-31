from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.companies.schema import CompanyCreate, CompanyResponse
from backend.modules.companies.service import CompanyService

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
) -> CompanyResponse:
    service = CompanyService(db)

    try:
        return service.create_company(company)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=list[CompanyResponse],
)
def list_companies(
    db: Session = Depends(get_db),
) -> list[CompanyResponse]:
    service = CompanyService(db)
    return service.list_companies()
