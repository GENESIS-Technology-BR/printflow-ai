from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_table() -> str:
    return (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "PrinterTable.tsx"
    ).read_text(encoding="utf-8")


def test_frontend_has_search_and_filters():
    table = read_table()

    assert "Buscar por nome, IP, host ou serial" in table
    assert "Todos os status" in table
    assert "Todas as unidades" in table
    assert "Todos os setores" in table


def test_frontend_has_organization_editor():
    table = read_table()

    assert "unit_name" in table
    assert "sector_name" in table
    assert "Salvar localização" in table
