# app/services/pdf_factura.py
from __future__ import annotations

import os
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlencode
from collections import defaultdict

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

from sqlalchemy.orm import Session, selectinload

from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.config import settings

# Catálogos para etiquetas CLAVE — DESCRIPCIÓN
from app.catalogos_sat.regimenes_fiscales import obtener_todos_regimenes
from app.catalogos_sat.facturacion import (
    obtener_todos_metodos_pago,
    obtener_todas_formas_pago,
    obtener_todos_usos_cfdi,
    obtener_todas_tipos_relacion,
)

# (Opcional) catálogo de UNIDADES; si no existe, se maneja con fallback.
try:
    from app.catalogos_sat.unidades import obtener_todas_unidades as _fetch_unidades_sat
except Exception:  # pragma: no cover
    _fetch_unidades_sat = None

# ──────────────────────────────────────────────────────────────────────────────
# Layout / estilos
# ──────────────────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = letter
MARGIN      = 0.5 * inch
LOGO_W      = 2.5 * inch
LOGO_H      = 1.5 * inch
CBB_SIZE    = 1.20 * inch   # ~86pt

FONT        = "Helvetica"
FONT_B      = "Helvetica-Bold"

CONTENT_X0  = MARGIN
CONTENT_Y0  = MARGIN
CONTENT_X1  = PAGE_W - MARGIN
CONTENT_Y1  = PAGE_H - MARGIN

FOOTER_TOP_Y        = CONTENT_Y0 + 2.90 * inch
AVAILABLE_BOTTOM_Y  = FOOTER_TOP_Y + 0.10 * inch

styles = getSampleStyleSheet()
p_center_6 = ParagraphStyle(
    name="p_center_6",
    parent=styles["Normal"],
    fontName=FONT,
    fontSize=6,
    leading=7,
    alignment=1,  # CENTER
)
p_left_6 = ParagraphStyle(
    name="p_left_6",
    parent=styles["Normal"],
    fontName=FONT,
    fontSize=6,
    leading=7,
    alignment=0,  # LEFT
)
p_right_6 = ParagraphStyle(
    name="p_right_6",
    parent=styles["Normal"],
    fontName=FONT,
    fontSize=6,
    leading=7,
    alignment=2,  # RIGHT
)

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades numéricas / formato
# ──────────────────────────────────────────────────────────────────────────────
def _money(v: Optional[Decimal | float | int]) -> str:
    try:
        return f"${Decimal(v):,.2f}"
    except Exception:
        try:
            return f"${float(v):,.2f}"
        except Exception:
            return "$0.00"

def _num(v) -> str:
    try:
        return f"{Decimal(v):,.2f}"
    except Exception:
        try:
            return f"{float(v):,.2f}"
        except Exception:
            return "0.00"

def _tt_param_17_6(total: Decimal | float | int) -> str:
    d = Decimal(str(total)).quantize(Decimal("0.000000"), rounding=ROUND_HALF_UP)
    s = f"{d}"
    ent, frac = s.split(".")
    return f"{ent.zfill(17)}.{frac[:6].ljust(6, '0')}"

# ──────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ──────────────────────────────────────────────────────────────────────────────
def load_factura_full(db: Session, factura_id: UUID) -> Optional[Factura]:
    return (
        db.query(Factura)
        .options(
            selectinload(Factura.empresa),
            selectinload(Factura.cliente),
            selectinload(Factura.conceptos),
        )
        .filter(Factura.id == factura_id)
        .first()
    )

# ──────────────────────────────────────────────────────────────────────────────
# Catálogos CLAVE — DESCRIPCIÓN
# ──────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _regimen_map() -> dict:
    return {x["clave"]: x["descripcion"] for x in obtener_todos_regimenes()}

def _regimen_label(clave: Optional[str]) -> Optional[str]:
    if not clave:
        return None
    d = _regimen_map().get(clave)
    return f"{clave} — {d}" if d else clave

@lru_cache(maxsize=1)
def _metodo_map() -> dict:
    return {x["clave"]: x["descripcion"] for x in obtener_todos_metodos_pago()}

def _metodo_label(clave: Optional[str]) -> Optional[str]:
    if not clave:
        return None
    d = _metodo_map().get(clave)
    return f"{clave} — {d}" if d else clave

