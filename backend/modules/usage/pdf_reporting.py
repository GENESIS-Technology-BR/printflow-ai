from __future__ import annotations

from datetime import date
from io import BytesIO

BRAND_NAVY = "0B2A52"
BRAND_BLUE = "0A6ED1"
BRAND_MUTED = "6B7C93"
PALE_BLUE = "EEF6FF"
BORDER = "D7E1EA"


def _num(value) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}".replace(",", ".")


def _money(value) -> str:
    text = f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def _rate(value) -> str:
    return f"R$ {float(value or 0):.4f}".replace(".", ",")


def _model(item: dict) -> str:
    brand = (item.get("manufacturer") or "").strip()
    model = (item.get("model") or "").strip()
    if model and brand and model.lower().startswith(brand.lower()):
        return model
    return " ".join(x for x in (brand, model) if x) or "-"


def _label(item: dict) -> bool:
    text = " ".join(str(item.get(k) or "") for k in ("manufacturer", "model", "display_name", "hostname", "serial")).lower()
    return any(x in text for x in ("zebra", "zt230", "zpl", "ztc ", "zbr"))


def _short(value, limit: int) -> str:
    text = str(value or "-").strip()
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def build_pdf_report(
    company_name: str,
    start: date,
    end: date,
    rows: list[dict],
    report_scope: str = "Parque completo",
    bw_rate: float = 0.0,
    color_rate: float = 0.0,
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(output, pagesize=page_size, leftMargin=7*mm, rightMargin=7*mm, topMargin=4.5*mm, bottomMargin=8*mm, title="Printflow - Relatorio de Impressao")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("pf-final-title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15.5, leading=16, alignment=1, textColor=colors.HexColor(f"#{BRAND_NAVY}"), spaceAfter=0)
    brand = ParagraphStyle("pf-final-brand", parent=styles["Normal"], fontSize=6.4, leading=7, textColor=colors.HexColor(f"#{BRAND_MUTED}"))
    meta_right = ParagraphStyle("pf-final-meta", parent=styles["Normal"], fontSize=6.2, leading=7, alignment=2, textColor=colors.HexColor("#24364B"))
    cell = ParagraphStyle("pf-final-cell", parent=styles["Normal"], fontSize=5.05, leading=5.4, textColor=colors.HexColor("#142638"), wordWrap="LTR")
    cell_right = ParagraphStyle("pf-final-cell-right", parent=cell, alignment=2)

    header = Table([[
        Paragraph(f'<font color="#{BRAND_BLUE}" size="17"><b>Printflow</b></font><br/><font color="#{BRAND_MUTED}">Gestão inteligente de impressão</font>', brand),
        Paragraph(f"Relatório de Impressão<br/><font size='7' color='#{BRAND_MUTED}'>Período: {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}</font>", title),
        Paragraph(f'<font color="#{BRAND_BLUE}" size="6"><b>FECHAMENTO COMERCIAL</b></font><br/><br/><b>Empresa:</b> {_short(company_name,32)}<br/><b>Escopo:</b> {_short(report_scope,32)}', meta_right),
    ]], colWidths=[67*mm,145*mm,71*mm], rowHeights=[15*mm])
    header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),1.5*mm),("RIGHTPADDING",(0,0),(-1,-1),1.5*mm),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LINEBELOW",(0,0),(-1,-1),0.45,colors.HexColor(f"#{BORDER}"))]))

    data = [["#","Impressora","IP / Serial","Unidade / Setor","Modelo","Inicial","Final","Impressões","R$/pág.","Custo"]]
    for idx, item in enumerate(rows, start=1):
        label = _label(item)
        identity = " / ".join(x for x in (item.get("ip"), item.get("serial")) if x) or "-"
        org = " / ".join(x for x in (item.get("unit_name"), item.get("sector_name")) if x) or "-"
        values = [str(idx), _short(item.get("display_name"),22), _short(identity,25), _short(org,25), _short(_model(item),25), "N/A" if label else _num(item.get("opening_page_count")), "N/A" if label else _num(item.get("closing_page_count")), "N/A" if label else _num(item.get("pages_printed")), "N/A" if label else _rate(item.get("cost_per_page")), "N/A" if label else _money(item.get("estimated_cost"))]
        data.append([Paragraph(str(v), cell_right if i >= 5 else cell) for i, v in enumerate(values)])

    table = Table(data, repeatRows=1, colWidths=[7*mm,32*mm,38*mm,40*mm,39*mm,18*mm,18*mm,24*mm,24*mm,29*mm], rowHeights=[6*mm]+[4.7*mm]*len(rows), hAlign="CENTER")
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(f"#{BRAND_BLUE}")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),5.5),("ALIGN",(0,0),(4,0),"LEFT"),("ALIGN",(5,0),(-1,0),"RIGHT"),("ALIGN",(5,1),(-1,-1),"RIGHT"),("ALIGN",(0,1),(0,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),0.18,colors.HexColor("#C7D3DE")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FC")]),("LEFTPADDING",(0,0),(-1,-1),2.2),("RIGHTPADDING",(0,0),(-1,-1),2.2),("TOPPADDING",(0,0),(-1,-1),.6),("BOTTOMPADDING",(0,0),(-1,-1),.6)]))

    applicable = [item for item in rows if not _label(item)]
    total_pages = sum(item.get("pages_printed",0) or 0 for item in applicable)
    variable_cost = sum(
        float(item.get("estimated_cost",0) or 0)
        for item in applicable
        if item.get("cost_source") != "fixed_monthly"
    )
    fixed_cost = sum(
        float(item.get("estimated_cost",0) or 0)
        for item in applicable
        if item.get("cost_source") == "fixed_monthly"
    )
    total_cost = variable_cost + fixed_cost
    label_count = len(rows) - len(applicable)
    card_title = ParagraphStyle("pf-final-card-title", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=7.8, textColor=colors.HexColor(f"#{BRAND_NAVY}"), alignment=0)
    card_value = ParagraphStyle("pf-final-card-value", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=13.5, leading=14, textColor=colors.HexColor(f"#{BRAND_NAVY}"), alignment=0)
    card_hint = ParagraphStyle("pf-final-card-hint", parent=styles["Normal"], fontSize=5.8, leading=6.2, textColor=colors.HexColor(f"#{BRAND_MUTED}"), alignment=0)

    def metric_card(label: str, value: str, hint: str):
        return Table([[Paragraph(label, card_title)], [Paragraph(value, card_value)], [Paragraph(hint, card_hint)]], colWidths=[83*mm], rowHeights=[4.5*mm,6.3*mm,4.2*mm])

    summary = Table([[
        metric_card("Tarifa P&B", _rate(bw_rate), "Tarifa contratual por página"),
        metric_card("Tarifa colorida", _rate(color_rate), "Aplicada quando houver contador de cor"),
        metric_card("Custo fixo", _money(fixed_cost), "Equipamentos com cobrança mensal"),
        metric_card("Total consolidado", _money(total_cost), f"{_num(total_pages)} páginas no período"),
    ]], colWidths=[70*mm,70*mm,70*mm,71*mm], rowHeights=[17*mm])
    summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F8FAFD")),("BOX",(0,0),(-1,-1),.35,colors.HexColor(f"#{BORDER}")),("INNERGRID",(0,0),(-1,-1),.35,colors.white),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5*mm),("RIGHTPADDING",(0,0),(-1,-1),5*mm),("TOPPADDING",(0,0),(-1,-1),1*mm),("BOTTOMPADDING",(0,0),(-1,-1),1*mm)]))

    base_note = (
        "A tarifa colorida é apresentada como referência contratual e só entra no cálculo automático "
        "quando houver contador colorido separado."
    )
    note_text = (
        f"●  {label_count} impressora(s) de etiquetas são exibidas como N/A e não entram no fechamento.  ●  {base_note}"
        if label_count
        else f"●  {base_note}"
    )
    note = Table([[Paragraph(note_text, ParagraphStyle("pf-final-note", parent=styles["Normal"], fontSize=5.8, leading=6.4, textColor=colors.HexColor("#365A7C")))]], colWidths=[281*mm], rowHeights=[7*mm])
    note.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(f"#{PALE_BLUE}")),("BOX",(0,0),(-1,-1),.25,colors.HexColor("#D7EAFD")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),4*mm),("RIGHTPADDING",(0,0),(-1,-1),4*mm),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))

    story = [header, Spacer(1,2.2*mm), table, Spacer(1,2.5*mm), summary, Spacer(1,1.5*mm), note]

    def footer(canvas, _doc):
        canvas.saveState(); width,_ = page_size
        canvas.setStrokeColor(colors.HexColor(f"#{BORDER}")); canvas.setLineWidth(.35); canvas.line(7*mm,6.3*mm,width-7*mm,6.3*mm)
        canvas.setFillColor(colors.HexColor(f"#{BRAND_NAVY}")); canvas.setFont("Helvetica-Bold",5.8); canvas.drawString(7*mm,3.3*mm,"Printflow")
        canvas.setFillColor(colors.HexColor(f"#{BRAND_MUTED}")); canvas.setFont("Helvetica",5.8); canvas.drawString(20*mm,3.3*mm,f"|  {company_name}"); canvas.drawRightString(width-7*mm,3.3*mm,f"Relatório gerado em {end.strftime('%d/%m/%Y')}  |  Fechamento comercial")
        canvas.restoreState()

    doc.build([KeepTogether(story)], onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
