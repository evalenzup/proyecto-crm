# backend/app/services/pdf_generator.py
from __future__ import annotations

import os
from io import BytesIO
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

from sqlalchemy.orm import Session, selectinload

from app.models.presupuestos import Presupuesto
from app.models.presupuestos import PresupuestoDetalle
from app.config import settings

# --- Layout / Estilos (inspirado en pdf_factura.py) ---
PAGE_W, PAGE_H = letter
MARGIN = 0.5 * inch
LOGO_W = 2.0 * inch
LOGO_H = 1.0 * inch

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"

CONTENT_X0 = MARGIN
CONTENT_Y0 = MARGIN
CONTENT_X1 = PAGE_W - MARGIN
CONTENT_Y1 = PAGE_H - MARGIN

FOOTER_TOP_Y = CONTENT_Y0 + 1.5 * inch
AVAILABLE_BOTTOM_Y = FOOTER_TOP_Y + 0.10 * inch

styles = getSampleStyleSheet()
p_left_6 = ParagraphStyle(name="p_left_6", parent=styles["Normal"], fontName=FONT, fontSize=6, leading=7, alignment=0)
p_right_6 = ParagraphStyle(name="p_right_6", parent=styles["Normal"], fontName=FONT, fontSize=6, leading=7, alignment=2)
p_center_6 = ParagraphStyle(name="p_center_6", parent=styles["Normal"], fontName=FONT, fontSize=6, leading=7, alignment=1)

# --- Helpers (inspirado en pdf_factura.py) ---

def _money(v: Optional[Decimal | float | int]) -> str:
    try:
        return f"${Decimal(v):,.2f}"
    except Exception:
        return "$0.00"

def _wrap_lines(c: canvas.Canvas, text: str, max_w: float, font=FONT, size=7) -> List[str]:
    if not text: return []
    c.setFont(font, size)
    out: List[str] = []
    line = ""
    for token in text.split(" "):
        test = token if not line else f"{line} {token}"
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            if line: out.append(line)
            line = token
    if line: out.append(line)
    return out

def _draw_label_wrap(c: canvas.Canvas, label: str, value: Optional[str], x: float, y: float, max_w_value: float, font_label=FONT_B, font_value=FONT, size=7, gap=4) -> float:
    if not value: return y
    c.setFont(font_label, size)
    c.drawString(x, y, f"{label}:")
    vx = x + c.stringWidth(f"{label}:", font_label, size) + 6
    max_w = max(10.0, max_w_value - (vx - x))
    lines = _wrap_lines(c, value, max_w, font=font_value, size=size)
    c.setFont(font_value, size)
    yy = y
    for ln in lines:
        c.drawString(vx, yy, ln)
        yy -= size + 2
    return yy - gap

def _compose_address(obj) -> Optional[str]:
    if not obj: return None
    parts = [
        getattr(obj, 'calle', ''),
        getattr(obj, 'numero_exterior', ''),
        f"Int {getattr(obj, 'numero_interior', '')}" if getattr(obj, 'numero_interior', '') else '',
    ]
    address_line1 = " ".join(filter(None, parts))
    parts_line2 = [
        getattr(obj, 'colonia', ''),
        getattr(obj, 'ciudad', ''),
        getattr(obj, 'estado', ''),
        f"CP {getattr(obj, 'codigo_postal', '')}"
    ]
    address_line2 = ", ".join(filter(None, parts_line2))
    return f"{address_line1}\n{address_line2}"

def _draw_watermark(c: canvas.Canvas, text: str):
    c.saveState()
    c.setFillColor(colors.Color(0.1, 0.1, 0.1, alpha=0.08))
    c.setFont(FONT_B, 60)
    c.translate(PAGE_W / 2, PAGE_H / 2)
    c.rotate(45)
    w = c.stringWidth(text, FONT_B, 60)
    c.drawCentredString(0, 0, text)
    c.restoreState()

def _guess_logo_path(presupuesto: Presupuesto) -> Optional[str]:
    emp = getattr(presupuesto, "empresa", None)
    if emp and getattr(emp, "logo", None):
        p = emp.logo
        if not os.path.isabs(p):
            # Asume que la ruta es relativa a la carpeta 'data'
            p = os.path.join(settings.DATA_DIR, p)
        if os.path.exists(p):
            return p
    return None

# --- Estructura del PDF ---

