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

# Colores Corporativos (Tema Gris Neutro)
COLOR_PRIMARY = colors.HexColor("#4A5568")   # Medium-dark gray
COLOR_ACCENT = colors.HexColor("#718096")    # Medium gray
COLOR_TEXT = colors.HexColor("#2D3748")      # Dark Gray
COLOR_TEXT_LIGHT = colors.HexColor("#A0AEC0") # Light Gray
COLOR_BG_HEADER = colors.HexColor("#F7FAFC") # Very Light Gray
COLOR_BORDER = colors.HexColor("#E2E8F0")    # Border Gray
COLOR_SECTION_BG = colors.HexColor("#EDF2F7") # Section header background

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

# ── Número a letras (español, pesos MXN) ──────────────────────────────────────
_UNIDADES = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
             "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS",
             "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
_DECENAS  = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
             "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
_CENTENAS = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
             "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

def _grupo(n: int) -> str:
    """Convierte un número 0-999 a palabras."""
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    c, resto = divmod(n, 100)
    partes = []
    if c:
        partes.append(_CENTENAS[c])
    if resto < 20:
        if resto:
            partes.append(_UNIDADES[resto])
    else:
        d, u = divmod(resto, 10)
        partes.append(_DECENAS[d])
        if u:
            partes.append(_UNIDADES[u])
    return " Y ".join(partes) if len(partes) > 1 else (partes[0] if partes else "")