@lru_cache(maxsize=1)
def _forma_map() -> dict:
    return {x["clave"]: x["descripcion"] for x in obtener_todas_formas_pago()}

def _forma_label(clave: Optional[str]) -> Optional[str]:
    if not clave:
        return None
    d = _forma_map().get(clave)
    clave_fmt = f"{int(clave):02d}" if clave.isdigit() else clave
    return f"{clave_fmt} — {d}" if d else clave_fmt

@lru_cache(maxsize=1)
def _uso_map() -> dict:
    return {x["clave"]: x["descripcion"] for x in obtener_todos_usos_cfdi()}

def _uso_label(clave: Optional[str]) -> Optional[str]:
    if not clave:
        return None
    d = _uso_map().get(clave)
    return f"{clave} — {d}" if d else clave

@lru_cache(maxsize=1)
def _rel_map() -> dict:
    return {x["clave"]: x["descripcion"] for x in obtener_todas_tipos_relacion()}

def _rel_label(clave: Optional[str]) -> Optional[str]:
    if not clave:
        return None
    d = _rel_map().get(clave)
    return f"{clave} — {d}" if d else clave

# Unidades SAT (opcional)
@lru_cache(maxsize=1)
def _unidad_map() -> dict:
    if _fetch_unidades_sat is None:
        return {}
    try:
        return {u["clave"]: u.get("descripcion") for u in (_fetch_unidades_sat() or [])}
    except Exception:
        return {}

def _unidad_label(clave: Optional[str], desc_hint: Optional[str] = None) -> str:
    if not clave:
        return ""
    d = desc_hint or _unidad_map().get(clave)
    return f"{clave}-{d}" if d else str(clave)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de texto / dibujo
# ──────────────────────────────────────────────────────────────────────────────
def _wrap_lines(c: canvas.Canvas, text: str, max_w: float, font=FONT, size=7) -> List[str]:
    if not text:
        return []
    c.setFont(font, size)

    def slice_to_fit(s: str) -> List[str]:
        out = []
        i = 0
        n = len(s)
        while i < n:
            lo, hi, cut = 1, n - i, 1
            while lo <= hi:
                mid = (lo + hi) // 2
                if c.stringWidth(s[i:i+mid], font, size) <= max_w:
                    cut = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            out.append(s[i:i+cut])
            i += cut
        return out

    out: List[str] = []
    line = ""
    for token in text.split(" "):
        test = token if not line else f"{line} {token}"
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            if line:
                out.append(line)
                line = ""
            out.extend(slice_to_fit(token))
    if line:
        out.append(line)
    return out

def _draw_label_wrap(c: canvas.Canvas, label: str, value: Optional[str],
                     x: float, y: float, max_w_value: float,
                     font_label=FONT_B, font_value=FONT, size=7, gap=4) -> float:
    if not value:
        return y
    c.setFont(font_label, size)
    c.drawString(x, y, f"{label}:")
    vx = x + c.stringWidth(f"{label}:", font_label, size) + 6
    max_w = max(10.0, max_w_value - (vx - x))
    lines = _wrap_lines(c, value, max_w, font=font_value, size=size)
    c.setFont(font_value, size)
    yy = y
    for ln in lines:
        c.drawString(vx, yy, ln)
        yy -= (size + 2)
    return yy - gap

def _draw_label_wrap_up(c: canvas.Canvas, label: str, value: Optional[str],
                        x: float, y: float, max_w_value: float,
                        font_label=FONT_B, font_value=FONT, size=8, gap=4) -> float:
    if not value:
        return y
    c.setFont(font_label, size)
    c.drawString(x, y, f"{label}:")
    vx = x + c.stringWidth(f"{label}:", font_label, size) + 6
    max_w = max(10.0, max_w_value - (vx - x))
    lines = _wrap_lines(c, value, max_w, font=font_value, size=size)
    c.setFont(font_value, size)
    yy = y
    for ln in lines:
        c.drawString(vx, yy, ln)
        yy += (size + 2)  # hacia ARRIBA
    return yy + gap

