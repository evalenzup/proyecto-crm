# app/services/pdf_pago.py
from __future__ import annotations

import os
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from urllib.parse import urlencode

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

from sqlalchemy.orm import Session, selectinload

from app.models.pago import Pago, PagoDocumentoRelacionado, EstatusPago
from app.config import settings

# Reutilizar helpers y catálogos del servicio de facturas
from .pdf_factura import (
    _regimen_label,
    _forma_label,
    _money,
    _num,
    _wrap_lines,
    _draw_label_wrap,
    _compose_address,
    _draw_watermark,
    _guess_logo_path_for_factura, # Adaptado para pago
    p_center_6,
    p_left_6,
    p_right_6,
    FONT,
    FONT_B,
    MARGIN,
    PAGE_W,
    PAGE_H,
    CONTENT_X0,
    CONTENT_Y0,
    CONTENT_X1,
    CONTENT_Y1,
    LOGO_W,
    LOGO_H,
)

# Layout específico para Complemento de Pago
CBB_SIZE = 1.4 * inch
FOOTER_TOP_Y = CONTENT_Y0 + 3.2 * inch
AVAILABLE_BOTTOM_Y = FOOTER_TOP_Y + 0.10 * inch

# --- Carga de datos ---
def load_pago_full(db: Session, pago_id: UUID) -> Optional[Pago]:
    return (
        db.query(Pago)
        .options(
            selectinload(Pago.empresa),
            selectinload(Pago.cliente),
            selectinload(Pago.documentos_relacionados).selectinload(PagoDocumentoRelacionado.factura),
        )
        .filter(Pago.id == pago_id)
        .first()
    )

# --- QR Code ---
def _build_pago_qr_url(p: Pago) -> str:
    base = "https://verificacfdi.facturaelectronica.sat.gob.mx/"
    uuid = (getattr(p, "uuid", None) or "").strip()
    re = (getattr(getattr(p, "empresa", None), "rfc", None) or "").strip().upper()
    rr = (getattr(getattr(p, "cliente", None), "rfc", None) or "").strip().upper()
    total = getattr(p, "monto", None)
    # El sello del CFDI de pago no está en el modelo, asumimos que se podría añadir
    # sello_cfdi = (getattr(p, "sello_cfdi", None) or "").strip()
    # fe = sello_cfdi[-8:] if sello_cfdi else ""

    if uuid and re and rr and (total is not None):
        params = {"id": uuid, "re": re, "rr": rr, "tt": f"{total:.2f}"}
        query = urlencode(params)
        # if fe:
        #     query += f"&fe={fe}"
        return base + "?" + query
    return base

def _draw_pago_qr(c: canvas.Canvas, p: Pago):
    try:
        import qrcode
        url = _build_pago_qr_url(p)
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        ir = ImageReader(img.convert("RGB"))
        c.drawImage(ir, CONTENT_X0, FOOTER_TOP_Y - CBB_SIZE - 1.1 * inch, width=CBB_SIZE, height=CBB_SIZE, mask="auto")
    except Exception as e:
        print(f"Error generando QR para pago: {e}")

