from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.modules.dashboard.router import (
    serialize_printer,
)

from backend.modules.printers.model import (
    Printer,
)

from backend.modules.printers.schema import (
    PrinterOrganizationUpdate,
)


def test_printer_has_organization_fields():
    assert "unit_name" in Printer.__table__.columns
    assert "sector_name" in Printer.__table__.columns


def test_organization_accepts_values():
    payload = PrinterOrganizationUpdate(
        unit_name="Caxias do Sul",
        sector_name="Comercial",
    )

    assert payload.unit_name == "Caxias do Sul"
    assert payload.sector_name == "Comercial"


def test_organization_can_be_cleared():
    payload = PrinterOrganizationUpdate(
        unit_name=None,
        sector_name=None,
    )

    assert payload.unit_name is None
    assert payload.sector_name is None


def test_organization_rejects_oversized_value():
    with pytest.raises(ValidationError):
        PrinterOrganizationUpdate(
            unit_name="X" * 121,
        )


def test_dashboard_exposes_organization():
    printer = SimpleNamespace(
        id=1,
        uuid="printer-1",
        ip="10.2.0.101",
        name="Kyocera ECOSYS M3145idn",
        hostname="KMCBA271",
        custom_name="Comercial",
        unit_name="Caxias do Sul",
        sector_name="Comercial",
        status="online",
        active=True,
        page_count=81373,
        last_seen=None,
        created_at=None,
    )

    result = serialize_printer(
        printer,
    )

    assert result["unit_name"] == "Caxias do Sul"
    assert result["sector_name"] == "Comercial"