def _compose_address(obj) -> Optional[str]:
    if not obj:
        return None
    direccion_txt = getattr(obj, "direccion", None)
    cp = getattr(obj, "codigo_postal", None)
    if direccion_txt:
        direccion_txt = str(direccion_txt).strip()
        return f"{direccion_txt} — CP {cp}" if cp else direccion_txt
    calle = getattr(obj, "calle", None)
    ne = getattr(obj, "numero_exterior", None)
    ni = getattr(obj, "numero_interior", None)
    col = getattr(obj, "colonia", None)
    cd  = getattr(obj, "ciudad", None)
    a = " ".join([p for p in [calle, ne, f"Int {ni}" if ni else None] if p])
    b = ", ".join([p for p in [col, cd] if p])
    cpo = f"CP {cp}" if cp else None
    parts = [p for p in [a if a else None, b if b else None, cpo] if p]
    return " — ".join(parts) if parts else None

def _draw_watermark(c: canvas.Canvas, text: str):
    c.saveState()
    c.setFillColor(colors.Color(0.85, 0.1, 0.1, alpha=0.12))
    c.setFont(FONT_B, 80)
    c.translate(PAGE_W / 2, PAGE_H / 2)
    c.rotate(45)
    w = c.stringWidth(text, FONT_B, 80)
    c.drawString(-w / 2, 0, text)
    c.restoreState()

# ──────────────────────────────────────────────────────────────────────────────
# Logo y CBB
# ──────────────────────────────────────────────────────────────────────────────
def _guess_logo_path_for_factura(f: Factura) -> Optional[str]:
    try:
        emp = getattr(f, "empresa", None)
        candidates: List[str] = []
        if emp is None:
            return None
        if getattr(emp, "logo", None):
            p = emp.logo
            if not os.path.isabs(p):
                p = os.path.join(settings.DATA_DIR, p)
            candidates.append(p)
        if getattr(emp, "id", None):
            candidates.append(os.path.join(settings.DATA_DIR, "logos", "empresas", f"{emp.id}.png"))
            candidates.append(os.path.join(settings.DATA_DIR, "logos", f"{emp.id}.png"))
        for p in candidates:
            if p and os.path.exists(p):
                return p
    except Exception:
        pass
    return None

def _tt_param(total) -> str:
    return f"{Decimal(total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

def _build_sat_qr_url(f) -> str:
    base = "https://verificacfdi.facturaelectronica.sat.gob.mx/"

    uuid = (getattr(f, "cfdi_uuid", None) or "").strip()
    re = (getattr(getattr(f, "empresa", None), "rfc", None) or "").strip().upper()
    rr = (getattr(getattr(f, "cliente", None), "rfc", None) or "").strip().upper()
    total = getattr(f, "total", None)
    sello_cfdi = (getattr(f, "sello_cfdi", None) or "").strip()
    fe = sello_cfdi[-8:] if sello_cfdi else ""

    if uuid and re and rr and (total is not None):
        params = {"id": uuid, "re": re, "rr": rr, "tt": _tt_param(total)}
        query = urlencode(params)
        if fe:
            query += f"&fe={fe}"
        return base + "?" + query

    return base

