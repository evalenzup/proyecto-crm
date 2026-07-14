# app/services/certificado_servicio_service.py
"""
Certificados de servicio — v1: Certificado de Aplicación de Plaguicidas.

El PDF replica el formato oficial de NORTON FUMIGACIONES (muestra folio 5262).
Folio consecutivo por empresa+tipo (mecánica de facturas). Los datos del
encabezado (logo, propietario, RFC, dirección, licencia sanitaria) salen del
registro de la empresa.
"""
from __future__ import annotations

import os
from io import BytesIO
from typing import Optional, Tuple, List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.certificado_servicio import CertificadoServicio

# ─────────────────────────────────────────────────────────────────────────────
# Reglas de disponibilidad: qué empresas pueden emitir cada tipo de certificado.
# (El layout PLAGUICIDAS es el formato oficial de NORTON FUMIGACIONES.)
EMPRESAS_PERMITIDAS = {
    "PLAGUICIDAS": {"NORTON FUMIGACIONES"},
}

# Orden y etiquetas fijas del formato
AREAS = [
    ("habitaciones", "No. Habitaciones:"),
    ("closets", "No. Closets:"),
    ("banos", "Baños:"),
    ("cocinas", "Cocinas:"),
    ("comedores", "Comedores:"),
    ("barras", "Barras:"),
    ("almacenes", "Almacenes:"),
    ("oficinas", "Oficinas:"),
    ("exteriores", "Exteriores:"),
    ("estacionamientos", "Estacionamientos:"),
    ("otros", "Otros:"),
]

PLAGAS = [
    ("cucaracha", "Cucaracha:"),
    ("roedores", "Roedores:"),
    ("hormiga", "Hormiga:"),
    ("aracnidos", "Arácnidos:"),
    ("alacran", "Alacrán:"),
    ("grillo", "Grillo:"),
    ("ectoparasitos", "Ectoparásitos:"),
    ("termita", "Termita:"),
    ("plagas_jardin", "Plagas de Jardín:"),
    ("desinfecciones", "Desinfecciones:"),
    ("otros", "Otros:"),
]


def validar_empresa_permitida(empresa, tipo: str) -> None:
    permitidas = EMPRESAS_PERMITIDAS.get((tipo or "").upper())
    if permitidas is None:
        raise HTTPException(status_code=400, detail=f"Tipo de certificado no soportado: {tipo}")
    nombre = (getattr(empresa, "nombre_comercial", None) or "").strip().upper()
    if nombre not in permitidas:
        raise HTTPException(
            status_code=400,
            detail=f"El certificado de {tipo.title()} solo está disponible para: {', '.join(sorted(permitidas))}.",
        )


def siguiente_folio(db: Session, empresa_id: UUID, tipo: str) -> int:
    ultimo = (
        db.query(CertificadoServicio)
        .filter(
            CertificadoServicio.empresa_id == empresa_id,
            CertificadoServicio.tipo == tipo,
        )
        .order_by(CertificadoServicio.folio.desc())
        .with_for_update()
        .first()
    )
    return ultimo.folio + 1 if ultimo else 1


# ─────────────────────────────────────────────────────────────────────────────
# CRUD

def list_certificados(
    db: Session,
    empresa_id: Optional[UUID] = None,
    tipo: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order_by: Optional[str] = None,
    order_dir: Optional[str] = None,
) -> Tuple[List[CertificadoServicio], int]:
    from app.services.ordering import apply_order

    query = db.query(CertificadoServicio)
    if empresa_id:
        query = query.filter(CertificadoServicio.empresa_id == empresa_id)
    if tipo:
        query = query.filter(CertificadoServicio.tipo == tipo.upper())
    if q:
        like = f"%{q}%"
        query = query.filter(CertificadoServicio.nombre_razon_social.ilike(like))
    total = query.count()
    eff_by = order_by or "folio"
    eff_dir = order_dir or ("desc" if eff_by in ("folio", "fecha") else "asc")
    query = apply_order(
        query, CertificadoServicio, eff_by, eff_dir,
        allowed={"folio", "fecha", "nombre_razon_social"},
        default="folio",
    )
    items = query.offset(offset).limit(limit).all()
    return items, total