def _numero_a_letras(monto: Decimal) -> str:
    """Convierte un monto Decimal a letras en español (pesos MXN)."""
    try:
        entero = int(monto)
        centavos = round((monto - entero) * 100)
        if entero == 0:
            letras = "CERO"
        elif entero < 0:
            return f"({_numero_a_letras(-monto)})"
        else:
            partes = []
            millones, resto = divmod(entero, 1_000_000)
            miles, unidades = divmod(resto, 1_000)
            if millones == 1:
                partes.append("UN MILLÓN")
            elif millones > 1:
                partes.append(f"{_grupo(millones)} MILLONES")
            if miles == 1:
                partes.append("MIL")
            elif miles > 1:
                partes.append(f"{_grupo(miles)} MIL")
            if unidades:
                partes.append(_grupo(unidades))
            letras = " ".join(filter(None, partes)) or "CERO"
        return f"{letras} PESOS {centavos:02d}/100 M.N."
    except Exception:
        return ""

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
    """
    Cabecera al estilo de facturas:
    - Logo arriba derecha (2.5" × 1.5")
    - Tira izquierda: nombre empresa + folio + fechas
    - Dos columnas: Emisor (izquierda) / Receptor (derecha)
    """
    top_y = PAGE_H - MARGIN_Y

    # ── LOGO (arriba derecha) ────────────────────────────────────────────────
    LOGO_W = 2.5 * inch
    LOGO_H = 1.5 * inch
    y_below_logo = top_y - 30

    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            scale = min(LOGO_W / iw, LOGO_H / ih)
            dw, dh = iw * scale, ih * scale
            x_logo = (PAGE_W - MARGIN_X) - LOGO_W + (LOGO_W - dw) / 2.0
            y_logo = top_y - LOGO_H + (LOGO_H - dh) / 2.0
            c.drawImage(img, x_logo, y_logo, width=dw, height=dh, mask="auto")
            y_below_logo = y_logo - 3
        except Exception:
            pass

    # ── TIRA IZQUIERDA: Etiqueta doc + Nombre empresa + Folio + Fechas ─────────
    emp = p.empresa
    y_strip = top_y - 14

    # Etiqueta del tipo de documento
    c.setFont(FONT_REGULAR, 16)
    c.setFillColor(COLOR_TEXT_LIGHT)
    c.drawString(MARGIN_X, y_strip, "PRESUPUESTO")
    y_strip -= 22

    if emp and emp.nombre_comercial:
        c.setFont(FONT_BOLD, 12)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(MARGIN_X, y_strip, emp.nombre_comercial)

    y_strip -= 18
    x_val = MARGIN_X + 85

    def _strip_row(label: str, value: str, red: bool = False):
        nonlocal y_strip
        c.setFont(FONT_BOLD, 8)
        c.setFillColor(COLOR_TEXT)
        c.drawString(MARGIN_X, y_strip, f"{label}:")
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(colors.red if red else COLOR_TEXT)
        c.drawString(x_val, y_strip, value)
        c.setFillColor(COLOR_TEXT)
        y_strip -= 12

    _strip_row("Folio", p.folio or "")
    _strip_row("Fecha emisión", p.fecha_emision.strftime("%d/%m/%Y") if p.fecha_emision else "")
    if p.fecha_vencimiento:
        _strip_row("Vence", p.fecha_vencimiento.strftime("%d/%m/%Y"), red=True)

    # ── DOS COLUMNAS: Emisor / Receptor ──────────────────────────────────────
    FULL_W = PAGE_W - 2 * MARGIN_X
    MID_X = MARGIN_X + FULL_W / 2.0
    GUTTER = 12
    x_right = MID_X + GUTTER / 2
    left_col_w = MID_X - MARGIN_X - GUTTER / 2 - 4
    right_col_w = (PAGE_W - MARGIN_X) - x_right - 4

    y_sections_start = min(y_strip - 4, y_below_logo - 4)

    def _col_row(label: str, value: Optional[str], x: float, y: float, col_w: float) -> float:
        """Dibuja una fila etiqueta+valor con word-wrap, retorna y actualizado."""
        if not value:
            return y
        lbl = f"{label}:"
        c.setFont(FONT_BOLD, 7)
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.drawString(x, y, lbl)
        lbl_w = c.stringWidth(lbl, FONT_BOLD, 7)
        vx = x + lbl_w + 4
        max_vw = col_w - (vx - x)
        c.setFont(FONT_REGULAR, 7)
        c.setFillColor(COLOR_TEXT)
        # Word-wrap simple
        words = str(value).split()
        line = ""
        yy = y
        for word in words:
            test = f"{line} {word}".strip()
            if c.stringWidth(test, FONT_REGULAR, 7) <= max_vw:
                line = test
            else:
                if line:
                    c.drawString(vx, yy, line)
                    yy -= 9
                line = word
        if line:
            c.drawString(vx, yy, line)
            yy -= 9
        return yy - 2

    # -- Emisor --
    y_col_left = y_sections_start
    c.setFont(FONT_BOLD, 8)
    c.setFillColor(COLOR_PRIMARY)
    c.drawString(MARGIN_X, y_col_left, "Emisor")
    y_col_left -= 12

    if emp:
        if emp.rfc:
            c.setFont(FONT_BOLD, 7)
            c.setFillColor(COLOR_TEXT_LIGHT)
            c.drawString(MARGIN_X, y_col_left, "RFC:")
            c.setFont(FONT_REGULAR, 7)
            c.setFillColor(COLOR_TEXT)
            c.drawString(MARGIN_X + 28, y_col_left, emp.rfc)
            y_col_left -= 10
        nombre_em = getattr(emp, "nombre", None) or emp.nombre_comercial or ""
        y_col_left = _col_row("Nombre", nombre_em, MARGIN_X, y_col_left, left_col_w)
        reg = getattr(emp, "regimen_fiscal", None)
        if reg:
            y_col_left = _col_row("Régimen", str(reg), MARGIN_X, y_col_left, left_col_w)
        dir_em = _compose_address(emp)
        if dir_em:
            y_col_left = _col_row("Dirección", dir_em.replace("\n", " "), MARGIN_X, y_col_left, left_col_w)
        tel = getattr(emp, "telefono", None)
        if tel:
            y_col_left = _col_row("Teléfono", str(tel), MARGIN_X, y_col_left, left_col_w)

    # -- Receptor --
    y_col_right = y_sections_start
    c.setFont(FONT_BOLD, 8)
    c.setFillColor(COLOR_PRIMARY)
    c.drawString(x_right, y_col_right, "Receptor")
    y_col_right -= 12

    cli = p.cliente
    if cli:
        if cli.rfc:
            c.setFont(FONT_BOLD, 7)
            c.setFillColor(COLOR_TEXT_LIGHT)
            c.drawString(x_right, y_col_right, "RFC:")
            c.setFont(FONT_REGULAR, 7)
            c.setFillColor(COLOR_TEXT)
            c.drawString(x_right + 28, y_col_right, cli.rfc)
            y_col_right -= 10
        nombre_cli = (
            getattr(cli, "nombre_razon_social", None)
            or getattr(cli, "nombre_comercial", None)
            or ""
        )
        y_col_right = _col_row("Nombre", nombre_cli, x_right, y_col_right, right_col_w)
        reg_cli = getattr(cli, "regimen_fiscal", None)
        if reg_cli:
            y_col_right = _col_row("Régimen", str(reg_cli), x_right, y_col_right, right_col_w)
        dir_cli = _compose_address(cli)
        if dir_cli:
            y_col_right = _col_row("Dirección", dir_cli.replace("\n", " "), x_right, y_col_right, right_col_w)

    header_bottom = min(y_col_left, y_col_right) - 8
    return header_bottom