def _draw_cbb_qr(c: canvas.Canvas, f: Factura) -> bool:
    try:
        import qrcode
        url = _build_sat_qr_url(f)
        qr = qrcode.QRCode(
            version=2,
            error_correction=getattr(__import__("qrcode.constants"), "ERROR_CORRECT_M"),
            box_size=10,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        ir = ImageReader(img.convert("RGB"))

        x = CONTENT_X1 - CBB_SIZE
        y = FOOTER_TOP_Y - CBB_SIZE - CBB_SIZE - 8
        c.drawImage(ir, x, y, width=CBB_SIZE, height=CBB_SIZE, mask="auto")
        return True
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
def _draw_header(c: canvas.Canvas, f: Factura, logo_path: Optional[str]) -> float:
    # LOGO (arriba derecha)
    y_below_logo = CONTENT_Y1 - 38
    if logo_path:
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            scale = min(LOGO_W / iw, LOGO_H / ih)
            dw, dh = iw * scale, ih * scale
            x_logo = CONTENT_X1 - LOGO_W + (LOGO_W - dw) / 2.0
            y_logo = CONTENT_Y1 - LOGO_H + (LOGO_H - dh) / 2.0
            c.drawImage(img, x_logo, y_logo, width=dw, height=dh, mask="auto")
            y_below_logo = y_logo - 3
        except Exception:
            pass

    # Datos simples (izquierda)
    y_left = CONTENT_Y1 - 38
    x_space = 70
    c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Fecha emisión:")
    c.setFont(FONT, 8);   c.drawString(CONTENT_X0 + x_space, y_left, (f.fecha_emision or datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S"))
    y_left -= 12
    if f.serie:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Serie y Folio:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0 + x_space, y_left, f"{f.serie} {f.folio}"); y_left -= 12
    else:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Folio:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0 + x_space, y_left, str(f.folio)); y_left -= 12
    if f.cfdi_uuid:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "UUID:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0 + x_space, y_left, f.cfdi_uuid); y_left -= 12
    if getattr(f, "fecha_timbrado", None):
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Fecha timbrado:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0 + x_space, y_left, f.fecha_timbrado.strftime("%Y-%m-%d %H:%M:%S"))
        y_left -= 12
    if f.lugar_expedicion:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Lugar de expedición:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0 + x_space + 20, y_left, f.lugar_expedicion)
        y_left -= 12

    # Dos columnas (Emisor / Receptor)
    MID_X  = (CONTENT_X0 + CONTENT_X1) / 2.0
    GUTTER = 12
    x_right = MID_X + GUTTER / 2
    left_w  = max(120.0, MID_X - CONTENT_X0 - GUTTER/2 - 4)
    right_w = max(120.0, CONTENT_X1 - x_right - 4)

    y_sections_start = min(y_left - 4, y_below_logo)

    # Emisor
    y_left = y_sections_start
    c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, y_left, "Emisor"); y_left -= 12
    emp = f.empresa
    if emp:
        # Título
        c.setFont(FONT_B, 10)
        c.drawString(CONTENT_X0, CONTENT_Y1 - 24, emp.nombre_comercial or "CFDI 4.0")
        if getattr(emp, "rfc", None):
            c.setFont(FONT_B, 7); c.drawString(CONTENT_X0, y_left, "RFC:")
            c.setFont(FONT, 7);   c.drawString(CONTENT_X0 + 28, y_left, emp.rfc)
            y_left -= 10
        nombre = getattr(emp, "nombre", None) or getattr(emp, "nombre_comercial", None) or ""
        if nombre:
            y_left = _draw_label_wrap(c, "Nombre", nombre, CONTENT_X0, y_left, left_w)
        if getattr(emp, "regimen_fiscal", None):
            reg_lbl = _regimen_label(emp.regimen_fiscal) or emp.regimen_fiscal
            y_left = _draw_label_wrap(c, "Régimen", reg_lbl, CONTENT_X0, y_left, left_w)
        dir_em = _compose_address(emp)
        if dir_em:
            y_left = _draw_label_wrap(c, "Dirección", dir_em, CONTENT_X0, y_left, left_w)
        tel = getattr(emp, "telefono", None)
        if tel:
            y_left = _draw_label_wrap(c, "Teléfono", tel, CONTENT_X0, y_left, left_w)
        mail = getattr(emp, "email", None)
        if mail:
            y_left = _draw_label_wrap(c, "Correo", mail, CONTENT_X0, y_left, left_w)

    # Receptor
    y_right = y_sections_start
    c.setFont(FONT_B, 8); c.drawString(x_right, y_right, "Receptor"); y_right -= 12
    cli = f.cliente
    if cli:
        if getattr(cli, "rfc", None):
            c.setFont(FONT_B, 7); c.drawString(x_right, y_right, "RFC:")
            c.setFont(FONT, 7);   c.drawString(x_right + 24, y_right, cli.rfc)
            y_right -= 10
        nombre_r = getattr(cli, "nombre_razon_social", None) or getattr(cli, "nombre_comercial", None) or getattr(cli, "nombre", "") or ""
        if nombre_r:
            y_right = _draw_label_wrap(c, "Nombre", nombre_r, x_right, y_right, right_w)
        if getattr(cli, "regimen_fiscal", None):
            reg_lbl_r = _regimen_label(cli.regimen_fiscal) or cli.regimen_fiscal
            y_right = _draw_label_wrap(c, "Régimen", reg_lbl_r, x_right, y_right, right_w)
        dir_rc = _compose_address(cli) or (f"CP {cli.codigo_postal}" if getattr(cli, "codigo_postal", None) else None)
        if dir_rc:
            y_right = _draw_label_wrap(c, "Dirección", dir_rc, x_right, y_right, right_w)

    header_bottom = min(y_left, y_right) - 8
    return max(header_bottom, AVAILABLE_BOTTOM_Y + 60)

