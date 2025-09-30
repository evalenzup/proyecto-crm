from sqlalchemy.orm import Session
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

    if serie: # If serie is provided, filter by it
        query = query.filter(Pago.serie == serie)
    else: # If serie is not provided, filter by null or empty serie
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
    # --- 1. Validaciones ---
    if not pago.documentos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pago debe tener al menos un documento relacionado."
        )

    total_pagado_en_documentos = sum(doc.imp_pagado for doc in pago.documentos)
    # Use a small tolerance for float comparison
    if not abs(total_pagado_en_documentos - pago.monto) < Decimal('0.01'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto total del pago ({pago.monto}) no coincide con la suma de los importes pagados en los documentos ({total_pagado_en_documentos})."
        )

    # --- 2. Crear objetos de BD ---
    serie = (pago.serie or "P").upper()
    folio = pago.folio if pago.folio is not None else str(siguiente_folio_pago(db, pago.empresa_id, serie))

    logger.info(f"Generated serie: {serie}, folio: {folio}")

    db_pago = Pago(**pago.dict(exclude={"documentos", "serie", "folio"}))
    db_pago.serie = serie
    db_pago.folio = folio
    
    for doc_in in pago.documentos:
        factura = db.query(Factura).filter(Factura.id == doc_in.factura_id).first()
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

        # A real system would have a 'saldo' field. We use 'total' as a proxy.
        if doc_in.imp_pagado > factura.total:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El importe pagado ({doc_in.imp_pagado}) para la factura {factura.folio} no puede ser mayor a su saldo total ({factura.total})."
            )

        db_doc = PagoDocumentoRelacionado(
            factura_id=factura.id,
            id_documento=factura.cfdi_uuid, # Important: this is the invoice UUID
            serie=factura.serie,
            folio=str(factura.folio),
            moneda_dr=factura.moneda,
            num_parcialidad=doc_in.num_parcialidad,
            imp_saldo_ant=doc_in.imp_saldo_ant,
            imp_pagado=doc_in.imp_pagado,
            imp_saldo_insoluto=doc_in.imp_saldo_insoluto,
        )
        db_pago.documentos_relacionados.append(db_doc)

    # --- 3. Guardar en BD --- 
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
        # This is a placeholder call, as the XML builder is not fully implemented
        xml_sin_timbre = build_pago20_xml_sin_timbrar(db, pago_id)
        
        # The following is a placeholder for the real PAC call
        # result = _pac.timbrar_pago(db, pago_id, xml_sin_timbre)
        
        # For now, just simulate a successful timbrado
        pago.estatus = "TIMBRADO"
        pago.uuid = str(UUID(int=0x12345))
        pago.fecha_timbrado = datetime.utcnow()
        # Set dummy values for new CFDI fields
        pago.no_certificado = "00001000000500000000"
        pago.no_certificado_sat = "00001000000400000000"
        pago.sello_cfdi = "DUMMY_SELLO_CFDI"
        pago.sello_sat = "DUMMY_SELLO_SAT"
        pago.rfc_proveedor_sat = "AAA010101AAA"
        
        # --- Actualizar saldo de facturas ---
        for doc in pago.documentos_relacionados:
            factura_a_actualizar = db.query(Factura).filter(Factura.id == doc.factura_id).first()
            if factura_a_actualizar:
                if doc.imp_saldo_insoluto == 0:
                    factura_a_actualizar.status_pago = "PAGADA"
                else:
                    # In a real scenario, you would update a 'saldo' field.
                    pass
        
        db.commit()
        db.refresh(pago)

        return {"ok": True, "uuid": pago.uuid, "message": "Timbrado simulado exitosamente."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno al timbrar el pago: {e}")

def generar_pdf_pago_bytes(db: Session, pago_id: UUID) -> bytes:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Placeholder: return a dummy PDF
    dummy_pdf_content = f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 52 >>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Dummy PDF for Pago {pago.id}) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000118 00000 n \n0000000198 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n284\n%%EOF"
    return dummy_pdf_content.encode('utf-8')

def obtener_ruta_xml_pago(db: Session, pago_id: UUID) -> tuple[str, str]:
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pago.estatus != "TIMBRADO":
        raise HTTPException(status_code=409, detail="El pago debe estar TIMBRADO para descargar el XML")
    
    dummy_path = f"/data/cfdis/dummy-pago-{pago.id}.xml"
    filename = f"PAGO-{pago.folio}.xml"
    
    return dummy_path, filename

def eliminar_pago(db: Session, pago_id: UUID):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    if pago.estatus != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar pagos en BORRADOR")
    
    db.delete(pago)
    db.commit()
    return {"message": "Pago eliminado exitosamente."}