def _draw_header(c: canvas.Canvas, p: Presupuesto, logo_path: Optional[str]) -> float:
    # Título principal
    c.setFont(FONT_B, 18)
    c.drawCentredString(PAGE_W / 2.0, CONTENT_Y1 - 0.5 * inch, f"PRESUPUESTO: {p.folio}")

    # Logo
    y_below_logo = CONTENT_Y1 - 0.7 * inch
    if logo_path:
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            scale = min(LOGO_W / iw, LOGO_H / ih)
            dw, dh = iw * scale, ih * scale
            c.drawImage(img, CONTENT_X0, CONTENT_Y1 - LOGO_H - 0.2*inch, width=dw, height=dh, mask="auto")
        except Exception:
            pass

    # Info del presupuesto (derecha)
    y_right = CONTENT_Y1 - 0.7 * inch
    c.setFont(FONT_B, 8)
    c.drawRightString(CONTENT_X1, y_right, "Fecha de Emisión:")
    c.setFont(FONT, 8)
    c.drawRightString(CONTENT_X1 - 100, y_right, p.fecha_emision.strftime("%Y-%m-%d"))
    y_right -= 12
    if p.fecha_vencimiento:
        c.setFont(FONT_B, 8)
        c.drawRightString(CONTENT_X1, y_right, "Válido hasta:")
        c.setFont(FONT, 8)
        c.drawRightString(CONTENT_X1 - 100, y_right, p.fecha_vencimiento.strftime("%Y-%m-%d"))
        y_right -= 12
    c.setFont(FONT_B, 8)
    c.drawRightString(CONTENT_X1, y_right, "Versión:")
    c.setFont(FONT, 8)
    c.drawRightString(CONTENT_X1 - 100, y_right, str(p.version))

    # Separador
    y_separator = min(y_below_logo, y_right) - 15
    c.setStrokeColor(colors.lightgrey)
    c.line(CONTENT_X0, y_separator, CONTENT_X1, y_separator)

    # Emisor y Receptor
    y_sections_start = y_separator - 15
    MID_X = (CONTENT_X0 + CONTENT_X1) / 2.0
    GUTTER = 18
    x_right_col = MID_X + GUTTER / 2
    left_w = max(120.0, MID_X - CONTENT_X0 - GUTTER / 2 - 4)
    right_w = max(120.0, CONTENT_X1 - x_right_col - 4)

    # Emisor
    y_left = y_sections_start
    c.setFont(FONT_B, 9)
    c.drawString(CONTENT_X0, y_left, "EMPRESA")
    y_left -= 12
    emp = p.empresa
    if emp:
        c.setFont(FONT_B, 8)
        c.drawString(CONTENT_X0, y_left, emp.nombre_comercial or "")
        y_left -= 10
        c.setFont(FONT, 7)
        y_left = _draw_label_wrap(c, "RFC", emp.rfc, CONTENT_X0, y_left, left_w)
        dir_em = _compose_address(emp)
        if dir_em:
            y_left = _draw_label_wrap(c, "Dirección", dir_em, CONTENT_X0, y_left, left_w)

    # Receptor
    y_right = y_sections_start
    c.setFont(FONT_B, 9)
    c.drawString(x_right_col, y_right, "CLIENTE")
    y_right -= 12
    cli = p.cliente
    if cli:
        c.setFont(FONT_B, 8)
        c.drawString(x_right_col, y_right, cli.nombre_comercial or "")
        y_right -= 10
        c.setFont(FONT, 7)
        y_right = _draw_label_wrap(c, "RFC", cli.rfc, x_right_col, y_right, right_w)
        dir_rc = _compose_address(cli)
        if dir_rc:
            y_right = _draw_label_wrap(c, "Dirección", dir_rc, x_right_col, y_right, right_w)

    header_bottom = min(y_left, y_right) - 8
    return max(header_bottom, AVAILABLE_BOTTOM_Y + 60)