# ──────────────────────────────────────────────────────────────────────────────
# Conversión a letra
# ──────────────────────────────────────────────────────────────────────────────
_UNIDADES = (
    "CERO","UNO","DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE",
    "DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE",
    "DIECIOCHO","DIECINUEVE","VEINTE","VEINTIUNO","VEINTIDOS","VEINTITRES",
    "VEINTICUATRO","VEINTICINCO","VEINTISEIS","VEINTISIETE","VEINTIOCHO","VEINTINUEVE"
)
_DECENAS = ("","","VEINTE","TREINTA","CUARENTA","CINCUENTA","SESENTA","SETENTA","OCHENTA","NOVENTA")
_CENTENAS = ("","CIENTO","DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS")

def _centenas_a_letras(n: int) -> str:
    if n == 0: return "CERO"
    if n == 100: return "CIEN"
    c = n // 100
    d = n % 100
    pref = (_CENTENAS[c] + " ") if c else ""
    if d < 30:
        return (pref + (_UNIDADES[d] if d > 0 else "")).strip()
    dec = d // 10
    uni = d % 10
    if uni == 0:
        return (pref + _DECENAS[dec]).strip()
    return (pref + _DECENAS[dec] + " Y " + _UNIDADES[uni]).strip()

def _numero_a_letras_enteros(n: int) -> str:
    if n == 0: return "CERO"
    if n < 0: return "MENOS " + _numero_a_letras_enteros(-n)
    partes: List[str] = []
    grupos = [(10**12,"BILLONES"), (10**9,"MIL MILLONES"), (10**6,"MILLONES"), (10**3,"MIL"), (1,"")]
    resto = n
    for val, nom in grupos:
        if resto >= val:
            cant = resto // val
            resto %= val
            if val == 10**6 and cant == 1:
                partes.append("UN MILLON")
            elif val == 10**12 and cant == 1:
                partes.append("UN BILLON")
            elif val == 10**3 and cant == 1:
                partes.append("MIL")
            else:
                partes.append((_centenas_a_letras(cant) + (" " + nom if nom else "")).strip())
    return " ".join(partes).replace("  "," ").strip()

def _importe_con_letra(total: Decimal | float | int, moneda: str = "MXN") -> str:
    d = Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    entero = int(d)
    cent = int((d - Decimal(entero)) * 100)
    letras = _numero_a_letras_enteros(entero)
    if (moneda or "").upper() == "USD":
        singular, plural, leyenda = "DOLAR", "DOLARES", "USD"
    else:
        singular, plural, leyenda = "PESO", "PESOS", "M.N."
    es_uno = (abs(entero) == 1)
    palabra = singular if es_uno else plural
    return f"{letras} {palabra} {cent:02d}/100 {leyenda}"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers impuestos (footer)
# ──────────────────────────────────────────────────────────────────────────────
def _pct(v: Decimal, places: int = 2) -> str:
    q = Decimal("1." + "0"*places)
    return f"{(v * Decimal('100')).quantize(q, rounding=ROUND_HALF_UP)}%"

