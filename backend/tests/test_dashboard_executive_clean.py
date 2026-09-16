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

    assert "sap-dashboard-page" in source
    assert "sap-dashboard-v0993" in source
    assert "Visão Geral" in source
    assert "sap-health-strip" in source
    assert "modern-health-gauge" not in source


def test_dashboard_no_longer_duplicates_inventory():
    source = dashboard_source()

    assert "PrinterTable" not in source
    assert "Impressoras monitoradas" not in source
    assert "FleetInsights" not in source
    assert "AlertCenter" not in source


def test_dashboard_has_six_primary_metrics_with_agent():
    source = dashboard_source()

    assert "sap-kpi-grid-six" in source
    assert source.count("sap-kpi-card") >= 6
    assert "Total de páginas" in source
    assert "Impressoras ativas" in source
    assert "Unidades" in source
    assert "Contadores válidos" in source
    assert "Alertas" in source
    assert "Agent" in source
    assert "Última comunicação:" in source


def test_dashboard_commercial_layout_contract():
    source = dashboard_source()

    assert "sap-dashboard-grid-overview" in source
    assert "Distribuição por fabricante" in source
    assert "Status das impressoras" in source
    assert "Equipamentos por unidade" in source
    assert "Impressoras com maior contador" in source
    assert "Parque de impressão saudável" in source
    assert "Alertas prioritários" not in source
    assert "Comunicação</h2>" not in source


def test_dashboard_final_polish():
    source = dashboard_source()

    assert "Última atualização:" in source
    assert "summary.agent.last_seen || summary.generated_at" in source
    assert "share:" in source
    assert "Tudo normal" in source


def test_dashboard_has_honest_empty_state():
    source = dashboard_source()

    assert "hasMonitoringData" in source
    assert "Aguardando dados" in source
    assert "Monitoramento ainda não iniciado." in source
    assert "Instale e conecte o Agent para começar." in source
