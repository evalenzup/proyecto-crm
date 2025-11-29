# backend/app/services/pdf_generator.py
from __future__ import annotations

import os
from io import BytesIO
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

from sqlalchemy.orm import Session

from app.models.presupuestos import Presupuesto
from app.models.presupuestos import PresupuestoDetalle
from app.config import settings

# --- Configuración de Diseño ---
PAGE_W, PAGE_H = letter
MARGIN_X = 20 * mm
MARGIN_Y = 20 * mm

# Colores Corporativos (Tema Profesional: Azul Marino y Gris)
COLOR_PRIMARY = colors.HexColor("#1A365D")  # Navy Blue
COLOR_ACCENT = colors.HexColor("#2B6CB0")   # Lighter Blue
COLOR_TEXT = colors.HexColor("#2D3748")     # Dark Gray
COLOR_TEXT_LIGHT = colors.HexColor("#718096") # Light Gray
COLOR_BG_HEADER = colors.HexColor("#F7FAFC") # Very Light Gray
COLOR_BORDER = colors.HexColor("#E2E8F0")   # Border Gray

# Fuentes
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

# Estilos de Párrafo
styles = getSampleStyleSheet()
style_normal = ParagraphStyle(
    name="NormalCustom",
    parent=styles["Normal"],
    fontName=FONT_REGULAR,
    fontSize=9,
    leading=12,
    textColor=COLOR_TEXT
)
style_bold = ParagraphStyle(
    name="BoldCustom",
    parent=style_normal,
    fontName=FONT_BOLD,
)
style_small = ParagraphStyle(
    name="SmallCustom",
    parent=style_normal,
    fontSize=8,
    leading=10,
    textColor=COLOR_TEXT_LIGHT
)
style_right = ParagraphStyle(
    name="RightCustom",
    parent=style_normal,
    alignment=TA_RIGHT
)

# --- Helpers ---

def _money(v: Optional[Decimal | float | int]) -> str:
    try:
        return f"${Decimal(v):,.2f}"
    except Exception:
        return "$0.00"

def _draw_logo(c: canvas.Canvas, logo_path: Optional[str], x: float, y: float, max_w: float, max_h: float):
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            
            # Calcular dimensiones manteniendo aspecto
            width = max_w
            height = width * aspect
            
            if height > max_h:
                height = max_h
                width = height / aspect
                
            c.drawImage(img, x, y - height, width=width, height=height, mask="auto")
        except Exception:
            pass

def _guess_logo_path(presupuesto: Presupuesto) -> Optional[str]:
    emp = getattr(presupuesto, "empresa", None)
    if emp and getattr(emp, "logo", None):
        p = emp.logo
        if not os.path.isabs(p):
            p = os.path.join(settings.DATA_DIR, p)
        if os.path.exists(p):
            return p
    return None

def _compose_address(obj) -> Optional[str]:
    """
    Compone una dirección formateada intentando usar campos estructurados
    o un campo de texto libre si los estructurados no existen/están vacíos.
    """
    if not obj: return None
    
    # Caso 1: Si tiene campo 'direccion' (texto libre), usarlo preferentemente si no hay estructurados
    # o si es el modelo Empresa que sabemos que usa 'direccion'.
    if hasattr(obj, 'direccion') and obj.direccion:
        # Si tiene CP, lo agregamos
        cp = getattr(obj, 'codigo_postal', '')
        if cp and cp not in obj.direccion:
             return f"{obj.direccion}\nCP {cp}"
        return obj.direccion

    # Caso 2: Intentar armar con campos estructurados (Modelo Cliente)
    parts = [
        getattr(obj, 'calle', ''),
        getattr(obj, 'numero_exterior', ''),
        f"Int {getattr(obj, 'numero_interior', '')}" if getattr(obj, 'numero_interior', '') else '',
    ]
    address_line1 = " ".join(filter(None, parts))
    
    parts_line2 = [
        getattr(obj, 'colonia', ''),
        getattr(obj, 'ciudad', ''), # Puede no existir en algunos modelos
        getattr(obj, 'estado', ''), # Puede no existir en algunos modelos
        f"CP {getattr(obj, 'codigo_postal', '')}" if getattr(obj, 'codigo_postal', '') else ''
    ]
    address_line2 = ", ".join(filter(None, parts_line2))
    
    full_addr = f"{address_line1}\n{address_line2}".strip()
    return full_addr if full_addr else None

