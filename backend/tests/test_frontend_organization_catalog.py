from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (
        ROOT / path
    ).read_text(encoding="utf-8")


def test_printer_screen_can_create_units():
    table = read(
        "frontend/src/components/PrinterTable.tsx"
    )

    assert "Nova unidade" in table
    assert "+ Adicionar unidade" in table
    assert "createOrganizationUnit" in table


def test_printer_screen_can_create_sectors():
    table = read(
        "frontend/src/components/PrinterTable.tsx"
    )

    assert "Novo setor" in table
    assert "+ Adicionar setor" in table
    assert "createOrganizationSector" in table


def test_printer_uses_catalog_selectors():
    table = read(
        "frontend/src/components/PrinterTable.tsx"
    )

    assert "Sem unidade" in table
    assert "Sem setor" in table
    assert "Salvar localização" in table


def test_frontend_api_has_catalog():
    api = read(
        "frontend/src/services/api.ts"
    )

    assert "getOrganizationUnits" in api
    assert "getOrganizationSectors" in api
    assert "/api/v1/organization/units" in api
    assert "/api/v1/organization/sectors" in api


def test_dashboard_uses_master_unit_count():
    dashboard = read(
        "frontend/src/components/Dashboard.tsx"
    )

    assert "getOrganizationUnits" in dashboard
    assert "organizationUnits.length" in dashboard
