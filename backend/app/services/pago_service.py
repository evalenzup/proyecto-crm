from sqlalchemy.orm import Session, selectinload
from sqlalchemy import cast, Integer, or_
from fastapi import HTTPException, status
import re
from decimal import Decimal, ROUND_HALF_UP

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
    if order_by == "folio":
        column = cast(Pago.folio, Integer)
        if order_dir == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    elif hasattr(Pago, order_by):
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
    db: Session, cliente_id: UUID, empresa_id: Optional[UUID] = None
) -> List[Factura]:
    """
    Obtiene todas las facturas pendientes de pago.
    Si el cliente tiene un RFC específico (no genérico), busca facturas de CUALQUIER cliente con ese RFC (multi-sucursal).
    Si se proporciona empresa_id, filtra por empresa.
    """
    from app.models.cliente import Cliente

    # 1. Obtener el cliente objetivo para saber su RFC
    target_client = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not target_client:
        return []

    # RFC Genérico: XAXX010101000
    RFC_GENERICO = "XAXX010101000"

    query = (
        db.query(Factura)
        .join(Factura.cliente)
        .options(selectinload(Factura.cliente))
        .filter(
            Factura.status_pago == "NO_PAGADA",
            Factura.estatus == "TIMBRADA",
        )
    )

    # 2. Aplicar filtro por RFC o ID
    if target_client.rfc and target_client.rfc != RFC_GENERICO:
        # Búsqueda amplia por RFC (Multi-sucursal)
        query = query.filter(Cliente.rfc == target_client.rfc)
    else:
        # Búsqueda estricta por ID (Genérico o sin RFC)
        query = query.filter(Factura.cliente_id == cliente_id)

    # 3. Filtrar por empresa si se proporciona (CRÍTICO para seguridad/tenant)
    if empresa_id:
        query = query.filter(Factura.empresa_id == empresa_id)

    facturas = query.order_by(Factura.fecha_emision.desc()).all()

    # Calcular saldo pendiente y parcialidad para cada factura
    for f in facturas:
        pagos_rels = (
            db.query(PagoDocumentoRelacionado)
            .join(Pago)
            .filter(
                PagoDocumentoRelacionado.factura_id == f.id,
                Pago.estatus == EstatusPago.TIMBRADO
            )
            .all()
        )
        total_pagado = sum(rel.imp_pagado for rel in pagos_rels)
        f.saldo_pendiente = f.total - total_pagado
        
        # Parcialidad actual es el número de pagos previos + 1
        # Usamos max() por si hay saltos, o count() + 1
        max_parc = 0
        if pagos_rels:
            max_parc = max(rel.num_parcialidad for rel in pagos_rels)
        f.parcialidad_actual = max_parc + 1

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

    # Validar y redondear montos a 2 decimales para evitar errores de precisión (CRP20217)
    pago_monto_d = Decimal(str(pago.monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    total_pagado_en_documentos = Decimal("0.00")
    docs_procesados = []
    
    for doc in pago.documentos:
        # Redondear importe pagado de cada documento
        imp_pagado_d = Decimal(str(doc.imp_pagado)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Validar imp_saldo_ant (aunque es informativo, mejor tenerlo limpio)
        imp_saldo_ant_d = Decimal(str(doc.imp_saldo_ant)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Recalcular saldo insoluto para consistencia
        imp_saldo_insoluto_d = imp_saldo_ant_d - imp_pagado_d
        
        # Actualizar valores en el objeto (copia) que usaremos
        doc.imp_pagado = imp_pagado_d
        doc.imp_saldo_ant = imp_saldo_ant_d
        doc.imp_saldo_insoluto = imp_saldo_insoluto_d
        
        total_pagado_en_documentos += imp_pagado_d
        docs_procesados.append(doc)

    # Validación estricta: Suma de imp_pagado debe ser IGUAL a monto del pago (con 2 decimales)
    # CRP20217
    差 = abs(total_pagado_en_documentos - pago_monto_d)
    if 差 > Decimal("0.00"):
        # Intento de corrección automática por "penny allocation" si la diferencia es mínima (1 centavo)
        # Esto sucede a menudo prorrateando. Ajustamos el último documento.
        if 差 <= Decimal("0.05") and docs_procesados: # Tolerancia de 5 centavos para ajuste auto
            diff = pago_monto_d - total_pagado_en_documentos
            docs_procesados[-1].imp_pagado += diff
            docs_procesados[-1].imp_saldo_insoluto -= diff
            logger.info(f"Ajuste automático de redondeo en pago: {diff} asignado al último documento.")
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El monto total del pago ({pago_monto_d}) no coincide con la suma de los importes pagados ({total_pagado_en_documentos}). Diferencia: {差}",
            )
             
    # Actualizar el monto del pago con el valor redondeado
    pago.monto = pago_monto_d
    pago.documentos = docs_procesados # Usamos la lista con valores redondeados/ajustados

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
        
        # Validar contra el total real de la factura (convertido a Decimal)
        factura_total_d = Decimal(str(factura.total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if doc_in.imp_pagado > factura_total_d:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El importe pagado ({doc_in.imp_pagado}) para la factura {factura.folio} no puede ser mayor a su saldo total ({factura_total_d}).",
            )

        # --- START: Calculate proportional taxes using Decimal ---
        impuestos_dr_json = {"retenciones_dr": [], "traslados_dr": []}
        
        # Usar Decimal para cálculos
        imp_pagado_dec = doc_in.imp_pagado # Ya es Decimal(2)
        factura_total_dec = str(factura.total) # Convertir a str primero
        if not factura_total_dec: factura_total_dec = "0"
        factura_total_dec = Decimal(factura_total_dec)

        if factura_total_dec > 0 and imp_pagado_dec > 0:
            payment_ratio = imp_pagado_dec / factura_total_dec

            retenciones_sum = {}
            traslados_sum = {}

            for concepto in factura.conceptos:
                # Valores base en Decimal
                c_cantidad = Decimal(str(concepto.cantidad))
                c_vunit = Decimal(str(concepto.valor_unitario))
                c_desc = Decimal(str(concepto.descuento or 0))
                
                base_concepto = (c_cantidad * c_vunit) - c_desc
                base_proporcional = base_concepto * payment_ratio

                if concepto.ret_isr_importe and concepto.ret_isr_importe > 0:
                    tasa = str(concepto.ret_isr_tasa)
                    importe_orig = Decimal(str(concepto.ret_isr_importe))
                    importe_prop = importe_orig * payment_ratio
                    
                    if "001" not in retenciones_sum:
                        retenciones_sum["001"] = {}
                    if tasa not in retenciones_sum["001"]:
                        retenciones_sum["001"][tasa] = {"base": Decimal(0), "importe": Decimal(0)}
                    retenciones_sum["001"][tasa]["base"] += base_proporcional
                    retenciones_sum["001"][tasa]["importe"] += importe_prop

                if concepto.ret_iva_importe and concepto.ret_iva_importe > 0:
                    tasa = str(concepto.ret_iva_tasa)
                    importe_orig = Decimal(str(concepto.ret_iva_importe))
                    importe_prop = importe_orig * payment_ratio
                    
                    if "002" not in retenciones_sum:
                        retenciones_sum["002"] = {}
                    if tasa not in retenciones_sum["002"]:
                        retenciones_sum["002"][tasa] = {"base": Decimal(0), "importe": Decimal(0)}
                    retenciones_sum["002"][tasa]["base"] += base_proporcional
                    retenciones_sum["002"][tasa]["importe"] += importe_prop

                if concepto.iva_importe and concepto.iva_importe > 0:
                    tasa = str(concepto.iva_tasa)
                    importe_orig = Decimal(str(concepto.iva_importe))
                    importe_prop = importe_orig * payment_ratio
                    
                    if "002" not in traslados_sum:
                        traslados_sum["002"] = {}
                    if tasa not in traslados_sum["002"]:
                        traslados_sum["002"][tasa] = {"base": Decimal(0), "importe": Decimal(0)}
                    traslados_sum["002"][tasa]["base"] += base_proporcional
                    traslados_sum["002"][tasa]["importe"] += importe_prop

            # Convertir a JSON, pero REDONDEANDO a 2 decimales (moneda) para cumplir validación CRP20274
            for impuesto, tasas in retenciones_sum.items():
                for tasa, montos in tasas.items():
                    base_dr_rounded = montos["base"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    importe_dr_rounded = montos["importe"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    
                    impuestos_dr_json["retenciones_dr"].append(
                        {
                            "base_dr": float(base_dr_rounded),
                            "impuesto_dr": impuesto,
                            "tipo_factor_dr": "Tasa",
                            "tasa_o_cuota_dr": float(tasa),
                            "importe_dr": float(importe_dr_rounded),
                        }
                    )

            for impuesto, tasas in traslados_sum.items():
                for tasa, montos in tasas.items():
                    base_dr_rounded = montos["base"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    importe_dr_rounded = montos["importe"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    
                    impuestos_dr_json["traslados_dr"].append(
                        {
                            "base_dr": float(base_dr_rounded),
                            "impuesto_dr": impuesto,
                            "tipo_factor_dr": "Tasa",
                            # Para tasa, usamos float directo o rounded a 6? Tasa suele ser 0.160000
                            "tasa_o_cuota_dr": float(tasa), 
                            "importe_dr": float(importe_dr_rounded),
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


def actualizar_pago(db: Session, pago_id: UUID, pago_in: PagoCreate) -> Pago:
    db_pago = leer_pago(db, pago_id)
    if not db_pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado"
        )

    if db_pago.estatus != EstatusPago.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar pagos en estatus BORRADOR.",
        )

    if not pago_in.documentos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pago debe tener al menos un documento relacionado.",
        )
    
    # --- Repetimos lógica de redondeo y validación (DRY idealmente, pero por completitud aquí) ---
    pago_monto_d = Decimal(str(pago_in.monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    total_pagado_en_documentos = Decimal("0.00")
    docs_procesados = []

    for doc in pago_in.documentos:
        imp_pagado_d = Decimal(str(doc.imp_pagado)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Validar imp_saldo_ant
        imp_saldo_ant_d = Decimal(str(doc.imp_saldo_ant)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        imp_saldo_insoluto_d = imp_saldo_ant_d - imp_pagado_d
        
        doc.imp_pagado = imp_pagado_d
        doc.imp_saldo_ant = imp_saldo_ant_d
        doc.imp_saldo_insoluto = imp_saldo_insoluto_d
        
        total_pagado_en_documentos += imp_pagado_d
        docs_procesados.append(doc)
    
    差 = abs(total_pagado_en_documentos - pago_monto_d)
    if 差 > Decimal("0.00"):
        if 差 <= Decimal("0.05") and docs_procesados:
            diff = pago_monto_d - total_pagado_en_documentos
            docs_procesados[-1].imp_pagado += diff
            docs_procesados[-1].imp_saldo_insoluto -= diff
            logger.info(f"Ajuste automático de redondeo en pago (editar): {diff}")
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El monto total del pago ({pago_monto_d}) no coincide con la suma de los importes pagados ({total_pagado_en_documentos}).",
            )
            
    # Asignar monto redondeado
    pago_in.monto = pago_monto_d
    pago_in.documentos = docs_procesados
    
    # Actualizar campos simples
    db_pago.fecha_pago = pago_in.fecha_pago
    db_pago.forma_pago_p = pago_in.forma_pago_p
    db_pago.moneda_p = pago_in.moneda_p
    db_pago.tipo_cambio_p = pago_in.tipo_cambio_p
    db_pago.monto = pago_in.monto

    # Limpiar documentos anteriores
    for doc in db_pago.documentos_relacionados:
        db.delete(doc)
    
    # Recrear documentos
    for doc_in in pago_in.documentos:
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
        
        # Validación de monto vs total (Decimal)
        factura_total_d = Decimal(str(factura.total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Ojo: aquí no validamos estrictamente > total si ya estaba pagada por OTRO, 
        # pero es buena práctica no pagar de más.

        # --- START: Calculate proportional taxes using Decimal ---
        impuestos_dr_json = {"retenciones_dr": [], "traslados_dr": []}
        
        imp_pagado_dec = doc_in.imp_pagado
        factura_total_dec = Decimal(str(factura.total)) if factura.total else Decimal("0")
        
        if factura_total_dec > 0 and imp_pagado_dec > 0:
            payment_ratio = imp_pagado_dec / factura_total_dec

            retenciones_sum = {}
            traslados_sum = {}

            for concepto in factura.conceptos:
                c_cantidad = Decimal(str(concepto.cantidad))
                c_vunit = Decimal(str(concepto.valor_unitario))
                c_desc = Decimal(str(concepto.descuento or 0))
                
                base_concepto = (c_cantidad * c_vunit) - c_desc
                base_proporcional = base_concepto * payment_ratio

                if concepto.ret_isr_importe and concepto.ret_isr_importe > 0:
                    tasa = str(concepto.ret_isr_tasa)
                    importe_orig = Decimal(str(concepto.ret_isr_importe))
                    importe_prop = importe_orig * payment_ratio
                    
                    if "001" not in retenciones_sum:
                        retenciones_sum["001"] = {}
                    if tasa not in retenciones_sum["001"]:
                        retenciones_sum["001"][tasa] = {"base": Decimal(0), "importe": Decimal(0)}
                    retenciones_sum["001"][tasa]["base"] += base_proporcional
                    retenciones_sum["001"][tasa]["importe"] += importe_prop

                if concepto.ret_iva_importe and concepto.ret_iva_importe > 0:
                    tasa = str(concepto.ret_iva_tasa)
                    importe_orig = Decimal(str(concepto.ret_iva_importe))
                    importe_prop = importe_orig * payment_ratio
                    
                    if "002" not in retenciones_sum:
                        retenciones_sum["002"] = {}
                    if tasa not in retenciones_sum["002"]:
                        retenciones_sum["002"][tasa] = {"base": Decimal(0), "importe": Decimal(0)}
                    retenciones_sum["002"][tasa]["base"] += base_proporcional
                    retenciones_sum["002"][tasa]["importe"] += importe_prop

                if concepto.iva_importe and concepto.iva_importe > 0:
                    tasa = str(concepto.iva_tasa)
                    importe_orig = Decimal(str(concepto.iva_importe))
                    importe_prop = importe_orig * payment_ratio
                    
                    if "002" not in traslados_sum:
                        traslados_sum["002"] = {}
                    if tasa not in traslados_sum["002"]:
                        traslados_sum["002"][tasa] = {"base": Decimal(0), "importe": Decimal(0)}
                    traslados_sum["002"][tasa]["base"] += base_proporcional
                    traslados_sum["002"][tasa]["importe"] += importe_prop

            # Convert to JSON with Rounding
            for impuesto, tasas in retenciones_sum.items():
                for tasa, montos in tasas.items():
                    base_dr_rounded = montos["base"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    importe_dr_rounded = montos["importe"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    
                    impuestos_dr_json["retenciones_dr"].append(
                        {
                            "base_dr": float(base_dr_rounded),
                            "impuesto_dr": impuesto,
                            "tipo_factor_dr": "Tasa",
                            "tasa_o_cuota_dr": float(tasa),
                            "importe_dr": float(importe_dr_rounded),
                        }
                    )

            for impuesto, tasas in traslados_sum.items():
                for tasa, montos in tasas.items():
                    base_dr_rounded = montos["base"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    importe_dr_rounded = montos["importe"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    
                    impuestos_dr_json["traslados_dr"].append(
                        {
                            "base_dr": float(base_dr_rounded),
                            "impuesto_dr": impuesto,
                            "tipo_factor_dr": "Tasa",
                            "tasa_o_cuota_dr": float(tasa),
                            "importe_dr": float(importe_dr_rounded),
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
            detail=f"Error al actualizar pago: {e}",
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
                    factura_a_actualizar.fecha_cobro = pago.fecha_pago

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
    if pago.estatus not in ["TIMBRADO", EstatusPago.CANCELADO]:
        raise HTTPException(
            status_code=409, detail="El pago debe estar TIMBRADO o CANCELADO para descargar el XML"
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
    db.delete(pago)
    db.commit()
    return {"message": "Pago eliminado exitosamente."}


def cancelar_pago_sat(
    db: Session, pago_id: UUID, motivo: str, folio_sustituto: Optional[str] = None
) -> dict:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado"
        )

    if pago.estatus != EstatusPago.TIMBRADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar un pago con estatus {pago.estatus}. Solo TIMBRADO.",
        )

    # Validacion motivo 01
    if motivo == "01" and not folio_sustituto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para motivo '01' se requiere folio sustituto.",
        )

    try:
        # 1. Llamada al PAC
        res = _pac.solicitar_cancelacion_pago(
            db=db,
            pago_id=pago_id,
            motivo=motivo,
            folio_sustituto=folio_sustituto,
        )

        # 2. Actualizar estatus del pago
        pago.estatus = EstatusPago.CANCELADO
        pago.motivo_cancelacion = motivo
        pago.folio_fiscal_sustituto = folio_sustituto
        # Nota: no tenemos campos para fecha de solicitud o mensaje del PAC en Pago,
        # pero guardamos el motivo y sustituto que sí existen.

        # 3. Revertir estatus de facturas relacionadas
        # Si una factura estaba PAGADA gracias a este pago, la regresamos a NO_PAGADA.
        for doc in pago.documentos_relacionados:
            factura = db.query(Factura).filter(Factura.id == doc.factura_id).first()
            if factura and factura.status_pago == "PAGADA":
                # Asumimos que al cancelar este pago, deja de estar pagada en su totalidad.
                # En un sistema más complejo, recalcularíamos el saldo con los pagos restantes.
                factura.status_pago = "NO_PAGADA"
                factura.fecha_cobro = None
        
        db.add(pago)
        db.commit()
        db.refresh(pago)

        return {
            "message": "Solicitud de cancelación enviada exitosamente.",
            "pago_estatus": pago.estatus,
            "pac_response": res,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al cancelar pago {pago_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la cancelación: {str(e)}",
        )
