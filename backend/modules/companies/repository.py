from sqlalchemy.orm import Session

from backend.modules.companies.model import Company
from backend.modules.companies.schema import CompanyCreate


class CompanyRepository:
    """
    Responsável por acessar a tabela companies.
    Nenhuma regra de negócio deve ficar aqui.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, company: CompanyCreate) -> Company:
        db_company = Company(name=company.name)

        self.db.add(db_company)
        self.db.commit()
        self.db.refresh(db_company)

        return db_company
