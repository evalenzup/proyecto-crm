from sqlalchemy.orm import Session, selectinload
from sqlalchemy import cast, Integer, or_
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.pago import Pago, PagoDocumentoRelacionado
from app.models.factura import Factura
from app.schemas.pago import PagoCreate
from app.services.pago20_xml import build_pago20_xml_sin_timbrar
from app.services.timbrado_factmoderna import FacturacionModernaPAC
from uuid import UUID
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

_pac = FacturacionModernaPAC()

def siguiente_folio_pago(db: Session, empresa_id: UUID, serie: str) -> int:
    logger.info(f"siguiente_folio_pago called with empresa_id: {empresa_id}, serie: {serie}")
    query = db.query(Pago).filter(Pago.empresa_id == empresa_id)

    if serie:
        query = query.filter(Pago.serie == serie)
    else:
        query = query.filter(or_(Pago.serie == None, Pago.serie == ''))

    latest_pago = (
        query
        .order_by(cast(Pago.folio, Integer).desc())
        .with_for_update()
        .first()
    )
    result_folio = int(latest_pago.folio) + 1 if latest_pago else 1
    logger.info(f"latest_pago: {latest_pago}")
    logger.info(f"Returning folio: {result_folio}")
    return result_folio

def crear_pago(db: Session, pago: PagoCreate):
    logger.info(f"crear_pago called with payload: {pago.dict()}")
    if not pago.documentos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pago debe tener al menos un documento relacionado."
        )

    total_pagado_en_documentos = sum(doc.imp_pagado for doc in pago.documentos)
    if not abs(total_pagado_en_documentos - pago.monto) < Decimal('0.01'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto total del pago ({pago.monto}) no coincide con la suma de los importes pagados en los documentos ({total_pagado_en_documentos})."
        )

    serie = (pago.serie or "P").upper()
    folio = pago.folio if pago.folio is not None else str(siguiente_folio_pago(db, pago.empresa_id, serie))

    logger.info(f"Generated serie: {serie}, folio: {folio}")

    db_pago = Pago(**pago.dict(exclude={"documentos", "serie", "folio"}))
    db_pago.serie = serie
    db_pago.folio = folio
    
    for doc_in in pago.documentos:
        factura = db.query(Factura).options(selectinload(Factura.conceptos)).filter(Factura.id == doc_in.factura_id).first()
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La factura con ID {doc_in.factura_id} no fue encontrada."
            )
        
        if factura.status_pago == "PAGADA":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La factura {factura.folio} ya ha sido pagada."
            )

        if doc_in.imp_pagado > factura.total:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El importe pagado ({doc_in.imp_pagado}) para la factura {factura.folio} no puede ser mayor a su saldo total ({factura.total})."
            )

        # --- START: Calculate proportional taxes ---
        impuestos_dr_json = {"retenciones_dr": [], "traslados_dr": []}
        if factura.total > 0 and doc_in.imp_pagado > 0:
            payment_ratio = doc_in.imp_pagado / factura.total
            
            retenciones_sum = {}
            traslados_sum = {}

            for concepto in factura.conceptos:
                base_proporcional = (concepto.cantidad * concepto.valor_unitario - concepto.descuento) * payment_ratio

                if concepto.ret_isr_importe and concepto.ret_isr_importe > 0:
                    tasa = str(concepto.ret_isr_tasa)
                    if '001' not in retenciones_sum: retenciones_sum['001'] = {}
                    if tasa not in retenciones_sum['001']: retenciones_sum['001'][tasa] = {'base': 0, 'importe': 0}
                    retenciones_sum['001'][tasa]['base'] += base_proporcional
                    retenciones_sum['001'][tasa]['importe'] += concepto.ret_isr_importe * payment_ratio

                if concepto.ret_iva_importe and concepto.ret_iva_importe > 0:
                    tasa = str(concepto.ret_iva_tasa)
                    if '002' not in retenciones_sum: retenciones_sum['002'] = {}
                    if tasa not in retenciones_sum['002']: retenciones_sum['002'][tasa] = {'base': 0, 'importe': 0}
                    retenciones_sum['002'][tasa]['base'] += base_proporcional
                    retenciones_sum['002'][tasa]['importe'] += concepto.ret_iva_importe * payment_ratio

                if concepto.iva_importe and concepto.iva_importe > 0:
                    tasa = str(concepto.iva_tasa)
                    if '002' not in traslados_sum: traslados_sum['002'] = {}
                    if tasa not in traslados_sum['002']: traslados_sum['002'][tasa] = {'base': 0, 'importe': 0}
                    traslados_sum['002'][tasa]['base'] += base_proporcional
                    traslados_sum['002'][tasa]['importe'] += concepto.iva_importe * payment_ratio

            for impuesto, tasas in retenciones_sum.items():
                for tasa, montos in tasas.items():
                    impuestos_dr_json["retenciones_dr"].append({
                        "base_dr": float(montos['base']),
                        "impuesto_dr": impuesto,
                        "tipo_factor_dr": "Tasa",
                        "tasa_o_cuota_dr": float(tasa),
                        "importe_dr": float(montos['importe'])
                    })

            for impuesto, tasas in traslados_sum.items():
                for tasa, montos in tasas.items():
                    impuestos_dr_json["traslados_dr"].append({
                        "base_dr": float(montos['base']),
                        "impuesto_dr": impuesto,
                        "tipo_factor_dr": "Tasa",
                        "tasa_o_cuota_dr": float(tasa),
                        "importe_dr": float(montos['importe'])
                    })

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
            tipo_cambio_dr=doc_in.tipo_cambio_dr
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
            detail=f"Error al guardar en la base de datos: {e}"
        )

    return db_pago

def timbrar_pago(db: Session, pago_id: UUID) -> dict:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pago.estatus != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se puede timbrar un pago en BORRADOR")

    try:
        result = _pac.timbrar_pago(db=db, pago_id=pago_id, generar_cbb=False, generar_txt=False, generar_pdf=False)
        
        pago.estatus = "TIMBRADO"
        pago.uuid = result["uuid"]
        pago.fecha_timbrado = datetime.utcnow()
        pago.xml_path = result.get("xml_path")
        
        for doc in pago.documentos_relacionados:
            factura_a_actualizar = db.query(Factura).filter(Factura.id == doc.factura_id).first()
            if factura_a_actualizar:
                if doc.imp_saldo_insoluto == 0:
                    factura_a_actualizar.status_pago = "PAGADA"
        
        db.commit()
        db.refresh(pago)

        return {"ok": True, "uuid": pago.uuid, "message": "Pago timbrado exitosamente."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno al timbrar el pago: {e}")

def obtener_ruta_xml_pago(db: Session, pago_id: UUID) -> tuple[str, str]:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pago.estatus != "TIMBRADO":
        raise HTTPException(status_code=409, detail="El pago debe estar TIMBRADO para descargar el XML")
    
    if not pago.xml_path:
        raise HTTPException(status_code=404, detail="Ruta de XML no encontrada para este pago.")

    filename = f"PAGO-{pago.folio}.xml"
    
    return pago.xml_path, filename

def eliminar_pago(db: Session, pago_id: UUID):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    if pago.estatus != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar pagos en BORRADOR")
    
    db.delete(pago)
    db.commit()
    return {"message": "Pago eliminado exitosamente."}