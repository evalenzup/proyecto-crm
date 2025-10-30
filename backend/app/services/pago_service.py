from sqlalchemy.orm import Session, selectinload
from sqlalchemy import cast, Integer, or_
from fastapi import HTTPException, status
import re
from decimal import Decimal

from app.models.pago import Pago, PagoDocumentoRelacionado, EstatusPago
from app.models.factura import Factura
from app.schemas.pago import PagoCreate
from app.services.timbrado_factmoderna import FacturacionModernaPAC
from app.services.pdf_pago import render_pago_pdf_bytes_from_model
from app.services.email_sender import send_pago_email, EmailSendingError
import os
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional, Tuple

import logging

logger = logging.getLogger(__name__)

_pac = FacturacionModernaPAC()


def siguiente_folio_pago(db: Session, empresa_id: UUID, serie: str) -> int:
    logger.info(
        f"siguiente_folio_pago called with empresa_id: {empresa_id}, serie: {serie}"
    )
    query = db.query(Pago).filter(Pago.empresa_id == empresa_id)

    if serie:
        query = query.filter(Pago.serie == serie)
    else:
        query = query.filter(or_(Pago.serie.is_(None), Pago.serie == ""))

    latest_pago = (
        query.order_by(cast(Pago.folio, Integer).desc()).with_for_update().first()
    )
    result_folio = int(latest_pago.folio) + 1 if latest_pago else 1
    logger.info(f"latest_pago: {latest_pago}")
    logger.info(f"Returning folio: {result_folio}")
    return result_folio


def leer_pago(db: Session, pago_id: UUID) -> Pago:
    db_pago = (
        db.query(Pago)
        .options(
            # Cargar el cliente para mostrar su nombre en el formulario de edición
            selectinload(Pago.cliente),
            selectinload(Pago.documentos_relacionados).selectinload(
                PagoDocumentoRelacionado.factura
            )
        )
        .filter(Pago.id == pago_id)
        .first()
    )
    if db_pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return db_pago


def listar_pagos(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 10,
    order_by: str = "fecha_pago",
    order_dir: str = "desc",
    empresa_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    estatus: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> Tuple[List[Pago], int]:
    query = db.query(Pago).options(selectinload(Pago.cliente))

    if empresa_id:
        query = query.filter(Pago.empresa_id == empresa_id)
    if cliente_id:
        query = query.filter(Pago.cliente_id == cliente_id)
    if estatus:
        query = query.filter(Pago.estatus == estatus)
    if fecha_desde:
        query = query.filter(Pago.fecha_pago >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Pago.fecha_pago <= fecha_hasta)

    # Count total items before pagination
    total = query.count()

    # Apply ordering
    if hasattr(Pago, order_by):
        column = getattr(Pago, order_by)
        if order_dir == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())

    # Apply pagination
    pagos = query.offset(offset).limit(limit).all()

    return pagos, total


def set_pago_to_borrador(db: Session, pago_id: UUID) -> Pago:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    pago.estatus = "BORRADOR"
    pago.uuid = None
    pago.fecha_timbrado = None
    pago.xml_path = None
    pago.pdf_path = None
    pago.cadena_original = None
    pago.qr_url = None
    pago.no_certificado = None
    pago.no_certificado_sat = None
    pago.sello_cfdi = None
    pago.sello_sat = None
    pago.rfc_proveedor_sat = None
    db.commit()
    db.refresh(pago)
    return pago


def listar_facturas_pendientes_por_cliente(
    db: Session, cliente_id: UUID
) -> List[Factura]:
    """
    Obtiene todas las facturas de un cliente que tienen estatus de pago 'NO_PAGADA'
    y que han sido timbradas.
    """
    facturas = (
        db.query(Factura)
        .filter(
            Factura.cliente_id == cliente_id,
            Factura.status_pago == "NO_PAGADA",
            Factura.estatus == "TIMBRADA",
        )
        .order_by(Factura.fecha_emision.desc())
        .all()
    )

    return facturas


def get_pago_pdf(db: Session, pago_id: UUID) -> tuple[bytes, str]:
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        preview = not (pago and pago.estatus == EstatusPago.TIMBRADO)
        pdf_bytes = render_pago_pdf_bytes_from_model(db, pago_id, preview=preview)
        folio_str = (
            f"{pago.serie}-{pago.folio}"
            if pago and pago.serie
            else str(pago.folio)
            if pago
            else str(pago_id)
        )
        filename = f"Pago-{folio_str}.pdf"
        return pdf_bytes, filename
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Idealmente, aquí se registraría el error `e` en un sistema de logging
        raise HTTPException(
            status_code=500, detail=f"No se pudo generar el PDF del pago: {e}"
        )


