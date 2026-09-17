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
    doc = SimpleDocTemplate(output, pagesize=page_size, leftMargin=7*mm, rightMargin=7*mm, topMargin=5*mm, bottomMargin=9*mm, title="Printflow - Relatorio de Impressao")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("pf-title-v2", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15.5, leading=16, alignment=1, textColor=colors.HexColor(f"#{BRAND_NAVY}"), spaceAfter=0)
    brand = ParagraphStyle("pf-brand-v2", parent=styles["Normal"], fontSize=7, leading=7.8, textColor=colors.HexColor(f"#{BRAND_MUTED}"))
    meta = ParagraphStyle("pf-meta-v2", parent=styles["Normal"], fontSize=7.1, leading=8, textColor=colors.HexColor("#24364B"))
    meta_center = ParagraphStyle("pf-meta-center-v2", parent=meta, alignment=1)
    meta_right = ParagraphStyle("pf-meta-right-v2", parent=meta, alignment=2)
    cell = ParagraphStyle("pf-cell-v2", parent=styles["Normal"], fontSize=5.45, leading=5.9, textColor=colors.HexColor("#142638"), wordWrap="LTR")
    cell_right = ParagraphStyle("pf-cell-right-v2", parent=cell, alignment=2)

    header = Table([[
        Paragraph(f'<font color="#{BRAND_BLUE}" size="17"><b>Printflow</b></font><br/><font color="#{BRAND_MUTED}">Gestão inteligente de impressão</font>', brand),
        Paragraph("Relatório de Impressão", title),
        Paragraph('<font color="#6B7C93" size="6.5">FECHAMENTO COMERCIAL</font>', meta_right),
    ]], colWidths=[70*mm,143*mm,70*mm])
    header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))

    info = Table([[
        Paragraph(f"<b>Empresa</b><br/>{_short(company_name,38)}", meta),
        Paragraph(f"<b>Período</b><br/>{start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}", meta_center),
        Paragraph(f"<b>Escopo</b><br/>{_short(report_scope,38)}", meta_right),
    ]], colWidths=[94*mm,95*mm,94*mm], rowHeights=[10*mm])
    info.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F4F8FC")),("BOX",(0,0),(-1,-1),0.35,colors.HexColor("#D7E1EA")),("INNERGRID",(0,0),(-1,-1),0.25,colors.HexColor("#D7E1EA")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),3*mm),("RIGHTPADDING",(0,0),(-1,-1),3*mm),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))

    data = [["Impressora","IP / Serial","Unidade / Setor","Modelo","Inicial","Final","Impressões","R$/pág.","Custo"]]
    for item in rows:
        label = _label(item)
        identity = " / ".join(x for x in (item.get("ip"),item.get("serial")) if x) or "-"
        org = " / ".join(x for x in (item.get("unit_name"),item.get("sector_name")) if x) or "-"
        values=[_short(item.get("display_name"),23),_short(identity,26),_short(org,25),_short(_model(item),26),"N/A" if label else _num(item.get("opening_page_count")),"N/A" if label else _num(item.get("closing_page_count")),"N/A" if label else _num(item.get("pages_printed")),"N/A" if label else _rate(item.get("cost_per_page")),"N/A" if label else _money(item.get("estimated_cost"))]
        data.append([Paragraph(str(v),cell_right if i>=4 else cell) for i,v in enumerate(values)])

    table=Table(data,repeatRows=1,colWidths=[36*mm,36*mm,42*mm,40*mm,19*mm,19*mm,23*mm,25*mm,27*mm],rowHeights=[6*mm]+[5.15*mm]*len(rows),hAlign="CENTER")
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(f"#{BRAND_BLUE}")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),5.8),("ALIGN",(0,0),(3,0),"LEFT"),("ALIGN",(4,0),(-1,0),"RIGHT"),("ALIGN",(4,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),0.22,colors.HexColor("#B8C7D5")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F5F8FB")]),("LEFTPADDING",(0,0),(-1,-1),2.6),("RIGHTPADDING",(0,0),(-1,-1),2.6),("TOPPADDING",(0,0),(-1,-1),.8),("BOTTOMPADDING",(0,0),(-1,-1),.8)]))

    total_pages=sum(item.get("pages_printed",0) for item in rows if not _label(item));total_cost=sum(float(item.get("estimated_cost",0) or 0) for item in rows)
    metric_label=ParagraphStyle("pf-metric-label",parent=meta,fontSize=6.5,leading=7,textColor=colors.HexColor(f"#{BRAND_MUTED}"),alignment=1)
    metric_value=ParagraphStyle("pf-metric-value",parent=meta,fontName="Helvetica-Bold",fontSize=11,leading=11.5,textColor=colors.HexColor(f"#{BRAND_NAVY}"),alignment=1)
    summary=Table([[
        Paragraph(f"IMPRESSORAS<br/><font size='11' color='#{BRAND_NAVY}'><b>{len(rows)}</b></font>",metric_label),
        Paragraph(f"IMPRESSÕES NO PERÍODO<br/><font size='11' color='#{BRAND_NAVY}'><b>{_num(total_pages)}</b></font>",metric_label),
        Paragraph(f"CUSTO ESTIMADO<br/><font size='11' color='#{BRAND_NAVY}'><b>{_money(total_cost)}</b></font>",metric_label),
    ]],colWidths=[94*mm,95*mm,94*mm],rowHeights=[11*mm])
    summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F4F8FC")),("BOX",(0,0),(-1,-1),.4,colors.HexColor("#C8D7E5")),("INNERGRID",(0,0),(-1,-1),.3,colors.HexColor("#C8D7E5")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))

    story=[header,Spacer(1,1.8*mm),info,Spacer(1,2.2*mm),table,Spacer(1,2.2*mm),summary]

    def footer(canvas,_doc):
        canvas.saveState();width,_=page_size;canvas.setStrokeColor(colors.HexColor("#D7E1EA"));canvas.setLineWidth(.35);canvas.line(7*mm,6.5*mm,width-7*mm,6.5*mm);canvas.setFillColor(colors.HexColor(f"#{BRAND_MUTED}"));canvas.setFont("Helvetica",6);canvas.drawString(7*mm,3.5*mm,f"Printflow · {company_name}");canvas.drawRightString(width-7*mm,3.5*mm,"Fechamento comercial");canvas.restoreState()

    doc.build([KeepTogether(story)],onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
