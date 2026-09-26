from datetime import date
from io import BytesIO
from types import SimpleNamespace

from openpyxl import load_workbook

from backend.modules.usage.router import _fixed_cost_for_period
from backend.modules.usage.reporting import (
    build_excel_report,
    build_pdf_report,
    consolidate_usage,
)


SAMPLE_ROWS = [
    {
        "printer_uuid": "printer-001",
        "display_name": "Impressora Financeiro",
        "ip": "10.0.0.25",
        "hostname": "PRN-FIN-01",
        "manufacturer": "HP",
        "model": "LaserJet",
        "serial": "SN001",
        "unit_name": "Matriz",
        "sector_name": "Financeiro",
        "first_usage_date": date(2026, 9, 1),
        "last_usage_date": date(2026, 9, 2),
        "opening_page_count": 1000,
        "closing_page_count": 1125,
        "pages_printed": 125,
        "anomaly_count": 0,
        "last_anomaly_type": None,
        "cost_per_page": 0.12,
        "estimated_cost": 15.0,
        "cost_source": "company",
    }
]


def test_excel_report_generates_valid_workbook():
    content = build_excel_report(
        "Empresa Teste",
        date(2026, 9, 1),
        date(2026, 9, 2),
        SAMPLE_ROWS,
        [],
    )

    assert content.startswith(b"PK")

    workbook = load_workbook(BytesIO(content), read_only=True)
    assert workbook.sheetnames == ["Resumo", "Histórico diário"]

    summary = workbook["Resumo"]
    assert summary["A1"].value == "Printflow - Relatório de Impressão"
    assert summary["A2"].value == (
        "Empresa: Empresa Teste  —  Período: 01/09/2026 a 02/09/2026"
    )
    assert summary["A8"].value == "Impressora Financeiro"
    assert summary["K8"].value == 125
    assert summary["L8"].value == 0.12
    assert summary["M8"].value == 15.0


def test_pdf_report_generates_valid_pdf():
    content = build_pdf_report(
        "Empresa Teste",
        date(2026, 9, 1),
        date(2026, 9, 2),
        SAMPLE_ROWS,
    )

    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_consolidated_report_keeps_active_printer_without_history() -> None:
    printer = SimpleNamespace(
        uuid="printer-002",
        custom_name="Impressora RH",
        hostname="PRN-RH-01",
        name="HP RH",
        ip="10.0.0.30",
        manufacturer="HP",
        model="LaserJet Pro",
        serial="SN002",
        unit_name="Matriz",
        sector_name="RH",
        page_count=500,
        cost_per_page=None,
    )

    rows = consolidate_usage([], [printer], default_cost_per_page=0.10)

    assert len(rows) == 1
    assert rows[0]["printer_uuid"] == "printer-002"
    assert rows[0]["pages_printed"] == 0
    assert rows[0]["opening_page_count"] == 500
    assert rows[0]["closing_page_count"] == 500
    assert rows[0]["cost_per_page"] == 0.10
    assert rows[0]["estimated_cost"] == 0.0


def test_printer_specific_cost_overrides_company_default() -> None:
    printer = SimpleNamespace(
        uuid="printer-003",
        custom_name="Impressora Diretoria",
        hostname="PRN-DIR-01",
        name="HP Diretoria",
        ip="10.0.0.40",
        manufacturer="HP",
        model="LaserJet Enterprise",
        serial="SN003",
        unit_name="Matriz",
        sector_name="Diretoria",
        page_count=800,
        cost_per_page=0.25,
    )

    rows = consolidate_usage([], [printer], default_cost_per_page=0.10)

    assert rows[0]["cost_per_page"] == 0.25
    assert rows[0]["cost_source"] == "printer"


def test_excel_report_does_not_display_scope_line() -> None:
    content = build_excel_report(
        "Empresa Teste",
        date(2026, 9, 1),
        date(2026, 9, 2),
        SAMPLE_ROWS,
        [],
        report_scope="Unidade: Matriz · Setor: Financeiro",
    )

    workbook = load_workbook(BytesIO(content), read_only=True)
    summary = workbook["Resumo"]
    visible_top = " ".join(
        str(summary.cell(row=row, column=column).value or "")
        for row in range(1, 8)
        for column in range(1, 14)
    )
    assert "Escopo" not in visible_top


def test_pdf_report_accepts_filtered_scope_and_technical_identity() -> None:
    content = build_pdf_report(
        "Empresa Teste",
        date(2026, 9, 1),
        date(2026, 9, 2),
        SAMPLE_ROWS,
        report_scope="Impressora: Impressora Financeiro",
    )

    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_fixed_monthly_contract_charges_full_month_without_daily_proration() -> None:
    assert _fixed_cost_for_period(
        1500.0,
        date(2026, 9, 1),
        date(2026, 9, 30),
    ) == 1500.0


def test_fixed_monthly_contract_counts_each_calendar_month_in_period() -> None:
    assert _fixed_cost_for_period(
        1500.0,
        date(2026, 8, 20),
        date(2026, 9, 18),
    ) == 3000.0


def test_consolidated_report_sorts_ipv4_numerically() -> None:
    def printer(uuid: str, ip: str):
        return SimpleNamespace(
            uuid=uuid, custom_name=uuid, hostname=None, name=uuid, ip=ip,
            manufacturer="HP", model="LaserJet", serial=None,
            unit_name=None, sector_name=None, page_count=0, cost_per_page=None,
        )

    rows = consolidate_usage(
        [],
        [
            printer("p100", "10.2.0.100"),
            printer("p9", "10.2.0.9"),
            printer("p10", "10.2.0.10"),
            printer("p124", "10.2.0.124"),
        ],
        default_cost_per_page=0.05,
    )

    assert [row["ip"] for row in rows] == [
        "10.2.0.9",
        "10.2.0.10",
        "10.2.0.100",
        "10.2.0.124",
    ]


def test_fixed_monthly_printer_never_uses_page_counter_for_cost() -> None:
    printer = SimpleNamespace(
        uuid="canon-fixed", custom_name="PLOTTER CANON IPF-770",
        hostname=None, name="Canon iPF-770", ip="10.2.0.109",
        manufacturer="Canon", model="iPF-770", serial="BACG3815",
        unit_name=None, sector_name=None, page_count=99999,
        cost_per_page=None, cost_model="fixed_monthly", fixed_monthly_cost=1500.0,
    )

    rows = consolidate_usage([], [printer], default_cost_per_page=0.05)

    assert rows[0]["cost_source"] == "fixed_monthly"
    assert rows[0]["cost_per_page"] == 0.0
    assert rows[0]["estimated_cost"] == 1500.0
    assert rows[0]["fixed_monthly_cost"] == 1500.0