def _draw_footer(c: canvas.Canvas, p: Presupuesto, y_start: float):
    """
    Footer de 3 columnas con proporciones ajustadas:
    - Izquierda (40%): Condiciones comerciales + notas
    - Centro   (33%): Datos bancarios de la empresa
    - Derecha  (27%): Subtotal / Descuento / IVA / TOTAL + total en letras
    """
    # ── Línea separadora ──────────────────────────────────────────────────────
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(1.5)
    c.line(MARGIN_X, y_start, PAGE_W - MARGIN_X, y_start)

    available_w = PAGE_W - 2 * MARGIN_X
    # Proporciones: 40% / 33% / 27%
    col_left_w  = available_w * 0.40
    col_mid_w   = available_w * 0.33
    col_right_w = available_w * 0.27

    x_mid   = MARGIN_X + col_left_w + 8
    right_x = PAGE_W - MARGIN_X
    y_top   = y_start - 18          # más holgura tras la línea separadora

    # ══════════════════════════════════════════════════════════════════════════
    # COLUMNA DERECHA: Totales
    # ══════════════════════════════════════════════════════════════════════════
    yr = y_top

    def _total_row(label: str, value: str, bold: bool = False, red: bool = False):
        nonlocal yr
        size = 10 if bold else 9
        lbl_color = COLOR_PRIMARY if bold else COLOR_TEXT
        val_color = colors.HexColor("#c0392b") if red else (COLOR_PRIMARY if bold else COLOR_TEXT)
        c.setFont(FONT_BOLD if bold else FONT_REGULAR, size)
        c.setFillColor(lbl_color)
        c.drawRightString(right_x - 85, yr, label)
        c.setFont(FONT_BOLD, size)
        c.setFillColor(val_color)
        c.drawRightString(right_x, yr, value)
        yr -= 16 if bold else 15

    _total_row("Subtotal:", _money(p.subtotal))
    try:
        if p.descuento_total and Decimal(str(p.descuento_total)) > 0:
            _total_row("Descuento:", f"-{_money(p.descuento_total)}", red=True)
    except Exception:
        pass
    try:
        if p.impuestos and Decimal(str(p.impuestos)) > 0:
            _total_row("IVA:", _money(p.impuestos))
    except Exception:
        pass

    # Línea divisoria antes del total
    yr -= 4
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.line(right_x - col_right_w + 4, yr, right_x, yr)
    yr -= 10

    _total_row("TOTAL:", _money(p.total), bold=True)

    # Total en letras — word-wrap correcto
    try:
        letras = _numero_a_letras(Decimal(str(p.total)))
        c.setFont(FONT_REGULAR, 7)
        c.setFillColor(COLOR_TEXT_LIGHT)
        max_w = col_right_w - 4
        words = letras.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if c.stringWidth(test, FONT_REGULAR, 7) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        yr -= 2
        for ln in lines[:3]:
            c.drawRightString(right_x, yr, ln)
            yr -= 10
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # COLUMNA CENTRAL: Datos bancarios
    # ══════════════════════════════════════════════════════════════════════════
    yc = y_top
    emp = p.empresa

    banco = getattr(emp, "nombre_banco", None) if emp else None
    cuenta = getattr(emp, "numero_cuenta", None) if emp else None
    clabe = getattr(emp, "clabe", None) if emp else None
    benef = getattr(emp, "beneficiario", None) if emp else None

    if any([banco, cuenta, clabe, benef]):
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(x_mid, yc, "DATOS BANCARIOS")
        yc -= 5
        c.setStrokeColor(COLOR_ACCENT)
        c.setLineWidth(0.5)
        c.line(x_mid, yc, x_mid + col_mid_w - 16, yc)
        yc -= 15

        # Ancho de la etiqueta más larga ("Beneficiario") para alinear valores
        lbl_w = c.stringWidth("Beneficiario:", FONT_BOLD, 8) + 6

        def _bank_row(label: str, value: Optional[str]):
            nonlocal yc
            if not value:
                return
            c.setFont(FONT_BOLD, 8)
            c.setFillColor(COLOR_TEXT_LIGHT)
            c.drawString(x_mid, yc, f"{label}:")
            c.setFont(FONT_REGULAR, 8)
            c.setFillColor(COLOR_TEXT)
            c.drawString(x_mid + lbl_w, yc, str(value))
            yc -= 15

        _bank_row("Banco", banco)
        _bank_row("Beneficiario", benef)
        _bank_row("No. Cuenta", cuenta)
        _bank_row("CLABE", clabe)

    # ══════════════════════════════════════════════════════════════════════════
    # COLUMNA IZQUIERDA: Condiciones + Notas
    # ══════════════════════════════════════════════════════════════════════════
    yl = y_top
    left_text_w = col_left_w - 10   # usa casi todo el ancho de la columna

    style_cond = ParagraphStyle(
        name="FooterCond",
        parent=style_small,
        fontSize=8,
        leading=12,
    )

    if p.condiciones_comerciales:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(MARGIN_X, yl, "Condiciones Comerciales:")
        yl -= 14
        para = Paragraph(p.condiciones_comerciales, style_cond)
        _, h = para.wrap(left_text_w, 400)
        yl -= h
        para.drawOn(c, MARGIN_X, yl)
        yl -= 8

    if p.notas_internas:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(MARGIN_X, yl, "Notas:")
        yl -= 14
        para = Paragraph(p.notas_internas, style_cond)
        _, h = para.wrap(left_text_w, 200)
        yl -= h
        para.drawOn(c, MARGIN_X, yl)

    # ══════════════════════════════════════════════════════════════════════════
    # Línea de firma (centrada) — 40 pts bajo el bloque más bajo
    # ══════════════════════════════════════════════════════════════════════════
    y_sig = min(yr, yc, yl) - 40
    center_doc = PAGE_W / 2
    c.setStrokeColor(COLOR_TEXT)
    c.setLineWidth(0.5)
    c.line(center_doc - 90, y_sig, center_doc + 90, y_sig)
    c.setFont(FONT_REGULAR, 8)
    c.setFillColor(COLOR_TEXT_LIGHT)
    c.drawCentredString(center_doc, y_sig - 12, "Nombre y Firma de Aceptación")

    # ── Pie de página ─────────────────────────────────────────────────────────
    c.setFont(FONT_REGULAR, 7.5)
    c.setFillColor(COLOR_TEXT_LIGHT)
    c.drawCentredString(PAGE_W / 2, MARGIN_Y / 2 + 4, "Gracias por su preferencia.")
    c.drawCentredString(PAGE_W / 2, MARGIN_Y / 2 - 6, f"Página {c.getPageNumber()}")