def get_certificado(db: Session, cert_id: UUID) -> CertificadoServicio:
    obj = db.query(CertificadoServicio).filter(CertificadoServicio.id == cert_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# Generación del PDF (réplica del formato NORTON — muestra 5262)

_NEGRO = "#000000"
_ROJO = "#e8112d"
_VERDE = "#3aa335"

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL",
    "MAYO", "JUNIO", "JULIO", "AGOSTO",
    "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]


def _logo_path(empresa) -> Optional[str]:
    rel = getattr(empresa, "logo", None)
    if not rel:
        return None
    path = os.path.join(settings.DATA_DIR, rel)
    return path if os.path.isfile(path) else None


def _fmt_rfc(rfc: str) -> str:
    """GAOA611225II9 → GAOA-611225-II9 (como aparece en el formato)."""
    rfc = (rfc or "").strip().upper()
    if len(rfc) == 13:
        return f"{rfc[:4]}-{rfc[4:10]}-{rfc[10:]}"
    if len(rfc) == 12:
        return f"{rfc[:3]}-{rfc[3:9]}-{rfc[9:]}"
    return rfc


def generar_pdf(cert: CertificadoServicio) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    W, H = letter  # 612 x 792
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    rojo = HexColor(_ROJO)
    verde = HexColor(_VERDE)

    emp = cert.empresa
    areas = cert.areas or {}
    plagas = cert.plagas or {}
    apl = cert.aplicaciones or {}

    ML, MR = 28, 584  # márgenes del contenido (izq/der)

    # ── Encabezado ───────────────────────────────────────────────────────────
    logo = _logo_path(emp)
    if logo:
        try:
            img = ImageReader(logo)
            iw, ih = img.getSize()
            dw = 150.0
            dh = dw * ih / iw
            if dh > 92:
                dh = 92.0
                dw = dh * iw / ih
            c.drawImage(img, 42, H - 42 - dh, width=dw, height=dh, mask="auto")
        except Exception:
            pass

    cx = 330  # centro del bloque de texto
    c.setFillColor(black)
    c.setFont("Helvetica-BoldOblique", 12.5)
    c.drawCentredString(cx, H - 52, "FUMIGACIONES RESIDENCIALES,")
    c.drawCentredString(cx, H - 69, "COMERCIALES, INDUSTRIALES Y")
    c.drawCentredString(cx, H - 86, "MARÍTIMAS")
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(cx, H - 101, f"PROP. {(emp.nombre or '').upper()}")
    c.drawCentredString(cx, H - 113, f"R.F.C. {_fmt_rfc(emp.rfc)}")
    c.drawCentredString(cx, H - 125, (emp.direccion or "").upper())

    # Cajas derecha: Certificado / Fecha
    bx, bw = 466, 130
    # Certificado
    c.setFillColor(black)
    c.rect(bx, H - 50, bw, 17, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(bx + bw / 2, H - 45, "Certificado")
    c.setFillColor(white)
    c.setStrokeColor(black)
    c.rect(bx, H - 68, bw, 18, stroke=1, fill=1)
    c.setFillColor(rojo)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(bx + bw / 2, H - 63, f"No. {cert.folio}")
    # Fecha
    c.setFillColor(black)
    c.rect(bx, H - 96, bw, 17, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(bx + bw / 2, H - 91, "Fecha")
    c.setFillColor(white)
    c.rect(bx, H - 113, bw, 17, stroke=1, fill=1)
    c.setFillColor(rojo)
    c.setFont("Helvetica-Bold", 8)
    third = bw / 3
    c.drawCentredString(bx + third * 0.5, H - 108, "Día")
    c.drawCentredString(bx + third * 1.5, H - 108, "Mes")
    c.drawCentredString(bx + third * 2.5, H - 108, "Año")
    c.setFillColor(white)
    c.rect(bx, H - 131, bw, 18, stroke=1, fill=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    fecha_txt = cert.fecha.strftime("%d/%m/%Y") if cert.fecha else ""
    c.drawCentredString(bx + bw / 2, H - 126, fecha_txt)

    # ── Barra de título ──────────────────────────────────────────────────────
    ty = H - 162  # borde inferior de la barra
    c.setFillColor(black)
    c.rect(ML, ty, MR - ML, 18, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 11.5)
    titulo = "CERTIFICADO DE APLICACIÓN DE PLAGUICIDAS"
    c.drawCentredString((ML + MR) / 2, ty + 5, titulo)

    # ── Caja de datos del establecimiento ────────────────────────────────────
    cy_top = ty - 4
    cy_bot = cy_top - 74
    c.setStrokeColor(black)
    c.setLineWidth(1.4)
    c.roundRect(ML - 4, cy_bot, (MR - ML) + 8, cy_top - cy_bot, 12, stroke=1, fill=0)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(56, cy_top - 22, "Nombre o Razón Social:")
    c.setFont("Helvetica-BoldOblique", 8.5)
    c.drawCentredString(330, cy_top - 22, (cert.nombre_razon_social or "").upper())

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(42, cy_top - 47, "Domicilio:")
    c.setFont("Helvetica-BoldOblique", 8.5)
    c.drawCentredString(255, cy_top - 47, (cert.domicilio or "").upper())
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(452, cy_top - 47, "Teléfono:")
    c.setFont("Helvetica-BoldOblique", 8.5)
    c.drawCentredString(540, cy_top - 47, cert.telefono or "")

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(56, cy_top - 66, "Actividad del Establecimiento:")
    c.setFont("Helvetica-BoldOblique", 8.5)
    c.drawCentredString(360, cy_top - 66, (cert.actividad or "").upper())

    # ── Barra de secciones ───────────────────────────────────────────────────
    sy = cy_bot - 21
    c.setFillColor(black)
    c.rect(ML, sy, MR - ML, 17, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(112, sy + 5, "ÁREAS TRATADAS")
    c.drawCentredString(242, sy + 5, "PLAGAS SUJETAS A CONTROL")
    c.drawCentredString(470, sy + 5, "APLICACIONES")

    # ── Caja principal de 3 columnas ─────────────────────────────────────────
    by_top = sy - 6
    by_bot = by_top - 273
    c.setLineWidth(1.4)
    c.roundRect(ML - 4, by_bot, (MR - ML) + 8, by_top - by_bot, 12, stroke=1, fill=0)
    # divisores verticales
    d1, d2 = 200, 368
    c.setLineWidth(1.0)
    c.line(d1, by_bot, d1, by_top)
    c.line(d2, by_bot, d2, by_top)

    # Columna 1: áreas
    row_h = 24
    y0 = by_top - 20
    for i, (key, label) in enumerate(AREAS):
        yy = y0 - i * row_h
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(148, yy, label)
        val = str(areas.get(key) or "")
        if val:
            c.setFillColor(verde)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(172, yy - 1, val)

    # Columna 2: plagas
    for i, (key, label) in enumerate(PLAGAS):
        yy = y0 - i * row_h
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(312, yy, label)
        val = str(plagas.get(key) or "")
        if val:
            c.setFillColor(verde)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(338, yy - 1, val)

    # Columna 3: aplicaciones (tabla con líneas)
    lx, rx = d2, MR + 4  # límites de la col 3 (rx = borde caja)
    vx = 480             # divisor etiqueta/valor
    c.setLineWidth(1.0)

    def fila(y_top: float, alto: float, etiqueta_lineas, valor: str,
             divisor: bool = True, valor_arriba: bool = False, etiqueta_abajo: bool = False):
        y_bot = y_top - alto
        c.setStrokeColor(black)
        c.line(lx, y_bot, rx, y_bot)
        if divisor:
            c.line(vx, y_bot, vx, y_top)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 8)
        n = len(etiqueta_lineas)
        base = (y_bot + 8) if etiqueta_abajo else (y_top - alto / 2 - 3 + (n - 1) * 5)
        for j, ln in enumerate(etiqueta_lineas):
            c.drawCentredString((lx + vx) / 2, base - j * 10, ln)
        if valor:
            c.setFillColor(verde)
            c.setFont("Helvetica-Bold", 8.5)
            vy = (y_top - 12) if valor_arriba else (y_top - alto / 2 - 3)
            c.drawCentredString((vx + rx) / 2, vy, valor)
        return y_bot

    yy = by_top
    yy = fila(yy, 26, ["Tiempo de Entrada:"], str(apl.get("tiempo_entrada") or ""))
    yy = fila(yy, 30, ["Tiempo de", "Ventilación:"], str(apl.get("tiempo_ventilacion") or ""))
    yy = fila(yy, 22, ["Aplicación Diurna:"], str(apl.get("diurna") or ""))
    yy = fila(yy, 26, ["Aplicación Nocturna:"], str(apl.get("nocturna") or ""), divisor=False)
    yy = fila(yy, 24, ["Producto Utilizado:"], str(apl.get("producto") or ""))
    yy = fila(yy, 28, ["%"], str(apl.get("porcentaje") or ""))
    yy = fila(yy, 36, ["Antídoto"], str(apl.get("antidoto") or ""),
              valor_arriba=True, etiqueta_abajo=True)

    # Observaciones (barra negra + líneas verdes)
    c.setFillColor(black)
    c.rect(lx, yy - 16, rx - lx, 16, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString((lx + rx) / 2, yy - 11, "Observaciones")
    obs_lines = [ln.strip() for ln in (cert.observaciones or "").splitlines() if ln.strip()]
    # "VENCE:" sale del campo fecha_vencimiento (a menos que ya esté escrito a mano)
    if cert.fecha_vencimiento and not any("VENCE" in ln.upper() for ln in obs_lines):
        obs_lines.insert(0, f"VENCE: {cert.fecha_vencimiento.strftime('%d/%m/%Y')}")
    c.setFillColor(verde)
    c.setFont("Helvetica-Bold", 8)
    oy = yy - 30
    for ln in obs_lines[:5]:
        c.drawCentredString((lx + rx) / 2, oy, ln.upper())
        oy -= 12

    # ── Licencia sanitaria + firma ───────────────────────────────────────────
    ly_top = by_bot - 8
    c.setLineWidth(1.4)
    c.roundRect(54, ly_top - 48, 230, 48, 10, stroke=1, fill=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(169, ly_top - 14, "Licencia Sanitaria")
    lic = (getattr(emp, "licencia_sanitaria", None) or "").strip()
    c.setFillColor(rojo)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(169, ly_top - 29, f"No. {lic}" if lic else "")
    c.setFillColor(black)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawCentredString(169, ly_top - 42, "Autorización S .S. A.")

    fx0, fx1 = 356, 576
    fy = ly_top - 32
    c.setLineWidth(1.2)
    c.line(fx0, fy, fx1, fy)
    c.setFont("Helvetica-BoldOblique", 10)
    c.drawCentredString((fx0 + fx1) / 2, fy + 5, cert.gerente_nombre or "")
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString((fx0 + fx1) / 2, fy - 11, "Nombre y Firma del Gerente")

    # ── Advertencia + sello de meses ─────────────────────────────────────────
    c.setFillColor(rojo)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(
        306, ly_top - 62,
        "DOCUMENTO SIN VALIDEZ AL NO PRESENTARSE DEBIDAMENTE SELLADO, NO SE ACEPTA CON ENMENDADURAS O   RASPADURAS",
    )
    c.drawCentredString(306, ly_top - 73, "CONSÉRVESE A LA VISTA.")

    c.setFillColor(black)
    c.setFont("Helvetica-BoldOblique", 7.5)
    c.drawString(30, ly_top - 87, "Sello que la empresa extiende")

    # Grid de meses (3 filas x 4 columnas)
    gy_top = ly_top - 92
    cell_w = (MR - ML - 4) / 4
    cell_h = 36
    c.setLineWidth(1.2)
    c.setStrokeColor(black)
    for r in range(3):
        for col in range(4):
            x = ML + 2 + col * cell_w
            y = gy_top - (r + 1) * cell_h
            c.rect(x, y, cell_w, cell_h, stroke=1, fill=0)
            c.setFillColor(rojo)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(x + cell_w / 2, y + cell_h / 2 - 3, MESES[r * 4 + col])

    # ── Franja negra inferior ────────────────────────────────────────────────
    c.setFillColor(black)
    c.rect(ML, 10, MR - ML, 11, stroke=0, fill=1)

    c.showPage()
    c.save()
    return buf.getvalue()
