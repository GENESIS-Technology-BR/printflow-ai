"""
Registro central dos Models SQLAlchemy do PRINTFLOW.

Este módulo deve ser importado antes de Base.metadata.create_all()
para que todas as tabelas e relacionamentos sejam conhecidos.
"""

from backend.modules.companies.model import Company
from backend.modules.auth.model import User
from backend.modules.partners.model import Partner, PartnerMembership
from backend.modules.printers.model import Printer
from backend.modules.alerts.model import OperationalAlert
from backend.modules.organization.model import (
    CompanySector,
    CompanyUnit,
)
from backend.modules.usage.model import PrinterUsageDaily


__all__ = [
    "Company",
    "User",
    "Partner",
    "PartnerMembership",
    "Printer",
    "OperationalAlert",
    "CompanyUnit",
    "CompanySector",
    "PrinterUsageDaily",
]
