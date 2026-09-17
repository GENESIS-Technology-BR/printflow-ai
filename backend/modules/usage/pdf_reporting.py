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
    text = " ".join(str(item.get(k) or "") for k in ("manufacturer", "model", "display_name", "hostname", "serial")).lower()
    return any(x in text for x in ("zebra", "zt230", "zpl", "ztc ", "zbr"))


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
    doc = SimpleDocTemplate(output, pagesize=page_size, leftMargin=8*mm, rightMargin=8*mm, topMargin=5*mm, bottomMargin=9*mm, title="Printflow - Relatorio de Impressao")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("pf-title-v4", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15, leading=15.5, alignment=1, textColor=colors.HexColor(f"#{BRAND_NAVY}"), spaceAfter=0)
    brand = ParagraphStyle("pf-brand-v4", parent=styles["Normal"], fontSize=6.8, leading=7.4, textColor=colors.HexColor(f"#{BRAND_MUTED}"))
    meta = ParagraphStyle("pf-meta-v4", parent=styles["Normal"], fontSize=6.8, leading=7.5, textColor=colors.HexColor("#24364B"))
    meta_center = ParagraphStyle("pf-meta-center-v4", parent=meta, alignment=1)
    meta_right = ParagraphStyle("pf-meta-right-v4", parent=meta, alignment=2)
    cell = ParagraphStyle("pf-cell-v4", parent=styles["Normal"], fontSize=5.25, leading=5.65, textColor=colors.HexColor("#142638"), wordWrap="LTR")
    cell_right = ParagraphStyle("pf-cell-right-v4", parent=cell, alignment=2)

    header = Table([[
        Paragraph(f'<font color="#{BRAND_BLUE}" size="16"><b>Printflow</b></font><br/><font color="#{BRAND_MUTED}">Gestão inteligente de impressão</font>', brand),
        Paragraph("Relatório de Impressão", title),
        Paragraph('<font color="#6B7C93" size="6.2"><b>FECHAMENTO COMERCIAL</b></font>', meta_right),
    ]], colWidths=[67*mm,147*mm,67*mm], rowHeights=[10.5*mm])
    header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))

    info = Table([[
        Paragraph(f"<b>EMPRESA</b><br/>{_short(company_name,38)}", meta),
        Paragraph(f"<b>PERÍODO</b><br/>{start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}", meta_center),
        Paragraph(f"<b>ESCOPO</b><br/>{_short(report_scope,38)}", meta_right),
    ]], colWidths=[93*mm,95*mm,93*mm], rowHeights=[8.5*mm])
    info.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F6F9FC")),("BOX",(0,0),(-1,-1),0.3,colors.HexColor("#D7E1EA")),("INNERGRID",(0,0),(-1,-1),0.25,colors.HexColor("#D7E1EA")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),3*mm),("RIGHTPADDING",(0,0),(-1,-1),3*mm),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))

    data = [["Impressora","IP / Serial","Unidade / Setor","Modelo","Inicial","Final","Impressões","R$/pág.","Custo"]]
    for item in rows:
        label = _label(item)
        identity = " / ".join(x for x in (item.get("ip"),item.get("serial")) if x) or "-"
        org = " / ".join(x for x in (item.get("unit_name"),item.get("sector_name")) if x) or "-"
        values=[_short(item.get("display_name"),22),_short(identity,25),_short(org,24),_short(_model(item),25),"N/A" if label else _num(item.get("opening_page_count")),"N/A" if label else _num(item.get("closing_page_count")),"N/A" if label else _num(item.get("pages_printed")),"N/A" if label else _rate(item.get("cost_per_page")),"N/A" if label else _money(item.get("estimated_cost"))]
        data.append([Paragraph(str(v),cell_right if i>=4 else cell) for i,v in enumerate(values)])

    table=Table(data,repeatRows=1,colWidths=[36*mm,36*mm,42*mm,40*mm,19*mm,19*mm,23*mm,25*mm,27*mm],rowHeights=[5.8*mm]+[4.95*mm]*len(rows),hAlign="CENTER")
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(f"#{BRAND_BLUE}")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),5.6),("ALIGN",(0,0),(3,0),"LEFT"),("ALIGN",(4,0),(-1,0),"RIGHT"),("ALIGN",(4,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),0.2,colors.HexColor("#B8C7D5")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F5F8FB")]),("LEFTPADDING",(0,0),(-1,-1),2.4),("RIGHTPADDING",(0,0),(-1,-1),2.4),("TOPPADDING",(0,0),(-1,-1),.7),("BOTTOMPADDING",(0,0),(-1,-1),.7)]))

    applicable=[item for item in rows if not _label(item)]
    total_pages=sum(item.get("pages_printed",0) or 0 for item in applicable)
    total_cost=sum(float(item.get("estimated_cost",0) or 0) for item in applicable)
    label_count=len(rows)-len(applicable)
    metric_label=ParagraphStyle("pf-metric-label-v4",parent=meta,fontName="Helvetica-Bold",fontSize=5.8,leading=6.3,textColor=colors.HexColor(f"#{BRAND_MUTED}"),alignment=1)
    metric_value=ParagraphStyle("pf-metric-value-v4",parent=meta,fontName="Helvetica-Bold",fontSize=11.5,leading=12,textColor=colors.HexColor(f"#{BRAND_NAVY}"),alignment=1)
    summary_data=[
        [Paragraph("EQUIPAMENTOS MONITORADOS",metric_label),Paragraph("IMPRESSÕES APLICÁVEIS",metric_label),Paragraph("CUSTO ESTIMADO",metric_label)],
        [Paragraph(str(len(rows)),metric_value),Paragraph(_num(total_pages),metric_value),Paragraph(_money(total_cost),metric_value)],
    ]
    summary=Table(summary_data,colWidths=[93*mm,95*mm,93*mm],rowHeights=[4.2*mm,7.2*mm])
    summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F6F9FC")),("BOX",(0,0),(-1,-1),.35,colors.HexColor("#C8D7E5")),("INNERGRID",(0,0),(-1,-1),.25,colors.HexColor("#C8D7E5")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(0,0),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))

    note_text=f"* {label_count} impressora(s) de etiquetas exibida(s) como N/A; não entram no volume nem no custo por página." if label_count else "* Fechamento calculado com os equipamentos monitorados no período."
    note=Paragraph(note_text,ParagraphStyle("pf-note-v4",parent=meta,fontSize=5.6,leading=6,textColor=colors.HexColor(f"#{BRAND_MUTED}")))
    story=[header,Spacer(1,1*mm),info,Spacer(1,1.5*mm),table,Spacer(1,1.5*mm),summary,Spacer(1,.7*mm),note]

    def footer(canvas,_doc):
        canvas.saveState();width,_=page_size;canvas.setStrokeColor(colors.HexColor("#D7E1EA"));canvas.setLineWidth(.35);canvas.line(8*mm,6.5*mm,width-8*mm,6.5*mm);canvas.setFillColor(colors.HexColor(f"#{BRAND_MUTED}"));canvas.setFont("Helvetica",6);canvas.drawString(8*mm,3.5*mm,f"Printflow · {company_name}");canvas.drawRightString(width-8*mm,3.5*mm,"Fechamento comercial");canvas.restoreState()

    doc.build([KeepTogether(story)],onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
