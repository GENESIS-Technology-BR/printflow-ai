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


def test_dashboard_uses_sap_fiori_structure():
    source = dashboard_source()

    assert 'className="sap-dashboard-page"' in source
    assert "Visão Geral" in source
    assert "Alertas prioritários" in source
    assert 'className="sap-kpi-grid"' in source
    assert "modern-health-gauge" not in source


def test_dashboard_no_longer_duplicates_inventory():
    source = dashboard_source()

    assert "PrinterTable" not in source
    assert "Impressoras monitoradas" not in source
    assert "FleetInsights" not in source
    assert "AlertCenter" not in source


def test_dashboard_has_five_primary_metrics():
    source = dashboard_source()

    assert source.count('className="sap-kpi-card"') == 5
    assert "Total de páginas" in source
    assert "Impressoras ativas" in source
    assert "Unidades" in source
    assert "Contadores válidos" in source
    assert "Alertas" in source


def test_dashboard_final_polish():
    source = dashboard_source()

    assert "Última atualização:" in source
    assert "summary.agent.last_seen || summary.generated_at" in source
    assert "Distribuição por fabricante" in source
    assert "Impressoras com maior contador" in source
    assert "Status das impressoras" in source


def test_dashboard_has_honest_empty_state():
    source = dashboard_source()

    assert "hasMonitoringData" in source
    assert "Aguardando dados" in source
    assert "Monitoramento ainda não iniciado." in source
    assert "Instale e conecte o Agent para começar." in source
