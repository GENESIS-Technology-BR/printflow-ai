from pydantic import ValidationError
import pytest

from backend.modules.organization.model import (
    CompanySector,
    CompanyUnit,
)
from backend.modules.organization.router import router
from backend.modules.organization.schema import (
    OrganizationSectorCreate,
    OrganizationUnitCreate,
)


def test_organization_tables_exist():
    assert CompanyUnit.__tablename__ == "company_units"
    assert CompanySector.__tablename__ == "company_sectors"


def test_units_are_isolated_by_company():
    assert "company_id" in CompanyUnit.__table__.columns


def test_sectors_belong_to_unit_and_company():
    assert "company_id" in CompanySector.__table__.columns
    assert "unit_id" in CompanySector.__table__.columns


def test_unit_schema_accepts_valid_name():
    payload = OrganizationUnitCreate(
        name="Caxias do Sul",
    )
    assert payload.name == "Caxias do Sul"


def test_sector_schema_accepts_unit():
    payload = OrganizationSectorCreate(
        unit_id=1,
        name="Comercial",
    )
    assert payload.unit_id == 1
    assert payload.name == "Comercial"


def test_sector_rejects_invalid_unit():
    with pytest.raises(ValidationError):
        OrganizationSectorCreate(
            unit_id=0,
            name="Comercial",
        )


def test_organization_routes_exist():
    paths = {
        route.path
        for route in router.routes
    }

    assert "/organization/units" in paths
    assert "/organization/sectors" in paths