# --- Header ---
def _draw_pago_header(c: canvas.Canvas, p: Pago, logo_path: Optional[str]) -> float:
    # Logo (similar a factura)
    y_below_logo = CONTENT_Y1 - 20
    if logo_path:
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            scale = min(LOGO_W / iw, LOGO_H / ih)
            dw, dh = iw * scale, ih * scale
            x_logo = CONTENT_X1 - dw - 0.1 * inch
            y_logo = CONTENT_Y1 - dh - 0.1 * inch
            c.drawImage(img, x_logo, y_logo, width=dw, height=dh, mask="auto")
            y_below_logo = y_logo - 3
        except Exception:
            pass

    # Título del documento
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_X0, CONTENT_Y1 - 24, "Complemento de Recepción de Pagos")

    # Datos del CFDI de Pago
    y_left = CONTENT_Y1 - 45
    x_space = 80
    if p.serie or p.folio:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Serie y Folio:")
        c.setFont(FONT, 8); c.drawString(CONTENT_X0 + x_space, y_left, f"{p.serie or ''} {p.folio}"); y_left -= 12
    if p.uuid:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Folio Fiscal (UUID):")
        c.setFont(FONT, 8); c.drawString(CONTENT_X0 + x_space, y_left, p.uuid); y_left -= 12
    if p.fecha_timbrado:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Fecha Timbrado:")
        c.setFont(FONT, 8); c.drawString(CONTENT_X0 + x_space, y_left, p.fecha_timbrado.strftime("%Y-%m-%d %H:%M:%S")); y_left -= 12
    if p.empresa and p.empresa.codigo_postal:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Lugar de expedición:")
        c.setFont(FONT, 8); c.drawString(CONTENT_X0 + x_space, y_left, p.empresa.codigo_postal); y_left -= 12

    # Emisor y Receptor
    MID_X = (CONTENT_X0 + CONTENT_X1) / 2.0
    GUTTER = 12
    x_right = MID_X + GUTTER / 2
    left_w = max(120.0, MID_X - CONTENT_X0 - GUTTER / 2 - 4)
    right_w = max(120.0, CONTENT_X1 - x_right - 4)
    y_sections_start = min(y_left - 4, y_below_logo)

    # Emisor
    y_left = y_sections_start
    c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Emisor"); y_left -= 12
    if p.empresa:
        y_left = _draw_label_wrap(c, "Nombre", p.empresa.nombre, CONTENT_X0, y_left, left_w)
        y_left = _draw_label_wrap(c, "RFC", p.empresa.rfc, CONTENT_X0, y_left, left_w)
        y_left = _draw_label_wrap(c, "Régimen", _regimen_label(p.empresa.regimen_fiscal), CONTENT_X0, y_left, left_w)

    # Receptor
    y_right = y_sections_start
    c.setFont(FONT_B, 8); c.drawString(x_right, y_right, "Receptor"); y_right -= 12
    if p.cliente:
        y_right = _draw_label_wrap(c, "Nombre", p.cliente.nombre_razon_social, x_right, y_right, right_w)
        y_right = _draw_label_wrap(c, "RFC", p.cliente.rfc, x_right, y_right, right_w)
        y_right = _draw_label_wrap(c, "Régimen", _regimen_label(p.cliente.regimen_fiscal), x_right, y_right, right_w)
        y_right = _draw_label_wrap(c, "Uso CFDI", "CP01 - Pagos", x_right, y_right, right_w)

    header_bottom = min(y_left, y_right) - 15
    return max(header_bottom, AVAILABLE_BOTTOM_Y + 60)

# --- Footer ---
def _draw_pago_footer(c: canvas.Canvas, p: Pago):
    c.setStrokeColor(colors.lightgrey)
    c.line(CONTENT_X0, FOOTER_TOP_Y, CONTENT_X1, FOOTER_TOP_Y)

    # Leyenda
    c.setFont(FONT, 6)
    c.drawCentredString(PAGE_W / 2, FOOTER_TOP_Y - 12, "Este documento es una representación impresa de un CFDI")

    # QR y Sellos
    _draw_pago_qr(c, p)

    qr_right_x = CONTENT_X0 + CBB_SIZE + 12
    max_w = CONTENT_X1 - qr_right_x
    y = FOOTER_TOP_Y - CBB_SIZE - 24

    def draw_block(label, value, y_start):
        if not value: return y_start
        c.setFont(FONT_B, 6); c.drawString(qr_right_x, y_start, label)
        y = y_start - 8
        lines = _wrap_lines(c, value, max_w, font=FONT, size=5)
        c.setFont(FONT, 5)
        for ln in lines:
            c.drawString(qr_right_x, y, ln); y -= 7
        return y - 4

    # Asumiendo que estos campos existen en el modelo Pago
    y = draw_block("Sello digital del CFDI:", getattr(p, 'sello_cfdi', None), y)
    y = draw_block("Sello digital del SAT:", getattr(p, 'sello_sat', None), y)
    y = draw_block("Cadena original del complemento de certificación digital del SAT:", getattr(p, 'cadena_original', None), y)
    if p.no_certificado:
        c.setFont(FONT_B, 6); c.drawString(qr_right_x, y, f"No. de Serie del Certificado del Emisor: {p.no_certificado}"); y -= 10
    if p.no_certificado_sat:
        c.setFont(FONT_B, 6); c.drawString(qr_right_x, y, f"No. de Serie del Certificado del SAT: {p.no_certificado_sat}"); y -= 10
    

# --- Tabla de Documentos Relacionados ---
_COL_WIDTHS_PAGO = [
    1.6 * inch,  # ID Documento (UUID)
    0.8 * inch,  # Serie y Folio
    0.6 * inch,  # Moneda
    0.8 * inch,  # Método de Pago
    0.7 * inch,  # Num. Parcialidad
    1.0 * inch,  # Saldo Anterior
    1.0 * inch,  # Importe Pagado
    1.0 * inch,  # Saldo Insoluto
]