def _draw_footer(c: canvas.Canvas, p: Presupuesto):
    c.setStrokeColor(colors.lightgrey)
    c.line(CONTENT_X0, FOOTER_TOP_Y, CONTENT_X1, FOOTER_TOP_Y)
    base_y = FOOTER_TOP_Y - 15

    # Totales a la derecha
    right_x = CONTENT_X1
    totales_y = FOOTER_TOP_Y - 15
    c.setFont(FONT_B, 9)
    c.drawRightString(right_x, totales_y, f"Subtotal: {_money(p.subtotal)}")
    totales_y -= 15
    c.drawRightString(right_x, totales_y, f"Impuestos: {_money(p.impuestos)}")
    totales_y -= 15
    c.setFont(FONT_B, 10)
    c.drawRightString(right_x, totales_y, f"Total: {_money(p.total)}")

    # Condiciones comerciales a la izquierda
    if p.condiciones_comerciales:
        c.setFont(FONT_B, 8)
        c.drawString(CONTENT_X0, base_y, "Condiciones Comerciales:")
        base_y -= 10
        p_cond = Paragraph(p.condiciones_comerciales, styles['Normal'])
        p_cond.wrapOn(c, PAGE_W / 2 - MARGIN, FOOTER_TOP_Y)
        p_cond.drawOn(c, CONTENT_X0, base_y - p_cond.height)

def _build_table(rows: List[List[Paragraph | str]]) -> Table:
    col_widths = [3.5 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch]
    tbl = Table(rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), FONT_B),
        ('ALIGN', (0, 0), (-1, 0), "CENTER"),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 1), (-1, -1), "RIGHT"),
        ('ALIGN', (0, 1), (0, -1), "LEFT"),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('TOPPADDING', (0,0), (-1,0), 10),
    ]))
    return tbl

def _concept_row(cpt: PresupuestoDetalle) -> List[Paragraph | str]:
    importe = (cpt.cantidad or 0) * (cpt.precio_unitario or 0)
    return [
        Paragraph(str(cpt.descripcion or ""), styles['Normal']),
        Paragraph(str(cpt.cantidad or 0), styles['Normal']),
        Paragraph(_money(cpt.precio_unitario), styles['Normal']),
        Paragraph(_money(importe), styles['Normal']),
    ]

# --- Render Principal ---

def render_presupuesto_pdf_bytes(presupuesto: Presupuesto, db: Session) -> bytes:
    logo_path = _guess_logo_path(presupuesto)
    
    watermark_text = None
    if presupuesto.estado not in ["BORRADOR", "ENVIADO"]:
        watermark_text = presupuesto.estado

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    conceptos = list(presupuesto.detalles or [])
    header = [
        Paragraph("Descripción", styles['Normal']),
        Paragraph("Cantidad", styles['Normal']),
        Paragraph("P. Unitario", styles['Normal']),
        Paragraph("Importe", styles['Normal']),
    ]

    i = 0
    total_conceptos = len(conceptos)
    page_top_y: float = 0.0

    def new_page():
        nonlocal page_top_y
        c.setFont(FONT, 6)
        page_top_y = _draw_header(c, presupuesto, logo_path)
        if watermark_text:
            _draw_watermark(c, watermark_text)

    new_page()

    while i < total_conceptos or total_conceptos == 0:
        rows = [header]
        y_available = page_top_y - AVAILABLE_BOTTOM_Y
        tbl = _build_table(rows)
        _, h = tbl.wrapOn(c, CONTENT_X1 - CONTENT_X0, y_available)

        j = i
        while j < total_conceptos:
            row = _concept_row(conceptos[j])
            test_rows = rows + [row]
            test_tbl = _build_table(test_rows)
            _, test_h = test_tbl.wrapOn(c, CONTENT_X1 - CONTENT_X0, y_available)
            if test_h <= y_available:
                rows.append(row)
                h = test_h
                j += 1
            else:
                break

        tbl = _build_table(rows)
        tbl.wrapOn(c, CONTENT_X0, page_top_y - h)

        i = j
        is_last = i >= total_conceptos
        if is_last:
            _draw_footer(c, presupuesto)

        c.setFont(FONT, 6)
        c.drawCentredString(PAGE_W / 2, MARGIN / 2, f"Página {c.getPageNumber()}")

        if not is_last:
            c.showPage()
            new_page()
        
        if total_conceptos == 0 and is_last:
             break
        elif is_last:
             break


    c.save()
    return buf.getvalue()

def generate_presupuesto_pdf(presupuesto: Presupuesto, db: Session) -> bytes:
    """
    Genera un archivo PDF para un presupuesto dado, utilizando el nuevo motor de renderizado.
    """
    # Aquí se podría añadir lógica para cargar datos adicionales si fuera necesario
    # Por ahora, el objeto presupuesto ya viene con 'empresa' y 'cliente' cargados.
    return render_presupuesto_pdf_bytes(presupuesto, db)