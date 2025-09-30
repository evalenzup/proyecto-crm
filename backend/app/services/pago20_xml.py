# app/services/pago20_xml.py
from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace

from app.models.pago import Pago, PagoDocumentoRelacionado

# Placeholder for the real implementation
def build_pago20_xml_sin_timbrar(db: Session, pago_id: UUID) -> bytes:
    """
    This is a placeholder for the payment complement XML builder.
    A real implementation would be very complex, similar to cfdi40_xml.py
    """
    pago = db.query(Pago).options(
        selectinload(Pago.empresa),
        selectinload(Pago.cliente),
        selectinload(Pago.documentos_relacionados).selectinload(PagoDocumentoRelacionado.factura)
    ).filter(Pago.id == pago_id).first()

    if not pago:
        raise ValueError("Pago no encontrado")

    # Define namespaces
    NS_CFDI = "http://www.sat.gob.mx/cfd/4"
    NS_PAGO20 = "http://www.sat.gob.mx/Pagos20"
    NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
    register_namespace("cfdi", NS_CFDI)
    register_namespace("pago20", NS_PAGO20)
    register_namespace("xsi", NS_XSI)

    # Create a dummy XML for now
    comprobante = Element(f"{{{NS_CFDI}}}Comprobante", {
        "Version": "4.0",
        "Serie": pago.serie or "P",
        "Folio": pago.folio or "1",
        "Fecha": pago.fecha_pago.strftime("%Y-%m-%dT%H:%M:%S"),
        "SubTotal": "0",
        "Moneda": "XXX",
        "Total": "0",
        "TipoDeComprobante": "P",
        "Exportacion": "01",
        "LugarExpedicion": pago.empresa.codigo_postal,
        f"{{{NS_XSI}}}schemaLocation": "http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd http://www.sat.gob.mx/Pagos20 http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos20.xsd",
    })

    # A real implementation would add Emisor, Receptor, Concepto, and the Complemento node here.

    xml_bytes = tostring(comprobante, encoding="UTF-8", xml_declaration=True)

    # The signing process would happen here

    return xml_bytes