def _compute_tax_breakdown(f: Factura):
    trasladados = defaultdict(Decimal)  # key: (nombre, tasa_decimal)
    retenidos   = defaultdict(Decimal)

    for c in (getattr(f, "conceptos", None) or []):
        try:
            cantidad = Decimal(str(c.cantidad or 0))
            valor    = Decimal(str(c.valor_unitario or 0))
            desc     = Decimal(str(c.descuento or 0))
        except Exception:
            cantidad = Decimal(c.cantidad or 0)
            valor    = Decimal(c.valor_unitario or 0)
            desc     = Decimal(c.descuento or 0)

        base = (cantidad * valor) - desc
        if base < 0:
            base = Decimal("0")

        iva_tasa = getattr(c, "iva_tasa", None)
        if iva_tasa is not None:
            try:
                t = Decimal(str(iva_tasa))
                if t > 0:
                    trasladados[("IVA", t)] += (base * t)
            except Exception:
                pass

        ret_iva_tasa = getattr(c, "ret_iva_tasa", None)
        if ret_iva_tasa is not None:
            try:
                t = Decimal(str(ret_iva_tasa))
                if t > 0:
                    retenidos[("IVA", t)] += (base * t)
            except Exception:
                pass

        ret_isr_tasa = getattr(c, "ret_isr_tasa", None)
        if ret_isr_tasa is not None:
            try:
                t = Decimal(str(ret_isr_tasa))
                if t > 0:
                    retenidos[("ISR", t)] += (base * t)
            except Exception:
                pass

    tras_list = sorted(trasladados.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    ret_list  = sorted(retenidos.items(),   key=lambda kv: (kv[0][0], kv[0][1]))
    return tras_list, ret_list

def _tfd_cadena_original_11(f: Factura) -> str | None:
    uuid = (getattr(f, "cfdi_uuid", None) or "").strip()
    sello_cfd = (getattr(f, "sello_cfdi", None) or "").strip()
    rfc_pac = (getattr(f, "rfc_proveedor_sat", None) or "").strip()
    nocer_sat = (getattr(f, "no_certificado_sat", None) or "").strip()
    ft = getattr(f, "fecha_timbrado", None)
    if not (uuid and sello_cfd and rfc_pac and nocer_sat and ft):
        return None
    try:
        fecha_iso = ft.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None
    return f"||1.1|{uuid}|{fecha_iso}|{rfc_pac}|{sello_cfd}|{nocer_sat}||"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de párrafo / KV para el footer
# ──────────────────────────────────────────────────────────────────────────────
def _draw_paragraph_box(c: canvas.Canvas, text: str, x: float, y_top: float,
                        max_w: float, font=FONT, size=6, leading=7) -> float:
    if not text:
        return y_top
    lines = _wrap_lines(c, text, max_w, font=font, size=size)
    c.setFont(font, size)
    y = y_top
    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading
    return y

def _draw_kv_block(c: canvas.Canvas, label: str, value: str | None, x: float, y_top: float, max_w: float,
                   label_font=FONT_B, label_size=8, value_font=FONT, value_size=6, value_leading=7, gap=6) -> float:
    if not value:
        return y_top
    c.setFont(label_font, label_size)
    c.drawString(x, y_top, f"{label}:")
    y = y_top - (label_size + 2)
    y = _draw_paragraph_box(c, value, x, y, max_w, font=value_font, size=value_size, leading=value_leading)
    return y - gap

# ──────────────────────────────────────────────────────────────────────────────
# Footer (QR fijo, bloque TFD a la izquierda, fila de pagos + totales)
# ──────────────────────────────────────────────────────────────────────────────
def _draw_footer(c: canvas.Canvas, f: Factura, is_last_page: bool):
    c.setStrokeColor(colors.lightgrey)
    c.line(CONTENT_X0, FOOTER_TOP_Y, CONTENT_X1, FOOTER_TOP_Y)

    base_y = FOOTER_TOP_Y - 12

    uso_cfdi_lbl = _uso_label(f.uso_cfdi) or f.uso_cfdi or ""
    metodo_lbl = _metodo_label(f.metodo_pago) or f.metodo_pago or ""
    forma_lbl  = _forma_label(f.forma_pago) or f.forma_pago or ""
    moneda_lbl = "Peso Mexicano" if (f.moneda or "MXN") == "MXN" else (f.moneda or "")
    tipo_cambio_lbl = f.tipo_cambio or ""

    c.setFont(FONT_B, 8)

    if uso_cfdi_lbl:
        c.drawString(CONTENT_X0, base_y, "Uso de CFDI:")
        c.setFont(FONT, 8); c.drawString(CONTENT_X0+90, base_y, uso_cfdi_lbl); base_y -= 12
    if metodo_lbl:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, base_y, "Método de pago:")
        c.setFont(FONT, 8); c.drawString(CONTENT_X0+90, base_y, metodo_lbl); base_y -= 12
    if forma_lbl:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, base_y, "Forma de pago:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0+90, base_y, forma_lbl); base_y -= 12
    if moneda_lbl:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, base_y, "Moneda:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0+90, base_y, moneda_lbl); base_y -= 12
    if tipo_cambio_lbl and moneda_lbl and moneda_lbl != "Peso Mexicano":
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, base_y, "Tipo de cambio:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0+90, base_y, str(tipo_cambio_lbl)); base_y -= 12
    if f.observaciones:
        c.setFont(FONT_B, 8); c.drawString(CONTENT_X0, base_y, "Observaciones:")
        c.setFont(FONT, 8);   c.drawString(CONTENT_X0+90, base_y, str(f.observaciones)); base_y -= 12

    # Totales (derecha) con desglose
    right_x = CONTENT_X1
    espacio_y = 12
    totales_y = FOOTER_TOP_Y - espacio_y
    c.setFont(FONT_B, 8)
    c.drawRightString(right_x, totales_y, f"Subtotal: {_money(f.subtotal)}"); totales_y -= espacio_y

    tras_list, ret_list = _compute_tax_breakdown(f)
    if tras_list:
        for (imp_name, tasa), monto in tras_list:
            c.drawRightString(right_x, totales_y, f"{imp_name} {_pct(tasa, 2)}: {_money(monto)}")
            totales_y -= espacio_y
    elif (f.impuestos_trasladados or 0) > 0:
        c.drawRightString(right_x, totales_y, f"Impuestos trasladados: {_money(f.impuestos_trasladados)}"); totales_y -= espacio_y

    if ret_list:
        for (imp_name, tasa), monto in ret_list:
            c.drawRightString(right_x, totales_y, f"Retención {imp_name} {_pct(tasa, 4)}: {_money(monto)}")
            totales_y -= espacio_y
    elif (f.impuestos_retenidos or 0) > 0:
        c.drawRightString(right_x, totales_y, f"Impuestos retenidos: {_money(f.impuestos_retenidos)}"); totales_y -= espacio_y

    c.drawRightString(right_x, totales_y, f"Total: {_money(f.total)}"); totales_y -= espacio_y

    # QR (abajo derecha)
    _draw_cbb_qr(c, f)

    # Bloque timbrado (texto envuelto a la izquierda del QR)
    base_y -= 8
    qr_left_x = CONTENT_X1 - CBB_SIZE
    MARGIN_R = 16
    max_w = (qr_left_x - MARGIN_R) - CONTENT_X0

    def draw_block(label, value, y, font_label=FONT_B, font_value=FONT, size=6):
        if not value:
            return y
        c.setFont(font_label, size); c.drawString(CONTENT_X0, y, label)
        y -= 10
        lines = _wrap_lines(c, value, max_w, font=font_value, size=size)
        c.setFont(font_value, size)
        for ln in lines:
            c.drawString(CONTENT_X0, y, ln); y -= 9
        return y - 4

    y = base_y
    y = draw_block("Sello digital del CFDI:", getattr(f, "sello_cfdi", None), y)
    y = draw_block("Sello digital del SAT:", getattr(f, "sello_sat", None), y)
    y = draw_block("Cadena original:", _tfd_cadena_original_11(f), y)

