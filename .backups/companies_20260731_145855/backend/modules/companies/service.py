from sqlalchemy.orm import Session

from backend.modules.companies.model import Company
from backend.modules.companies.repository import CompanyRepository
from backend.modules.companies.schema import CompanyCreate


class CompanyService:
    """
    Camada de regras de negócio.
    """

    def __init__(self, db: Session):
        self.repository = CompanyRepository(db)

    def create_company(self, company: CompanyCreate) -> Company:
        return self.repository.create(company)