async def enviar_pago_por_email(
    db: Session, pago_id: UUID, recipients: List[str], subject: Optional[str], body: Optional[str]
):
    try:
        # Generar el PDF del pago
        pdf_bytes, pdf_filename = get_pago_pdf(db, pago_id)

        # Obtener el XML del pago
        xml_path, xml_filename = obtener_ruta_xml_pago(db, pago_id)
        xml_content = None
        if not os.path.exists(xml_path):
            raise HTTPException(
                status_code=404,
                detail="XML para el pago no encontrado, no se puede enviar el correo.",
            )

        with open(xml_path, "rb") as f:
            xml_content = f.read()

        # Enviar correo
        await send_pago_email(
            db=db,
            pago_id=pago_id,
            recipients=recipients,
            subject=subject,
            body=body,
            pdf_content=pdf_bytes,
            pdf_filename=pdf_filename,
            xml_content=xml_content,
            xml_filename=xml_filename,
        )
        return {
            "message": "Complemento de pago enviado por correo electrónico exitosamente."
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EmailSendingError as e:
        raise HTTPException(
            status_code=500, detail=f"Error al enviar el correo electrónico: {e}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


def crear_pago(db: Session, pago: PagoCreate):
    logger.info(f"crear_pago called with payload: {pago.dict()}")
    if not pago.documentos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pago debe tener al menos un documento relacionado.",
        )

    total_pagado_en_documentos = sum(doc.imp_pagado for doc in pago.documentos)
    if not abs(total_pagado_en_documentos - pago.monto) < Decimal("0.01"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto total del pago ({pago.monto}) no coincide con la suma de los importes pagados en los documentos ({total_pagado_en_documentos}).",
        )

    serie = (pago.serie or "P").upper()
    folio = (
        pago.folio
        if pago.folio is not None
        else str(siguiente_folio_pago(db, pago.empresa_id, serie))
    )

    logger.info(f"Generated serie: {serie}, folio: {folio}")

    db_pago = Pago(**pago.dict(exclude={"documentos", "serie", "folio"}))
    db_pago.serie = serie
    db_pago.folio = folio

    for doc_in in pago.documentos:
        factura = (
            db.query(Factura)
            .options(selectinload(Factura.conceptos))
            .filter(Factura.id == doc_in.factura_id)
            .first()
        )
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La factura con ID {doc_in.factura_id} no fue encontrada.",
            )

        if factura.status_pago == "PAGADA":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La factura {factura.folio} ya ha sido pagada.",
            )

        if doc_in.imp_pagado > factura.total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El importe pagado ({doc_in.imp_pagado}) para la factura {factura.folio} no puede ser mayor a su saldo total ({factura.total}).",
            )

        # --- START: Calculate proportional taxes ---
        impuestos_dr_json = {"retenciones_dr": [], "traslados_dr": []}
        if factura.total > 0 and doc_in.imp_pagado > 0:
            payment_ratio = doc_in.imp_pagado / factura.total

            retenciones_sum = {}
            traslados_sum = {}

            for concepto in factura.conceptos:
                base_proporcional = (
                    concepto.cantidad * concepto.valor_unitario - concepto.descuento
                ) * payment_ratio

                if concepto.ret_isr_importe and concepto.ret_isr_importe > 0:
                    tasa = str(concepto.ret_isr_tasa)
                    if "001" not in retenciones_sum:
                        retenciones_sum["001"] = {}
                    if tasa not in retenciones_sum["001"]:
                        retenciones_sum["001"][tasa] = {"base": 0, "importe": 0}
                    retenciones_sum["001"][tasa]["base"] += base_proporcional
                    retenciones_sum["001"][tasa]["importe"] += (
                        concepto.ret_isr_importe * payment_ratio
                    )

                if concepto.ret_iva_importe and concepto.ret_iva_importe > 0:
                    tasa = str(concepto.ret_iva_tasa)
                    if "002" not in retenciones_sum:
                        retenciones_sum["002"] = {}
                    if tasa not in retenciones_sum["002"]:
                        retenciones_sum["002"][tasa] = {"base": 0, "importe": 0}
                    retenciones_sum["002"][tasa]["base"] += base_proporcional
                    retenciones_sum["002"][tasa]["importe"] += (
                        concepto.ret_iva_importe * payment_ratio
                    )

                if concepto.iva_importe and concepto.iva_importe > 0:
                    tasa = str(concepto.iva_tasa)
                    if "002" not in traslados_sum:
                        traslados_sum["002"] = {}
                    if tasa not in traslados_sum["002"]:
                        traslados_sum["002"][tasa] = {"base": 0, "importe": 0}
                    traslados_sum["002"][tasa]["base"] += base_proporcional
                    traslados_sum["002"][tasa]["importe"] += (
                        concepto.iva_importe * payment_ratio
                    )

            for impuesto, tasas in retenciones_sum.items():
                for tasa, montos in tasas.items():
                    impuestos_dr_json["retenciones_dr"].append(
                        {
                            "base_dr": float(montos["base"]),
                            "impuesto_dr": impuesto,
                            "tipo_factor_dr": "Tasa",
                            "tasa_o_cuota_dr": float(tasa),
                            "importe_dr": float(montos["importe"]),
                        }
                    )

            for impuesto, tasas in traslados_sum.items():
                for tasa, montos in tasas.items():
                    impuestos_dr_json["traslados_dr"].append(
                        {
                            "base_dr": float(montos["base"]),
                            "impuesto_dr": impuesto,
                            "tipo_factor_dr": "Tasa",
                            "tasa_o_cuota_dr": float(tasa),
                            "importe_dr": float(montos["importe"]),
                        }
                    )

        # --- END: Calculate proportional taxes ---

        db_doc = PagoDocumentoRelacionado(
            factura_id=factura.id,
            id_documento=factura.cfdi_uuid,
            serie=factura.serie,
            folio=str(factura.folio),
            moneda_dr=factura.moneda,
            num_parcialidad=doc_in.num_parcialidad,
            imp_saldo_ant=doc_in.imp_saldo_ant,
            imp_pagado=doc_in.imp_pagado,
            imp_saldo_insoluto=doc_in.imp_saldo_insoluto,
            impuestos_dr=impuestos_dr_json,
            # Opcional: si no viene en el payload, permanece en None
            tipo_cambio_dr=getattr(doc_in, "tipo_cambio_dr", None),
        )
        db_pago.documentos_relacionados.append(db_doc)

    try:
        db.add(db_pago)
        db.commit()
        db.refresh(db_pago)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar en la base de datos: {e}",
        )

    return db_pago


