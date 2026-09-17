from __future__ import annotations

from datetime import date
from io import BytesIO

BRAND_NAVY = "0B2A52"
BRAND_BLUE = "0A6ED1"
BRAND_MUTED = "6B7C93"


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
    text = f"{item.get('manufacturer') or ''} {item.get('model') or ''} {item.get('display_name') or ''}".lower()
    return any(x in text for x in ("zebra", "zt230", "zpl"))


def _short(value, limit: int) -> str:
    text = str(value or "-").strip()
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def build_pdf_report(company_name: str, start: date, end: date, rows: list[dict], report_scope: str = "Parque completo") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(output, pagesize=page_size, leftMargin=6*mm, rightMargin=6*mm, topMargin=5*mm, bottomMargin=9*mm, title="Printflow - Relatorio de Impressao")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("pf-title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15, leading=16, textColor=colors.HexColor(f"#{BRAND_NAVY}"), spaceAfter=2)
    meta = ParagraphStyle("pf-meta", parent=styles["Normal"], fontSize=7.2, leading=8.3, textColor=colors.HexColor("#24364B"))
    cell = ParagraphStyle("pf-cell", parent=styles["Normal"], fontSize=5.2, leading=5.8, textColor=colors.HexColor("#142638"))
    cell_right = ParagraphStyle("pf-cell-right", parent=cell, alignment=2)

    header = Table([[Paragraph(f'<font color="#{BRAND_BLUE}" size="15"><b>Printflow</b></font><br/><font color="#{BRAND_MUTED}" size="6.5">Gestão inteligente de impressão</font>', styles["Normal"]), Paragraph("Relatório de Impressão", title)]], colWidths=[70*mm, 110*mm])
    header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))

    info = Table([[Paragraph(f"<b>Empresa:</b> {company_name}",meta), Paragraph(f"<b>Período:</b> {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}",meta), Paragraph(f"<b>Escopo:</b> {report_scope}",meta)]], colWidths=[90*mm,90*mm,100*mm])
    info.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))

    data = [["Impressora","IP / Serial","Unidade / Setor","Modelo","Inicial","Final","Impressões","R$/pág.","Custo"]]
    for item in rows:
        label = _label(item)
        identity = " / ".join(x for x in (item.get("ip"), item.get("serial")) if x) or "-"
        org = " / ".join(x for x in (item.get("unit_name"), item.get("sector_name")) if x) or "-"
        values = [
            _short(item.get("display_name"),24), _short(identity,28), _short(org,27), _short(_model(item),27),
            "N/A" if label else _num(item.get("opening_page_count")), "N/A" if label else _num(item.get("closing_page_count")),
            "N/A" if label else _num(item.get("pages_printed")), "N/A" if label else _rate(item.get("cost_per_page")),
            "N/A" if label else _money(item.get("estimated_cost")),
        ]
        data.append([Paragraph(str(v), cell_right if i>=4 else cell) for i,v in enumerate(values)])

    table = Table(data, repeatRows=1, colWidths=[35*mm,34*mm,40*mm,39*mm,19*mm,19*mm,22*mm,23*mm,27*mm], rowHeights=[5.5*mm]+[4.7*mm]*len(rows))
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(f"#{BRAND_BLUE}")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),5.5),("ALIGN",(4,0),(-1,-1),"RIGHT"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),0.2,colors.HexColor("#B8C7D5")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4F8FC")]),
        ("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1),
    ]))

    total_pages = sum(item.get("pages_printed",0) for item in rows if not _label(item))
    total_cost = sum(float(item.get("estimated_cost",0) or 0) for item in rows)
    summary = Paragraph(f"<b>Total de impressoras:</b> {len(rows)} &nbsp;&nbsp;&nbsp; <b>Total de impressões:</b> {_num(total_pages)} &nbsp;&nbsp;&nbsp; <b>Custo estimado:</b> {_money(total_cost)}", ParagraphStyle("pf-summary",parent=meta,fontSize=8,leading=9))
    story=[header,Spacer(1,1.5*mm),info,Spacer(1,2*mm),table,Spacer(1,2*mm),summary]

    def footer(canvas,_doc):
        canvas.saveState(); width,_=page_size; canvas.setStrokeColor(colors.HexColor("#D7E1EA"));canvas.setLineWidth(.35);canvas.line(6*mm,6.5*mm,width-6*mm,6.5*mm);canvas.setFillColor(colors.HexColor(f"#{BRAND_MUTED}"));canvas.setFont("Helvetica",6);canvas.drawString(6*mm,3.5*mm,f"Printflow · {company_name}");canvas.drawRightString(width-6*mm,3.5*mm,"Fechamento comercial");canvas.restoreState()

    doc.build([KeepTogether(story)],onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