def _build_pago_table(rows: List[List[Paragraph | str]]) -> Table:
    tbl = Table(rows, colWidths=_COL_WIDTHS_PAGO, hAlign="LEFT", repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), FONT_B),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"), # Alinear numéricos
    ]))
    return tbl

def _doc_rel_row(doc) -> List[Paragraph | str]:
    factura = doc.factura
    return [
        Paragraph(doc.id_documento, p_left_6),
        Paragraph(f"{factura.serie}-{factura.folio}" if factura else "", p_center_6),
        Paragraph(doc.moneda_dr, p_center_6),
        Paragraph("PPD", p_center_6), # Asumimos PPD para complementos
        Paragraph(str(doc.num_parcialidad), p_right_6),
        Paragraph(_money(doc.imp_saldo_ant), p_right_6),
        Paragraph(_money(doc.imp_pagado), p_right_6),
        Paragraph(_money(doc.imp_saldo_insoluto), p_right_6),
    ]

# --- Render Principal ---
def render_pago_pdf_bytes_from_model(
    db: Session,
    pago_id: UUID,
    *,
    logo_path: Optional[str] = None,
    preview: bool = False, # Added preview parameter
) -> bytes:
    p = load_pago_full(db, pago_id)
    if not p:
        raise ValueError("Complemento de Pago no encontrado")

    if not logo_path:
        # Adaptar la función de logos si es necesario
        if p.empresa and hasattr(p.empresa, 'logo') and p.empresa.logo:
            logo_path = os.path.join(settings.DATA_DIR, p.empresa.logo)

    watermark_text = None
    if p.estatus == EstatusPago.CANCELADO:
        watermark_text = "CANCELADO"
    elif preview and p.estatus == EstatusPago.BORRADOR: # Added preview watermark logic
        watermark_text = "BORRADOR"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # --- Dibujar Pago Info (arriba de la tabla) ---
    page_top_y = _draw_pago_header(c, p, logo_path)
    if watermark_text:
        _draw_watermark(c, watermark_text)

    y_pago_info = page_top_y - 15
    c.setFont(FONT_B, 8)
    c.drawString(CONTENT_X0, y_pago_info, "Información del Pago")
    c.line(CONTENT_X0, y_pago_info - 5, CONTENT_X1, y_pago_info - 5)
    y_pago_info -= 20

    pago_details = [
        ("Fecha de Pago:", p.fecha_pago.strftime("%Y-%m-%d %H:%M:%S") if p.fecha_pago else ""),
        ("Forma de Pago:", _forma_label(p.forma_pago_p)),
        ("Moneda:", p.moneda_p),
        ("Monto Total:", _money(p.monto)),
    ]
    if p.moneda_p != 'MXN' and p.tipo_cambio_p:
        pago_details.append(("Tipo de Cambio:", str(p.tipo_cambio_p)))

    x_curr = CONTENT_X0
    for label, value in pago_details:
        c.setFont(FONT_B, 7)
        c.drawString(x_curr, y_pago_info, label)
        c.setFont(FONT, 7)
        c.drawString(x_curr + 70, y_pago_info, value)
        y_pago_info -= 12

    # --- Tabla de Documentos Relacionados ---
    y_table_start = y_pago_info - 10
    c.setFont(FONT_B, 8)
    c.drawString(CONTENT_X0, y_table_start, "Documentos Relacionados")
    y_table_start -= 15

    docs = list(p.documentos_relacionados or [])
    header = [
        Paragraph("ID Documento", p_center_6),
        Paragraph("Serie-Folio", p_center_6),
        Paragraph("Moneda", p_center_6),
        Paragraph("Método Pago", p_center_6),
        Paragraph("No. Parc.", p_center_6),
        Paragraph("Saldo Ant.", p_center_6),
        Paragraph("Imp. Pagado", p_center_6),
        Paragraph("Saldo Insoluto", p_center_6),
    ]

    rows = [header] + [_doc_rel_row(doc) for doc in docs]
    table = _build_pago_table(rows)
    table.wrapOn(c, CONTENT_X1 - CONTENT_X0, y_table_start - AVAILABLE_BOTTOM_Y)
    table.drawOn(c, CONTENT_X0, y_table_start - table._height)

    # --- Footer ---
    _draw_pago_footer(c, p)
    c.setFont(FONT, 6)
    c.drawCentredString(PAGE_W / 2, MARGIN / 2, f"Página {c.getPageNumber()}")

    c.save()
    return buf.getvalue()