# ──────────────────────────────────────────────────────────────────────────────
# Tabla de conceptos
# ──────────────────────────────────────────────────────────────────────────────
# NUEVOS ANCHOS (6 columnas) — total 7.50"
_COL_WIDTHS = [
    0.80*inch,  # ClaveProdServ
    3.00*inch,  # Descripción
    1.10*inch,  # Unidad (CLAVE-descripción)
    0.60*inch,  # Cantidad
    1.00*inch,  # Valor unitario
    1.00*inch,  # Importe (cantidad x valor unitario)
]

def _build_table(rows: List[List[Paragraph | str]]) -> Table:
    tbl = Table(rows, colWidths=_COL_WIDTHS, hAlign="LEFT", repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), FONT_B),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 6),

        # Alinear numéricas a la derecha: cols 3..5 en filas de datos (desde 1)
        ("ALIGN", (3,1), (5,-1), "RIGHT"),
        # Descripción a la izquierda
        ("ALIGN", (1,1), (1,-1), "LEFT"),
        # Unidad centrada
        ("ALIGN", (2,1), (2,-1), "CENTER"),
    ]))
    return tbl

def _concept_base_vals(cpt: FacturaDetalle) -> Tuple[Decimal, Decimal]:
    """Regresa (cantidad, valor_unitario) como Decimal."""
    cantidad = Decimal(str(getattr(cpt, "cantidad", 0) or 0))
    valor_unitario = Decimal(str(getattr(cpt, "valor_unitario", 0) or 0))
    return cantidad, valor_unitario

