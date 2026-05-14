# app/services/credencial_service.py
"""
Credencial PDF de dos caras estilo Card Depot.
Frente : fondo blanco, ola derecha en color empresa, logo top-left, foto, nombre, datos.
Reverso: fondo blanco, ola en la parte inferior en color empresa, datos, QR negro.
"""
from __future__ import annotations

import io
import os
from typing import Optional
from uuid import UUID

import qrcode
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from app.config import settings

CARD_W = 86 * mm
CARD_H = 135 * mm
M      = 5.5 * mm      # margen lateral

TIPO_LABEL = {
    "TECNICO":        "Técnico",
    "ADMINISTRATIVO": "Administrativo",
    "OPERATIVO":      "Operativo",
    "SUPERVISOR":     "Supervisor",
    "OTRO":           "Personal",
}


# ── Utilidades ────────────────────────────────────────────────────────────────

def _load_img(path: str | None) -> Optional[PILImage.Image]:
    if not path:
        return None
    try:
        return PILImage.open(path).convert("RGBA")
    except Exception:
        return None


def _fit(img: PILImage.Image, max_w: float, max_h: float) -> tuple[float, float]:
    iw, ih = img.size
    r = min(max_w / iw, max_h / ih)
    return iw * r, ih * r


def _buf(img: PILImage.Image, flatten: bool = False) -> io.BytesIO:
    """Serializa a PNG. Con flatten=True composita sobre blanco (elimina alpha)."""
    if flatten or img.mode == "RGB":
        out = img.convert("RGB") if img.mode != "RGB" else img
    else:
        out = img  # RGBA con transparencia real (logos con fondo transparente)
    b = io.BytesIO()
    out.save(b, format="PNG")
    b.seek(0)
    return b


