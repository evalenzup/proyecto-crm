# app/services/acuse_cancelacion_service.py
"""
Obtención del acuse de cancelación del SAT (sellado) desde Facturación Moderna.

El PAC NO expone un método SOAP para el acuse; se descarga desde su storage:
  1) GET /cfdis/download/{Emisor}/{Receptor}/{UUID}  → asigna cookie de sesión
  2) GET /cfdis/recacuse/{Emisor}/{Receptor}/{UUID}/cfdi/txt  → XML del acuse (sellado)

El XML es la fuente oficial; el PDF lo generamos nosotros replicando el formato del SAT.
"""
from __future__ import annotations

import os
from io import BytesIO
from xml.etree import ElementTree as ET

import httpx

from app.config import settings
from app.core.logger import logger

_STORAGE_BASE = "https://storage.facturacionmoderna.com"
_RFC_PUBLICO_GENERAL = "XAXX010101000"
_ACUSES_DIR = os.path.join(settings.DATA_DIR, "acuses")
_TIMEOUT = 30.0

# Logo del SAT/Hacienda para el encabezado del acuse (opcional).
# Si el archivo no existe, el PDF se genera solo con el texto del encabezado.
_SAT_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "logo_sat.png")

# Mapeo de EstatusUUID del acuse SAT a texto legible (mejor esfuerzo).
_ESTATUS_UUID = {
    "201": "Solicitud de cancelación recibida",
    "202": "El comprobante ya se encontraba cancelado",
    "203": "El comprobante no aplica para cancelación",
    "205": "El UUID no existe en el SAT",
}

# Descripción de los motivos de cancelación del SAT.
_MOTIVOS = {
    "01": "01 - Comprobante emitido con errores con relación",
    "02": "02 - Comprobante emitido con errores sin relación",
    "03": "03 - No se llevó a cabo la operación",
    "04": "04 - Operación nominativa relacionada en una factura global",
}