def _build_table(data: List[List], col_widths: List[float], section_rows: Optional[List[int]] = None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    base_style = [
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
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Borders (Minimalist)
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEBELOW', (0, 0), (-1, 0), 0, COLOR_PRIMARY),
    ]

    # Aplicar estilo especial a filas de sección
    for sr in (section_rows or []):
        base_style += [
            ('BACKGROUND', (0, sr), (-1, sr), COLOR_SECTION_BG),
            ('TEXTCOLOR', (0, sr), (-1, sr), COLOR_PRIMARY),
            ('FONTNAME', (0, sr), (-1, sr), FONT_BOLD),
            ('FONTSIZE', (0, sr), (-1, sr), 8),
            ('TOPPADDING', (0, sr), (-1, sr), 6),
            ('BOTTOMPADDING', (0, sr), (-1, sr), 6),
            ('SPAN', (0, sr), (-1, sr)),
            ('LINEABOVE', (0, sr), (-1, sr), 1, COLOR_ACCENT),
        ]

    t.setStyle(TableStyle(base_style))
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

    # Preparar datos de la tabla (con soporte de secciones y costo_unitario_recarga)
    headers = ["Descripción", "Cant.", "Precio Unit.", "Importe"]
    data = [headers]
    # Rastrear índices de filas de sección para aplicar estilo diferente
    section_row_indices: list[int] = []

    last_seccion: Optional[str] = None
    for det in presupuesto.detalles:
        seccion = getattr(det, "seccion", None) or None
        # Insertar cabecera de sección cuando cambia
        if seccion and seccion != last_seccion:
            section_row_indices.append(len(data))
            data.append([
                Paragraph(f"<b>{seccion.upper()}</b>", style_bold),
                "", "", "",
            ])
            last_seccion = seccion

        importe = (det.cantidad or 0) * (det.precio_unitario or 0)

        # Descripción principal; añadir nota de recarga si existe
        desc_parts = [det.descripcion or ""]
        recarga = getattr(det, "costo_unitario_recarga", None)
        if recarga is not None:
            try:
                desc_parts.append(f'<font size="7" color="#718096">Costo unitario recarga: {_money(recarga)}</font>')
            except Exception:
                pass
        desc_paragraph = Paragraph("<br/>".join(desc_parts), style_normal)

        row = [
            desc_paragraph,
            f"{det.cantidad:g}",
            _money(det.precio_unitario),
            _money(importe),
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
        y_content_start = _draw_header_info(c, presupuesto, logo_path)
        if watermark_text:
            _draw_watermark(c, watermark_text)
        return y_content_start

    y_cursor = draw_page_template()

    # Tabla
    table = _build_table(data, col_widths, section_row_indices)
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