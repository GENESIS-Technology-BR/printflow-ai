from backend.app.database.migrations import PRINTER_COLUMNS
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import PrinterResponse


def test_printer_model_has_relational_organization_links():
    assert "unit_id" in Printer.__table__.columns
    assert "sector_id" in Printer.__table__.columns


def test_printer_response_exposes_organization_ids():
    assert "unit_id" in PrinterResponse.model_fields
    assert "sector_id" in PrinterResponse.model_fields


def test_existing_database_migration_adds_organization_ids():
    assert PRINTER_COLUMNS["unit_id"] == "INTEGER"
    assert PRINTER_COLUMNS["sector_id"] == "INTEGER"
