from __future__ import annotations

from datetime import date

from backend.modules.usage.reporting import build_excel_report, build_pdf_report
from backend.modules.usage.router import router
from config.settings import AgentSettings


def test_release_candidate_agent_defaults(monkeypatch) -> None:
    monkeypatch.delenv("PRINTFLOW_SCAN_INTERVAL", raising=False)
    monkeypatch.delenv("PRINTFLOW_CYCLE_SLA_SECONDS", raising=False)

    settings = AgentSettings.load()

    assert settings.scan_interval_seconds == 300
    assert settings.cycle_sla_seconds == 90


def test_release_candidate_usage_routes_are_exposed() -> None:
    paths = {route.path for route in router.routes}

    assert "/usage/report" in paths
    assert "/usage/export.xlsx" in paths
    assert "/usage/export.pdf" in paths


def test_release_candidate_exports_generate_real_files() -> None:
    rows = [
        {
            "printer_uuid": "rc-printer-001",
            "display_name": "Impressora Homologacao",
            "ip": "10.2.0.124",
            "hostname": "PRN-HOMOLOG",
            "manufacturer": "HP",
            "model": "Laser MFP 432",
            "serial": "RC001",
            "unit_name": "Matriz",
            "sector_name": "TI",
            "first_usage_date": date(2026, 9, 8),
            "last_usage_date": date(2026, 9, 9),
            "opening_page_count": 27300,
            "closing_page_count": 27344,
            "pages_printed": 44,
            "anomaly_count": 0,
            "last_anomaly_type": None,
            "cost_per_page": 0.10,
            "estimated_cost": 4.40,
            "cost_source": "company",
        }
    ]

    excel = build_excel_report(
        "Empresa Homologacao",
        date(2026, 9, 8),
        date(2026, 9, 9),
        rows,
        [],
    )
    pdf = build_pdf_report(
        "Empresa Homologacao",
        date(2026, 9, 8),
        date(2026, 9, 9),
        rows,
    )

    assert excel.startswith(b"PK")
    assert pdf.startswith(b"%PDF")
    assert len(excel) > 1000
    assert len(pdf) > 1000