class AcuseError(RuntimeError):
    """Error al obtener el acuse de cancelación."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(root: ET.Element, local_name: str) -> str | None:
    for el in root.iter():
        if _local(el.tag) == local_name and el.text:
            return el.text.strip()
    return None


def _resolver_datos(factura) -> tuple[str, str, str]:
    """(rfc_emisor, rfc_receptor, uuid) — mismo criterio que la consulta SAT."""
    uuid = (getattr(factura, "cfdi_uuid", None) or "").strip()
    if not uuid:
        raise AcuseError("La factura no tiene UUID fiscal.")
    emisor = (getattr(getattr(factura, "empresa", None), "rfc", None) or "").strip().upper()
    if not emisor:
        raise AcuseError("La factura no tiene RFC de emisor.")
    receptor = (getattr(getattr(factura, "cliente", None), "rfc", None) or "").strip().upper()
    # Si no hay RFC de receptor, el CFDI fue a público en general.
    receptor = receptor or _RFC_PUBLICO_GENERAL
    return emisor, receptor, uuid


def descargar_acuse_xml(factura, *, forzar: bool = False) -> bytes:
    """Descarga (y cachea) el XML del acuse de cancelación sellado por el SAT."""
    emisor, receptor, uuid = _resolver_datos(factura)

    os.makedirs(_ACUSES_DIR, exist_ok=True)
    cache_path = os.path.join(_ACUSES_DIR, f"{uuid}.xml")
    if not forzar and os.path.isfile(cache_path):
        with open(cache_path, "rb") as fh:
            return fh.read()

    page_url = f"{_STORAGE_BASE}/cfdis/download/{emisor}/{receptor}/{uuid}"
    acuse_url = f"{_STORAGE_BASE}/cfdis/recacuse/{emisor}/{receptor}/{uuid}/cfdi/txt"

    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            # Paso 1: abrir la página para obtener la cookie de sesión.
            client.get(page_url)
            # Paso 2: descargar el XML del acuse con la cookie ya en el cliente.
            resp = client.get(acuse_url)
    except Exception as e:  # noqa: BLE001
        raise AcuseError(f"No se pudo conectar con el PAC para obtener el acuse: {e}") from e

    if resp.status_code != 200 or not resp.content:
        raise AcuseError(
            "El PAC no devolvió el acuse. Verifica que la factura tenga una "
            "solicitud de cancelación registrada (puede tardar unos minutos)."
        )

    contenido = resp.content
    # Validar que sea el XML del acuse y no la página HTML de error.
    if b"<Acuse" not in contenido:
        raise AcuseError(
            "Aún no está disponible el acuse de cancelación para esta factura. "
            "Intenta de nuevo más tarde."
        )

    with open(cache_path, "wb") as fh:
        fh.write(contenido)
    logger.info("Acuse de cancelación descargado y cacheado: %s", uuid)
    return contenido


def _parse_acuse(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    fecha = root.attrib.get("Fecha", "")
    rfc_emisor = root.attrib.get("RfcEmisor", "")
    uuid = _find_text(root, "UUID") or ""
    estatus_uuid = _find_text(root, "EstatusUUID") or ""
    sello = _find_text(root, "SignatureValue") or ""
    no_serie = _find_text(root, "KeyName") or ""
    return {
        "fecha": fecha,
        "rfc_emisor": rfc_emisor,
        "uuid": uuid,
        "estatus_uuid": estatus_uuid,
        "estatus_texto": _ESTATUS_UUID.get(estatus_uuid, f"EstatusUUID {estatus_uuid}"),
        "sello_sat": sello,
        "no_serie": no_serie,
    }


def _fmt_fecha(fecha_iso: str) -> str:
    """'2026-06-22T15:30:02.254' → '22/06/2026 15:30:02'."""
    try:
        from datetime import datetime
        s = fecha_iso.split(".")[0]
        dt = datetime.fromisoformat(s)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:  # noqa: BLE001
        return fecha_iso


def generar_pdf_acuse(xml_bytes: bytes, factura) -> bytes:
    """Genera el PDF del acuse replicando el formato del SAT a partir del XML."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    )

    datos = _parse_acuse(xml_bytes)
    motivo = _MOTIVOS.get(getattr(factura, "motivo_cancelacion", None) or "", getattr(factura, "motivo_cancelacion", None) or "—")
    reemplaza = getattr(factura, "folio_fiscal_sustituto", None) or "—"

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    h_title = ParagraphStyle("t", parent=styles["Title"], fontSize=15, spaceAfter=2)
    h_sub = ParagraphStyle("s", parent=styles["Title"], fontSize=13, spaceAfter=16, textColor=colors.HexColor("#333333"))
    label = ParagraphStyle("l", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold")
    val = ParagraphStyle("v", parent=styles["Normal"], fontSize=10)
    small = ParagraphStyle("sm", parent=styles["Normal"], fontSize=7.5, leading=9, wordWrap="CJK")
    cell = ParagraphStyle("c", parent=styles["Normal"], fontSize=8, leading=10, wordWrap="CJK")
    cell_h = ParagraphStyle("ch", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold")

    el = []
    titulos = [
        Paragraph("Servicio de Administración Tributaria", h_title),
        Paragraph("Acuse de solicitud de Cancelación de CFDI", h_sub),
    ]
    logo_path = os.path.abspath(_SAT_LOGO_PATH)
    if os.path.isfile(logo_path):
        try:
            logo = Image(logo_path, width=4 * cm, height=2 * cm, kind="proportional")
            header = Table([[logo, titulos]], colWidths=[4.5 * cm, 12 * cm])
            header.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]))
            el.append(header)
        except Exception:  # noqa: BLE001
            el.extend(titulos)  # si el logo falla, caemos al encabezado de texto
    else:
        el.extend(titulos)

    # Fecha y RFC
    meta = Table(
        [
            [Paragraph("Fecha y hora de solicitud:", label), Paragraph(_fmt_fecha(datos["fecha"]), val)],
            [Paragraph("RFC Emisor:", label), Paragraph(datos["rfc_emisor"], val)],
        ],
        colWidths=[6 * cm, 10.5 * cm],
    )
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    el.append(meta)
    el.append(Spacer(1, 10))

    # Tabla principal
    tabla = Table(
        [
            [
                Paragraph("Folio Fiscal", cell_h),
                Paragraph("Estatus de Proceso de Cancelación", cell_h),
                Paragraph("Motivo de Cancelación", cell_h),
                Paragraph("CFDI Reemplaza", cell_h),
            ],
            [
                Paragraph(datos["uuid"], cell),
                Paragraph(datos["estatus_texto"], cell),
                Paragraph(motivo, cell),
                Paragraph(reemplaza, cell),
            ],
        ],
        colWidths=[4.3 * cm, 4.3 * cm, 4.3 * cm, 3.6 * cm],
    )
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    el.append(tabla)
    el.append(Spacer(1, 16))

    el.append(Paragraph("Número de Serie de la E.Firma o CSD:", label))
    el.append(Paragraph(datos["no_serie"] or "—", val))
    el.append(Spacer(1, 12))
    el.append(Paragraph("Sello digital SAT:", label))
    el.append(Paragraph(datos["sello_sat"] or "—", small))

    doc.build(el)
    return buf.getvalue()


def obtener_acuse(factura, fmt: str = "pdf", *, forzar: bool = False) -> tuple[bytes, str, str]:
    """Devuelve (contenido, media_type, filename) del acuse en el formato pedido."""
    xml_bytes = descargar_acuse_xml(factura, forzar=forzar)
    _emisor, _receptor, uuid = _resolver_datos(factura)
    base = f"acuse_cancelacion_{factura.serie}-{factura.folio}"
    if (fmt or "pdf").lower() == "xml":
        return xml_bytes, "application/xml", f"{base}.xml"
    pdf_bytes = generar_pdf_acuse(xml_bytes, factura)
    return pdf_bytes, "application/pdf", f"{base}.pdf"
