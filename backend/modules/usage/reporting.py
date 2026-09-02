from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Iterable

from backend.modules.printers.model import Printer

from .model import PrinterUsageDaily


def _looks_like_opaque_hex(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    return len(text) >= 48 and all(char in "0123456789abcdef" for char in text)


def _clean_identity(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text or _looks_like_opaque_hex(text):
        return None
    return text


def _display_name(
    custom_name: str | None,
    hostname: str | None,
    name: str | None,
    ip: str | None,
) -> str:
    if custom_name and custom_name.strip():
        return custom_name.strip()

    for candidate in (hostname, name):
        cleaned = _clean_identity(candidate)
        if cleaned:
            return cleaned

    return ip or "Impressora sem nome"


def consolidate_usage(
    history: Iterable[PrinterUsageDaily],
    printers: Iterable[Printer] = (),
) -> list[dict]:
    groups: dict[str, dict] = {}
    ordered_history = sorted(
        history,
        key=lambda row: (
            row.printer_uuid,
            row.usage_date,
            row.id or 0,
        ),
    )

    for usage in ordered_history:
        item = groups.get(usage.printer_uuid)
        if item is None:
            item = {
                "printer_uuid": usage.printer_uuid,
                "display_name": _display_name(
                    usage.custom_name,
                    usage.hostname,
                    usage.name,
                    usage.ip,
                ),
                "ip": usage.ip,
                "hostname": _clean_identity(usage.hostname),
                "manufacturer": usage.manufacturer,
                "model": usage.model,
                "serial": _clean_identity(usage.serial),
                "unit_name": usage.unit_name,
                "sector_name": usage.sector_name,
                "first_usage_date": usage.usage_date,
                "last_usage_date": usage.usage_date,
                "opening_page_count": usage.opening_page_count,
                "closing_page_count": usage.closing_page_count,
                "pages_printed": 0,
                "anomaly_count": 0,
                "last_anomaly_type": None,
            }
            groups[usage.printer_uuid] = item

        item["pages_printed"] += usage.pages_printed
        item["anomaly_count"] += usage.anomaly_count
        item["last_usage_date"] = usage.usage_date
        item["closing_page_count"] = usage.closing_page_count
        item["display_name"] = _display_name(
            usage.custom_name,
            usage.hostname,
            usage.name,
            usage.ip,
        )
        item["ip"] = usage.ip
        item["hostname"] = _clean_identity(usage.hostname)
        item["manufacturer"] = usage.manufacturer
        item["model"] = usage.model
        item["serial"] = _clean_identity(usage.serial)
        item["unit_name"] = usage.unit_name
        item["sector_name"] = usage.sector_name

        if usage.last_anomaly_type:
            item["last_anomaly_type"] = usage.last_anomaly_type

    for printer in printers:
        if printer.uuid in groups:
            continue

        page_count = (
            int(printer.page_count)
            if printer.page_count is not None
            else None
        )
        groups[printer.uuid] = {
            "printer_uuid": printer.uuid,
            "display_name": _display_name(
                printer.custom_name,
                printer.hostname,
                printer.name,
                printer.ip,
            ),
            "ip": printer.ip,
            "hostname": _clean_identity(printer.hostname),
            "manufacturer": printer.manufacturer,
            "model": printer.model,
            "serial": _clean_identity(printer.serial),
            "unit_name": printer.unit_name,
            "sector_name": printer.sector_name,
            "first_usage_date": None,
            "last_usage_date": None,
            "opening_page_count": page_count,
            "closing_page_count": page_count,
            "pages_printed": 0,
            "anomaly_count": 0,
            "last_anomaly_type": None,
        }

    return sorted(
        groups.values(),
        key=lambda item: (
            item["unit_name"] or "",
            item["sector_name"] or "",
            item["display_name"].lower(),
        ),
    )


def build_excel_report(
    company_name: str,
    start: date,
    end: date,
    rows: list[dict],
    history: Iterable[PrinterUsageDaily],
) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Resumo"

    sheet["A1"] = "PRINTFLOW AI - Relatorio de Impressao"
    sheet["A1"].font = Font(size=16, bold=True)
    sheet["A2"] = f"Empresa: {company_name}"
    sheet["A3"] = (
        f"Periodo: {start.strftime('%d/%m/%Y')} "
        f"a {end.strftime('%d/%m/%Y')}"
    )

    headers = [
        "Impressora", "IP", "Hostname", "Fabricante", "Modelo", "Serial",
        "Unidade", "Setor", "Primeira leitura", "Ultima leitura",
        "Contador inicial", "Contador final", "Impressoes no periodo", "Anomalias",
    ]
    header_row = 5

    for column, label in enumerate(headers, start=1):
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="12344D")
        cell.alignment = Alignment(horizontal="center")

    for row_index, item in enumerate(rows, start=header_row + 1):
        values = [
            item["display_name"], item["ip"] or "", item["hostname"] or "",
            item["manufacturer"] or "", item["model"] or "", item["serial"] or "",
            item["unit_name"] or "", item["sector_name"] or "",
            item["first_usage_date"].strftime("%d/%m/%Y") if item["first_usage_date"] else "Sem historico",
            item["last_usage_date"].strftime("%d/%m/%Y") if item["last_usage_date"] else "Sem historico",
            item["opening_page_count"], item["closing_page_count"],
            item["pages_printed"], item["anomaly_count"],
        ]
        for column, value in enumerate(values, start=1):
            sheet.cell(row=row_index, column=column, value=value)

    sheet.freeze_panes = "A6"
    sheet.auto_filter.ref = f"A{header_row}:N{max(header_row, header_row + len(rows))}"
    widths = [30, 16, 24, 18, 28, 22, 20, 20, 16, 16, 16, 16, 20, 12]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    detail = workbook.create_sheet("Historico diario")
    detail_headers = [
        "Data", "Impressora", "IP", "Unidade", "Setor",
        "Contador abertura", "Contador fechamento", "Impressoes", "Anomalias",
    ]
    for column, label in enumerate(detail_headers, start=1):
        cell = detail.cell(row=1, column=column, value=label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="12344D")

    for row_index, usage in enumerate(
        sorted(history, key=lambda item: (item.usage_date, item.printer_uuid)),
        start=2,
    ):
        values = [
            usage.usage_date.strftime("%d/%m/%Y"),
            _display_name(usage.custom_name, usage.hostname, usage.name, usage.ip),
            usage.ip, usage.unit_name or "", usage.sector_name or "",
            usage.opening_page_count, usage.closing_page_count,
            usage.pages_printed, usage.anomaly_count,
        ]
        for column, value in enumerate(values, start=1):
            detail.cell(row=row_index, column=column, value=value)

    detail.freeze_panes = "A2"
    detail.auto_filter.ref = f"A1:I{max(1, detail.max_row)}"
    for index, width in enumerate([14, 30, 16, 20, 20, 18, 18, 14, 12], start=1):
        detail.column_dimensions[get_column_letter(index)].width = width

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_pdf_report(
    company_name: str,
    start: date,
    end: date,
    rows: list[dict],
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="PRINTFLOW AI - Relatorio de Impressao",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("PRINTFLOW AI - Relatorio de Impressao", styles["Title"]),
        Paragraph(f"<b>Empresa:</b> {company_name}", styles["Normal"]),
        Paragraph(
            f"<b>Periodo:</b> {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]

    table_data = [[
        "Impressora", "IP", "Unidade / Setor", "Modelo",
        "Inicial", "Final", "Impressoes",
    ]]
    for item in rows:
        organization = " / ".join(
            part for part in (item["unit_name"], item["sector_name"]) if part
        ) or "-"
        model = " ".join(
            part for part in (item["manufacturer"], item["model"]) if part
        ) or "-"
        table_data.append([
            item["display_name"], item["ip"] or "-", organization, model,
            str(item["opening_page_count"]) if item["opening_page_count"] is not None else "-",
            str(item["closing_page_count"]) if item["closing_page_count"] is not None else "-",
            f'{item["pages_printed"]:,}'.replace(",", "."),
        ])

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[48 * mm, 25 * mm, 45 * mm, 58 * mm, 25 * mm, 25 * mm, 28 * mm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12344D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    total_pages = sum(item["pages_printed"] for item in rows)
    story.extend([
        Spacer(1, 5 * mm),
        Paragraph(
            (
                f"<b>Total de impressoras:</b> {len(rows)} &nbsp;&nbsp; "
                f"<b>Total de impressoes:</b> {total_pages:,}".replace(",", ".")
            ),
            styles["Normal"],
        ),
    ])
    document.build(story)
    return output.getvalue()