def timbrar_pago(db: Session, pago_id: UUID) -> dict:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pago.estatus != "BORRADOR":
        raise HTTPException(
            status_code=400, detail="Solo se puede timbrar un pago en BORRADOR"
        )

    try:
        result = _pac.timbrar_pago(
            db=db,
            pago_id=pago_id,
            generar_cbb=False,
            generar_txt=False,
            generar_pdf=False,
        )

        pago.estatus = "TIMBRADO"
        pago.uuid = result["uuid"]
        pago.fecha_timbrado = datetime.utcnow()
        pago.xml_path = result.get("xml_path")

        for doc in pago.documentos_relacionados:
            factura_a_actualizar = (
                db.query(Factura).filter(Factura.id == doc.factura_id).first()
            )
            if factura_a_actualizar:
                if doc.imp_saldo_insoluto == 0:
                    factura_a_actualizar.status_pago = "PAGADA"

        db.commit()
        db.refresh(pago)

        return {"ok": True, "uuid": pago.uuid, "message": "Pago timbrado exitosamente."}

    except RuntimeError as e:
        db.rollback()
        # Extraer mensaje del PAC (SOAP) y regresarlo tal cual
        msg = str(e)
        m = re.search(
            r"<faultstring>(.*?)</faultstring>", msg, flags=re.IGNORECASE | re.DOTALL
        )
        if m:
            fault = m.group(1).strip()
            raise HTTPException(status_code=400, detail=fault)
        m2 = re.search(
            r"PAC devolvió Fault:\s*\S*\s*(.+)$", msg, flags=re.IGNORECASE | re.DOTALL
        )
        if m2:
            fault = m2.group(1).strip()
            raise HTTPException(status_code=400, detail=fault)
        logger.warning("Timbrado Pago PAC error no parseable: %s", msg)
        raise HTTPException(
            status_code=502,
            detail="El PAC rechazó el timbrado del pago. Intenta nuevamente o verifica los datos.",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error interno al timbrar el pago: {e}"
        )


def obtener_ruta_xml_pago(db: Session, pago_id: UUID) -> tuple[str, str]:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pago.estatus != "TIMBRADO":
        raise HTTPException(
            status_code=409, detail="El pago debe estar TIMBRADO para descargar el XML"
        )

    if not pago.xml_path:
        raise HTTPException(
            status_code=404, detail="Ruta de XML no encontrada para este pago."
        )

    filename = f"PAGO-{pago.folio}.xml"

    return pago.xml_path, filename


def eliminar_pago(db: Session, pago_id: UUID):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    if pago.estatus != "BORRADOR":
        raise HTTPException(
            status_code=400, detail="Solo se pueden eliminar pagos en BORRADOR"
        )

    db.delete(pago)
    db.commit()
    return {"message": "Pago eliminado exitosamente."}
