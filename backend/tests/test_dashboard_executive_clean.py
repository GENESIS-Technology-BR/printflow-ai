from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def dashboard_source() -> str:
    return (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "Dashboard.tsx"
    ).read_text(encoding="utf-8")


def test_dashboard_is_executive_clean():
    source = dashboard_source()

    assert "Saúde do parque" in source
    assert "Alertas prioritários" in source
    assert "clean-summary-strip" in source
    assert "modern-health-gauge" not in source


def test_dashboard_no_longer_duplicates_inventory():
    source = dashboard_source()

    assert "PrinterTable" not in source
    assert "Impressoras monitoradas" not in source
    assert "FleetInsights" not in source
    assert "AlertCenter" not in source


def test_dashboard_has_four_primary_metrics():
    source = dashboard_source()

    assert source.count("<MetricCard") == 4