def _concept_row(cpt: FacturaDetalle) -> List[Paragraph | str]:
    cantidad, valor_unitario = _concept_base_vals(cpt)

    # Importe = cantidad × valor_unitario (sin descuentos ni impuestos)
    importe = cantidad * valor_unitario

    # Unidad (CLAVE-descripción) con fallback
    unidad_desc_hint = getattr(cpt, "unidad_descripcion", None) or getattr(cpt, "clave_unidad_desc", None)
    unidad_label = _unidad_label(getattr(cpt, "clave_unidad", None), unidad_desc_hint)

    return [
        Paragraph(str(getattr(cpt, "clave_producto", "") or ""), p_center_6),  # 0 Clave
        Paragraph(str(getattr(cpt, "descripcion", "") or ""), p_left_6),       # 1 Descripción
        Paragraph(str(unidad_label or ""), p_center_6),                        # 2 Unidad (clave-descripción)
        Paragraph(_num(cantidad), p_right_6),                                   # 3 Cantidad
        Paragraph(_num(valor_unitario), p_right_6),                             # 4 Valor unitario
        Paragraph(_num(importe), p_right_6),                                    # 5 Importe
    ]

# ──────────────────────────────────────────────────────────────────────────────
# Render principal
# ──────────────────────────────────────────────────────────────────────────────
def render_factura_pdf_bytes_from_model(
    db: Session,
    factura_id: UUID,
    *,
    preview: bool = False,
    logo_path: Optional[str] = None,
) -> bytes:
    f = load_factura_full(db, factura_id)
    if not f:
        raise ValueError("Factura no encontrada")

    if not logo_path:
        logo_path = _guess_logo_path_for_factura(f)

    # Marca de agua
    watermark_text = None
    if preview and f.estatus == "BORRADOR":
        watermark_text = "PREVISUALIZACIÓN"
    elif f.estatus == "CANCELADA":
        watermark_text = "CANCELADO"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    conceptos = list(f.conceptos or [])
    header = [
        Paragraph("Clave ProdServ", p_center_6),   # 0
        Paragraph("Descripción", p_center_6),      # 1
        Paragraph("Unidad", p_center_6),           # 2 (CLAVE-descripción)
        Paragraph("Cantidad", p_center_6),         # 3
        Paragraph("Valor Unitario", p_center_6),   # 4
        Paragraph("Importe", p_center_6),          # 5 (cant x v.u.)
    ]

    i = 0
    total = len(conceptos)
    page_top_y: float = 0.0

    def new_page():
        nonlocal page_top_y
        c.setFont(FONT, 6)
        page_top_y = _draw_header(c, f, logo_path)
        if watermark_text:
            _draw_watermark(c, watermark_text)

    new_page()

    while i < total or total == 0:
        rows = [header]
        y_available = page_top_y - AVAILABLE_BOTTOM_Y
        tbl = _build_table(rows)
        _, h = tbl.wrapOn(c, CONTENT_X1 - CONTENT_X0, y_available)

        j = i
        while j < total:
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
        tbl.wrapOn(c, CONTENT_X1 - CONTENT_X0, y_available)
        tbl.drawOn(c, CONTENT_X0, page_top_y - h)

        i = j
        is_last = (i >= total)
        _draw_footer(c, f, is_last_page=is_last)

        c.setFont(FONT, 6)
        c.drawCentredString(PAGE_W/2, MARGIN/2, f"Página {c.getPageNumber()}")

        if not is_last:
            c.showPage()
            new_page()
        else:
            break

    c.save()
    return buf.getvalue()