def _draw_watermark(c: canvas.Canvas, text: str):
    c.saveState()
    c.setFillColor(colors.Color(0.5, 0.5, 0.5, alpha=0.1))
    c.setFont(FONT_BOLD, 80)
    c.translate(PAGE_W / 2, PAGE_H / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()

# --- Componentes del PDF ---

def _draw_header_info(c: canvas.Canvas, p: Presupuesto, logo_path: Optional[str]) -> float:
    top_y = PAGE_H - MARGIN_Y
    
    # 1. Logo (Izquierda)
    _draw_logo(c, logo_path, MARGIN_X, top_y, 2*inch, 1*inch)
    
    # 2. Título y Folio (Derecha)
    c.saveState()
    c.setFont(FONT_BOLD, 24)
    c.setFillColor(COLOR_PRIMARY)
    c.drawRightString(PAGE_W - MARGIN_X, top_y - 20, "PRESUPUESTO")
    
    c.setFont(FONT_REGULAR, 12)
    c.setFillColor(COLOR_TEXT_LIGHT)
    c.drawRightString(PAGE_W - MARGIN_X, top_y - 40, f"Folio: {p.folio}")
    c.restoreState()

    # 3. Datos de la Empresa (Debajo del Logo)
    y_cursor = top_y - 1.2*inch
    emp = p.empresa
    if emp:
        c.setFont(FONT_BOLD, 10)
        c.setFillColor(COLOR_TEXT)
        c.drawString(MARGIN_X, y_cursor, emp.nombre_comercial or "Empresa")
        y_cursor -= 12
        
        c.setFont(FONT_REGULAR, 9)
        c.setFillColor(COLOR_TEXT_LIGHT)
        if emp.rfc:
            c.drawString(MARGIN_X, y_cursor, f"RFC: {emp.rfc}")
            y_cursor -= 12
        
        # Dirección
        dir_em = _compose_address(emp)
        if dir_em:
            # Usar textLines para manejar saltos de línea en la dirección
            text_obj = c.beginText(MARGIN_X, y_cursor)
            text_obj.setFont(FONT_REGULAR, 9)
            text_obj.setFillColor(COLOR_TEXT_LIGHT)
            for line in dir_em.split('\n'):
                text_obj.textLine(line)
            c.drawText(text_obj)
            y_cursor = text_obj.getY() - 12 # Actualizar cursor basado en donde terminó el texto

    # 4. Datos del Cliente y Fechas (Panel derecho con fondo ligero)
    panel_y_start = top_y - 0.8*inch
    panel_h = 1.2*inch
    panel_w = 3.5*inch
    panel_x = PAGE_W - MARGIN_X - panel_w
    
    # Fondo del panel
    c.setFillColor(COLOR_BG_HEADER)
    c.roundRect(panel_x, panel_y_start - panel_h, panel_w, panel_h, 4, fill=1, stroke=0)
    
    # Contenido del panel
    py = panel_y_start - 15
    px = panel_x + 10
    
    # Cliente
    cli = p.cliente
    if cli:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(px, py, "CLIENTE:")
        c.setFont(FONT_REGULAR, 9)
        c.setFillColor(COLOR_TEXT)
        c.drawString(px + 60, py, cli.nombre_comercial or "Cliente General")
        py -= 14
        if cli.rfc:
            c.setFont(FONT_REGULAR, 8)
            c.setFillColor(COLOR_TEXT_LIGHT)
            c.drawString(px + 60, py, f"RFC: {cli.rfc}")
            py -= 14

    # Fechas
    py -= 5
    c.setStrokeColor(COLOR_BORDER)
    c.line(px, py, px + panel_w - 20, py)
    py -= 15
    
    c.setFont(FONT_BOLD, 9)
    c.setFillColor(COLOR_PRIMARY)
    c.drawString(px, py, "FECHA:")
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(COLOR_TEXT)
    c.drawString(px + 60, py, p.fecha_emision.strftime("%d/%m/%Y"))
    
    if p.fecha_vencimiento:
        c.drawString(px + 150, py, "VENCE:")
        c.setFillColor(colors.red)
        c.drawString(px + 200, py, p.fecha_vencimiento.strftime("%d/%m/%Y"))

    return min(y_cursor, panel_y_start - panel_h) - 20

def _draw_footer(c: canvas.Canvas, p: Presupuesto, y_start: float):
    # Línea separadora
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(1)
    c.line(MARGIN_X, y_start, PAGE_W - MARGIN_X, y_start)
    
    y = y_start - 20
    
    # Totales (Derecha)
    right_x = PAGE_W - MARGIN_X
    
    # Estilos de totales
    def draw_total_line(label, value, is_final=False):
        nonlocal y
        c.setFont(FONT_BOLD if is_final else FONT_REGULAR, 10 if is_final else 9)
        c.setFillColor(COLOR_PRIMARY if is_final else COLOR_TEXT)
        c.drawRightString(right_x - 100, y, label)
        c.drawRightString(right_x, y, value)
        y -= 15

    draw_total_line("Subtotal:", _money(p.subtotal))
    if p.descuento_total and p.descuento_total > 0:
        draw_total_line("Descuento:", f"-{_money(p.descuento_total)}")
    draw_total_line("Impuestos:", _money(p.impuestos))
    y -= 5
    draw_total_line("TOTAL:", _money(p.total), is_final=True)

    # Condiciones y Notas (Izquierda)
    text_width = PAGE_W - MARGIN_X - MARGIN_X - 200 # Espacio restante a la izquierda
    y_text = y_start - 20
    
    if p.condiciones_comerciales:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(MARGIN_X, y_text, "Condiciones Comerciales:")
        y_text -= 12
        
        p_cond = Paragraph(p.condiciones_comerciales, style_small)
        w, h = p_cond.wrap(text_width, 200)
        p_cond.drawOn(c, MARGIN_X, y_text - h)
        y_text -= (h + 10)

    if p.notas_internas: 
        pass

    # --- Espacio para Firma ---
    # Calculamos el punto más bajo entre totales y condiciones para no encimar
    y_signature_base = min(y, y_text) - 40
    
    # Línea de firma centrada
    center_x = PAGE_W / 2
    c.setStrokeColor(COLOR_TEXT)
    c.setLineWidth(0.5)
    c.line(center_x - 80, y_signature_base, center_x + 80, y_signature_base)
    
    c.setFont(FONT_REGULAR, 8)
    c.setFillColor(COLOR_TEXT)
    c.drawCentredString(center_x, y_signature_base - 12, "Nombre y Firma de Aceptación")

    # Pie de página final (número de página)
    c.setFont(FONT_REGULAR, 8)
    c.setFillColor(COLOR_TEXT_LIGHT)
    c.drawCentredString(PAGE_W/2, MARGIN_Y/2, "Gracias por su preferencia.")
    c.drawCentredString(PAGE_W/2, MARGIN_Y/2 - 10, f"Página {c.getPageNumber()}")

def _build_table(data: List[List], col_widths: List[float]) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXT),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), # Cantidad, Precio, Importe a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Borders (Minimalist)
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEBELOW', (0, 0), (-1, 0), 0, COLOR_PRIMARY), # Header underline hidden by bg
        
        # Zebra Striping (Optional - clean look preferred)
        # ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_HEADER]),
    ]))
    return t