def _qr_black(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(version=2, box_size=4, border=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return _buf(img)


def _darken(hex_color: str, f: float = 0.20) -> colors.Color:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return colors.Color(r * (1 - f), g * (1 - f), b * (1 - f))


def _lighten(hex_color: str, f: float = 0.25) -> colors.Color:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return colors.Color(min(1, r + (1-r)*f), min(1, g + (1-g)*f), min(1, b + (1-b)*f))


# ── Ola superior horizontal (frontal) ────────────────────────────────────────

def _wave_top(c: rl_canvas.Canvas, color_hex: str) -> float:
    """
    Rellena la parte superior de la tarjeta con una ola horizontal.
    El borde inferior de la zona de color es una curva bezier suave de
    izquierda a derecha.  Devuelve la Y del punto más bajo de la ola
    (límite entre color y blanco).
    """
    col  = colors.HexColor(color_hex)
    col2 = _lighten(color_hex, 0.18)

    # Alturas del borde inferior de la ola (desde la base del PDF)
    left_y  = CARD_H - 46 * mm   # borde izquierdo más arriba
    right_y = CARD_H - 50 * mm   # borde derecho ligeramente más abajo
    dip_y   = CARD_H - 56 * mm   # punto más bajo de la curva (centro)

    # Capa principal de color (la más abajo)
    p = c.beginPath()
    p.moveTo(0, CARD_H)
    p.lineTo(CARD_W, CARD_H)
    p.lineTo(CARD_W, right_y)
    # bezier S suave de derecha a izquierda
    p.curveTo(CARD_W * 0.72, right_y,
              CARD_W * 0.60, dip_y,
              CARD_W * 0.50, dip_y)
    p.curveTo(CARD_W * 0.38, dip_y,
              CARD_W * 0.22, left_y,
              0, left_y)
    p.close()
    c.setFillColor(col)
    c.drawPath(p, fill=1, stroke=0)

    # Segunda ola más clara, desplazada ~7mm hacia arriba (da profundidad)
    off = 7 * mm
    p2 = c.beginPath()
    p2.moveTo(0, CARD_H)
    p2.lineTo(CARD_W, CARD_H)
    p2.lineTo(CARD_W, right_y + off)
    p2.curveTo(CARD_W * 0.72, right_y + off,
               CARD_W * 0.60, dip_y + off,
               CARD_W * 0.50, dip_y + off)
    p2.curveTo(CARD_W * 0.38, dip_y + off,
               CARD_W * 0.22, left_y + off,
               0, left_y + off)
    p2.close()
    c.setFillColor(col2)
    c.drawPath(p2, fill=1, stroke=0)

    return dip_y   # punto más bajo de la ola principal


# ── Ola inferior (reverso) ────────────────────────────────────────────────────

def _wave_bottom(c: rl_canvas.Canvas, color_hex: str) -> float:
    """
    Dibuja la ola en la parte inferior del reverso (estilo Card Depot).
    Devuelve la coordenada Y del punto más alto de la ola (límite entre blanco y color).
    """
    col  = colors.HexColor(color_hex)
    col2 = _lighten(color_hex, 0.18)

    # Ola principal: cubre el lado inferior
    # Borde superior: S-curve de izquierda a derecha
    wave_left_y  = CARD_H * 0.40    # altura del borde izq
    wave_right_y = CARD_H * 0.33    # altura del borde der

    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(CARD_W, 0)
    p.lineTo(CARD_W, wave_right_y)
    # S-curve de der a izq
    p.curveTo(CARD_W * 0.72, wave_right_y + (wave_left_y - wave_right_y) * 0.05,
              CARD_W * 0.55, wave_left_y - (wave_left_y - wave_right_y) * 0.10,
              CARD_W * 0.40, (wave_left_y + wave_right_y) / 2)
    p.curveTo(CARD_W * 0.22, wave_left_y + (wave_left_y - wave_right_y) * 0.05,
              CARD_W * 0.10, wave_left_y * 0.98,
              0, wave_left_y)
    p.close()
    c.setFillColor(col)
    c.drawPath(p, fill=1, stroke=0)

    # Segunda ola más clara (desplazada hacia arriba ~6mm)
    off = 6 * mm
    p2 = c.beginPath()
    p2.moveTo(0, 0)
    p2.lineTo(CARD_W, 0)
    p2.lineTo(CARD_W, wave_right_y + off)
    p2.curveTo(CARD_W * 0.72, wave_right_y + off + (wave_left_y - wave_right_y) * 0.05,
               CARD_W * 0.55, wave_left_y + off - (wave_left_y - wave_right_y) * 0.10,
               CARD_W * 0.40, (wave_left_y + wave_right_y) / 2 + off)
    p2.curveTo(CARD_W * 0.22, wave_left_y + off + (wave_left_y - wave_right_y) * 0.05,
               CARD_W * 0.10, (wave_left_y + off) * 0.98,
               0, wave_left_y + off)
    p2.close()
    c.setFillColor(col2)
    c.drawPath(p2, fill=1, stroke=0)

    return wave_left_y + off   # Y superior de la zona de color


# ══════════════════════════════════════════════════════════════════════════════
# CARA FRONTAL
# ══════════════════════════════════════════════════════════════════════════════

def _draw_front(c: rl_canvas.Canvas, *, color_hex: str,
                empresa_id: UUID, empresa_nombre: str,
                nombre: str, primer_apellido: str, segundo_apellido: Optional[str],
                curp: Optional[str], numero_trabajador: Optional[str],
                tipo_personal: str, puesto: Optional[str],
                rfc_personal: Optional[str], area: Optional[str],
                foto_filename: Optional[str]) -> None:

    col_main = colors.HexColor(color_hex)

    # ── Fondo blanco ──────────────────────────────────────────────────────────
    c.setFillColor(colors.white)
    c.rect(0, 0, CARD_W, CARD_H, fill=1, stroke=0)

    # ── Ola horizontal superior ───────────────────────────────────────────────
    wave_bottom_y = _wave_top(c, color_hex)

    # ── Logo de empresa (centrado en la zona de color) ────────────────────────
    logo_area_top    = CARD_H
    logo_area_bottom = wave_bottom_y + 6 * mm
    logo_center_y    = (logo_area_top + logo_area_bottom) / 2

    logo_path = os.path.join(settings.DATA_DIR, "logos", f"{empresa_id}.png")
    logo_img = _load_img(logo_path)
    if logo_img:
        max_lw = CARD_W - 16 * mm
        max_lh = (logo_area_top - logo_area_bottom) * 0.60
        lw, lh = _fit(logo_img, max_lw, max_lh)
        c.drawImage(ImageReader(_buf(logo_img)),
                    (CARD_W - lw) / 2, logo_center_y - lh / 2,
                    width=lw, height=lh, mask="auto", preserveAspectRatio=True)
    else:
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        txt = empresa_nombre.upper()[:20]
        c.drawCentredString(CARD_W / 2, logo_center_y - 3.5, txt)

    # ── Foto del empleado (centrada, justo bajo la ola, mitad solapada) ───────
    PHOTO_W = 28 * mm
    PHOTO_H = 35 * mm
    photo_x = (CARD_W - PHOTO_W) / 2
    # La foto queda centrada verticalmente en el límite de la ola
    photo_y = wave_bottom_y - PHOTO_H - 3 * mm

    foto_img = _load_img(
        os.path.join(settings.DATA_DIR, "tecnicos_fotos", foto_filename)
        if foto_filename else None
    )

    # Fondo blanco sólido debajo de la foto (cubre la ola que se filtra)
    c.setFillColor(colors.white)
    c.roundRect(photo_x, photo_y, PHOTO_W, PHOTO_H, 4, fill=1, stroke=0)

    if foto_img:
        # Recortar la imagen al aspect ratio exacto del recuadro para que no queden
        # bordes vacíos que dejen ver el fondo de la ola
        target_ratio = PHOTO_W / PHOTO_H
        iw, ih = foto_img.size
        src_ratio = iw / ih
        if src_ratio > target_ratio:
            # imagen más ancha → recortar los lados
            new_w = int(ih * target_ratio)
            left = (iw - new_w) // 2
            foto_img = foto_img.crop((left, 0, left + new_w, ih))
        else:
            # imagen más alta → recortar arriba/abajo (centrar verticalmente)
            new_h = int(iw / target_ratio)
            top = (ih - new_h) // 4   # ligeramente hacia arriba para mostrar la cara
            foto_img = foto_img.crop((0, top, iw, top + new_h))

        c.drawImage(ImageReader(_buf(foto_img, flatten=True)), photo_x, photo_y,
                    width=PHOTO_W, height=PHOTO_H, preserveAspectRatio=False)
    else:
        c.setFillColor(colors.HexColor("#e0e8e0"))
        c.roundRect(photo_x, photo_y, PHOTO_W, PHOTO_H, 4, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#aaaaaa"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(photo_x + PHOTO_W / 2, photo_y + PHOTO_H / 2 - 3, "SIN FOTO")

    # Marco blanco de la foto
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)
    c.setLineWidth(2.5)
    c.roundRect(photo_x, photo_y, PHOTO_W, PHOTO_H, 4, fill=0, stroke=1)

    # ── Nombre y cargo ────────────────────────────────────────────────────────
    apellidos = " ".join(p for p in [primer_apellido, (segundo_apellido or "")] if p)
    y = photo_y - 7 * mm

    c.setFillColor(colors.HexColor("#1a1a1a"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(CARD_W / 2, y, apellidos.upper())
    y -= 5 * mm

    c.setFont("Helvetica", 9)
    c.drawCentredString(CARD_W / 2, y, nombre.upper())
    y -= 5 * mm

    cargo = puesto or TIPO_LABEL.get(tipo_personal, tipo_personal)
    c.setFillColor(colors.HexColor("#555555"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(CARD_W / 2, y, cargo)
    y -= 7 * mm

    # ── Campos de datos (estilo Card Depot: Label  :  Valor) ──────────────────
    LABEL_X = M
    COLON_X = LABEL_X + 20 * mm
    VALUE_X = COLON_X + 2.5 * mm
    ROW_H   = 5.5 * mm

    def data_row(label: str, value: str, ypos: float) -> float:
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 7)
        c.drawString(LABEL_X, ypos, label)
        c.drawString(COLON_X, ypos, ":")
        c.setFillColor(colors.HexColor("#1a1a1a"))
        c.setFont("Helvetica", 7)
        max_c = 22
        v = value if len(value) <= max_c else value[:max_c - 1] + "…"
        c.drawString(VALUE_X, ypos, v)
        return ypos - ROW_H

    if numero_trabajador:
        y = data_row("No. Empleado", numero_trabajador, y)
    if rfc_personal:
        y = data_row("RFC", rfc_personal, y)
    if curp:
        y = data_row("CURP", curp[:16], y)
    if area:
        y = data_row("Área", area, y)

    # ── Franja inferior ───────────────────────────────────────────────────────
    FOOTER_H = 9 * mm
    c.setFillColor(col_main)
    c.rect(0, 0, CARD_W, FOOTER_H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(CARD_W / 2, FOOTER_H / 2 - 2.5, "CREDENCIAL DE IDENTIFICACIÓN")

    # ── Borde exterior ────────────────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(0.5)
    c.rect(0.5, 0.5, CARD_W - 1, CARD_H - 1, fill=0, stroke=1)


# ══════════════════════════════════════════════════════════════════════════════
# CARA TRASERA
# ══════════════════════════════════════════════════════════════════════════════

def _draw_back(c: rl_canvas.Canvas, *, color_hex: str,
               empresa_id: UUID, empresa_nombre: str, empresa_rfc: str,
               empresa_telefono: Optional[str],
               nombre: str, primer_apellido: str, segundo_apellido: Optional[str],
               nss: Optional[str], tipo_sangre: Optional[str],
               tecnico_direccion: Optional[str],
               qr_data: str) -> None:

    # ── Fondo blanco ──────────────────────────────────────────────────────────
    c.setFillColor(colors.white)
    c.rect(0, 0, CARD_W, CARD_H, fill=1, stroke=0)

    # ── Ola inferior ──────────────────────────────────────────────────────────
    wave_top_y = _wave_bottom(c, color_hex)

    # ── QR negro (centrado en la zona de color) ───────────────────────────────
    QR_SIZE = 20 * mm
    qr_x = M
    qr_y = (wave_top_y - M * 0.5 - QR_SIZE) / 2     # centrado vertical en la ola

    c.setFillColor(colors.white)
    c.roundRect(qr_x - 1.5, qr_y - 1.5, QR_SIZE + 3, QR_SIZE + 3, 3, fill=1, stroke=0)
    c.drawImage(ImageReader(_qr_black(qr_data)), qr_x, qr_y, width=QR_SIZE, height=QR_SIZE)

    # ── Logo empresa (derecha de la ola inferior, estilo Card Depot) ──────────
    logo_path = os.path.join(settings.DATA_DIR, "logos", f"{empresa_id}.png")
    logo_img = _load_img(logo_path)
    logo_area_x = qr_x + QR_SIZE + 3 * mm
    logo_area_w = CARD_W - logo_area_x - M
    logo_area_h = wave_top_y - 3 * mm

    if logo_img:
        lw, lh = _fit(logo_img, logo_area_w, logo_area_h * 0.55)
        lx = logo_area_x + (logo_area_w - lw) / 2
        ly = (wave_top_y - M * 0.5 - lh) / 2
        c.drawImage(ImageReader(_buf(logo_img)), lx, ly, width=lw, height=lh,
                    mask="auto", preserveAspectRatio=True)
    else:
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(logo_area_x + logo_area_w / 2,
                            wave_top_y / 2 - 3,
                            empresa_nombre.upper()[:14])

    # ── Nombre del empleado (top, estilo Card Depot) ──────────────────────────
    apellidos = " ".join(p for p in [primer_apellido, (segundo_apellido or "")] if p)
    nombre_completo = f"{nombre} {apellidos}"

    y = CARD_H - M * 1.2

    c.setFillColor(colors.HexColor("#1a1a1a"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(CARD_W / 2, y - 5 * mm, nombre_completo)

    # Línea separadora sutil
    sep_y = y - 9 * mm
    c.setStrokeColor(colors.HexColor("#dddddd"))
    c.setLineWidth(0.5)
    c.line(M, sep_y, CARD_W - M, sep_y)

    # ── Campos de datos (zona blanca central) ─────────────────────────────────
    # Misma estructura que la imagen de referencia:
    # LABEL en gris, valor en negro, una línea entre campos

    y = sep_y - 7 * mm
    LABEL_X = M
    COL_X   = LABEL_X + 22 * mm      # columna del colon
    VAL_X   = COL_X + 2 * mm

    def back_row(label: str, value: str, ypos: float) -> float:
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 7)
        c.drawString(LABEL_X, ypos, label)
        c.drawString(COL_X, ypos, ":")
        c.setFillColor(colors.HexColor("#1a1a1a"))
        c.setFont("Helvetica", 7)
        max_c = 22
        v = value if len(value) <= max_c else value[:max_c - 1] + "…"
        c.drawString(VAL_X, ypos, v)
        return ypos - 5.5 * mm

    def back_block(header: str, value: str, ypos: float) -> float:
        """Bloque de dos líneas: encabezado en gris + valor en negro."""
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 7)
        c.drawString(LABEL_X, ypos, header)
        ypos -= 4.5 * mm
        c.setFillColor(colors.HexColor("#1a1a1a"))
        c.setFont("Helvetica", 7)
        max_c = 32
        v = value if len(value) <= max_c else value[:max_c - 1] + "…"
        c.drawString(LABEL_X, ypos, v)
        return ypos - 5.5 * mm

    if tecnico_direccion:
        y = back_block("DOMICILIO", tecnico_direccion.upper(), y)
    if nss:
        y = back_row("NSS", nss, y)
    if empresa_telefono:
        y = back_block("EN CASO DE EMERGENCIA", f"TEL: {empresa_telefono}", y)
    if tipo_sangre:
        y = back_row("TIPO DE SANGRE", tipo_sangre, y)

    # ── Borde exterior ────────────────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(0.5)
    c.rect(0.5, 0.5, CARD_W - 1, CARD_H - 1, fill=0, stroke=1)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PÚBLICA
# ══════════════════════════════════════════════════════════════════════════════

def generar_credencial_pdf(
    tecnico_id: UUID,
    nombre: str,
    primer_apellido: str,
    segundo_apellido: Optional[str],
    curp: Optional[str],
    numero_trabajador: Optional[str],
    tipo_personal: str,
    puesto: Optional[str],
    tipo_sangre: Optional[str],
    foto_filename: Optional[str],
    empresa_id: UUID,
    empresa_nombre: str,
    empresa_rfc: str,
    qr_data: str,
    color_hex: str = "#1a6b3a",
    nss: Optional[str] = None,
    rfc_personal: Optional[str] = None,
    area: Optional[str] = None,
    empresa_telefono: Optional[str] = None,
    tecnico_direccion: Optional[str] = None,
) -> bytes:
    """Genera un PDF de dos páginas (frente y reverso) de la credencial."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(CARD_W, CARD_H))

    _draw_front(
        c,
        color_hex=color_hex,
        empresa_id=empresa_id,
        empresa_nombre=empresa_nombre,
        nombre=nombre,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        curp=curp,
        numero_trabajador=numero_trabajador,
        tipo_personal=tipo_personal,
        puesto=puesto,
        rfc_personal=rfc_personal,
        area=area,
        foto_filename=foto_filename,
    )
    c.showPage()

    _draw_back(
        c,
        color_hex=color_hex,
        empresa_id=empresa_id,
        empresa_nombre=empresa_nombre,
        empresa_rfc=empresa_rfc,
        empresa_telefono=empresa_telefono,
        nombre=nombre,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        nss=nss,
        tipo_sangre=tipo_sangre,
        tecnico_direccion=tecnico_direccion,
        qr_data=qr_data,
    )

    c.save()
    return buf.getvalue()