def render_presupuesto_pdf_bytes(presupuesto: Presupuesto, db: Session) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setTitle(f"Presupuesto {presupuesto.folio}")

    logo_path = _guess_logo_path(presupuesto)
    
    # Watermark si no es borrador/enviado
    watermark_text = None
    if presupuesto.estado not in ["BORRADOR", "ENVIADO"]:
        watermark_text = presupuesto.estado

    # Preparar datos de la tabla
    headers = ["Descripción", "Cant.", "Precio Unit.", "Importe"]
    data = [headers]
    
    for det in presupuesto.detalles:
        importe = (det.cantidad or 0) * (det.precio_unitario or 0)
        row = [
            Paragraph(det.descripcion or "", style_normal),
            f"{det.cantidad:g}", # Elimina ceros decimales innecesarios
            _money(det.precio_unitario),
            _money(importe)
        ]
        data.append(row)

    # Anchos de columna
    available_width = PAGE_W - 2*MARGIN_X
    col_widths = [
        available_width * 0.55, # Descripción
        available_width * 0.10, # Cantidad
        available_width * 0.17, # Precio
        available_width * 0.18  # Importe
    ]

    # Renderizado
    def draw_page_template():
        # _draw_header_band(c) # REMOVED
        y_content_start = _draw_header_info(c, presupuesto, logo_path)
        if watermark_text:
            _draw_watermark(c, watermark_text)
        return y_content_start

    y_cursor = draw_page_template()
    
    # Tabla
    table = _build_table(data, col_widths)
    w, h = table.wrap(available_width, PAGE_H) # Wrap preliminar
    
    # Lógica de paginación manual básica para ReportLab Canvas
    # Nota: Platypus SimpleDocTemplate es más fácil, pero Canvas da control absoluto.
    # Aquí usamos Canvas directo como en el código original, pero mejorado.
    
    table.splitByRow = 1
    
    # Espacio disponible en primera página
    space_available = y_cursor - MARGIN_Y - 2*inch # Dejar espacio para footer
    
    # Dibujar tabla
    # Si la tabla es muy larga, ReportLab Table.split() ayuda
    parts = table.split(available_width, space_available)
    
    for i, part in enumerate(parts):
        if i > 0:
            c.showPage()
            draw_page_template()
            y_cursor = PAGE_H - MARGIN_Y - 1.5*inch # Margen superior en páginas siguientes
        
        w, h = part.wrapOn(c, available_width, PAGE_H)
        part.drawOn(c, MARGIN_X, y_cursor - h)
        y_cursor -= (h + 20) # Espacio después de la tabla

    # Footer (siempre al final de la última tabla, o en nueva página si no cabe)
    if y_cursor < MARGIN_Y + 1.5*inch:
        c.showPage()
        draw_page_template()
        y_cursor = PAGE_H - MARGIN_Y - 1.5*inch

    _draw_footer(c, presupuesto, y_cursor)
    
    c.save()
    return buf.getvalue()

def generate_presupuesto_pdf(presupuesto: Presupuesto, db: Session) -> bytes:
    return render_presupuesto_pdf_bytes(presupuesto, db)