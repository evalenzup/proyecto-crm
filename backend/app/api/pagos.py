import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, FileResponse
import os
from sqlalchemy.orm import Session, selectinload
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, FileResponse
import os
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from datetime import date
from sqlalchemy import cast, Integer, or_

from app.database import get_db
from app.models.pago import Pago, PagoDocumentoRelacionado
from app.models.factura import Factura
from app.schemas.pago import Pago as PagoSchema, PagoCreate, PagoListResponse
from app.schemas.factura import FacturaOut
from app.services import pago_service
from app.services.pdf_pago import render_pago_pdf_bytes_from_model
from app.services.email_sender import send_pago_email, EmailSendingError
from app.schemas.factura import FacturaOut, SendEmailIn

router = APIRouter()

@router.post("/", response_model=PagoSchema, status_code=201)
def crear_pago(pago: PagoCreate, db: Session = Depends(get_db)):
    return pago_service.crear_pago(db, pago)

@router.get("/siguiente-folio", response_model=int)
def get_siguiente_folio(empresa_id: uuid.UUID, serie: str = 'P', db: Session = Depends(get_db)):
    return pago_service.siguiente_folio_pago(db, empresa_id, serie)

@router.get("/debug-folios")
def debug_folios(empresa_id: uuid.UUID, serie: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Pago).filter(Pago.empresa_id == empresa_id)
    if serie:
        query = query.filter(Pago.serie == serie)
    else:
        query = query.filter(or_(Pago.serie == None, Pago.serie == ''))
    
    pagos = query.order_by(cast(Pago.folio, Integer)).all()
    
    result = []
    for pago in pagos:
        result.append({"id": pago.id, "serie": pago.serie, "folio": pago.folio})
    return result

@router.get("/", response_model=PagoListResponse)
def listar_pagos(
    db: Session = Depends(get_db),
    offset: int = 0,
    limit: int = 10,
    order_by: str = 'fecha_pago',
    order_dir: str = 'desc',
    empresa_id: Optional[uuid.UUID] = None,
    cliente_id: Optional[uuid.UUID] = None,
    estatus: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
):
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
        if order_dir == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())

    # Apply pagination
    pagos = query.offset(offset).limit(limit).all()

    return {"items": pagos, "total": total}

@router.get("/{pago_id}", response_model=PagoSchema)
def leer_pago(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    db_pago = db.query(Pago).options(
        selectinload(Pago.documentos_relacionados).selectinload(PagoDocumentoRelacionado.factura)
    ).filter(Pago.id == pago_id).first()
    if db_pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return db_pago

@router.delete("/{pago_id}", status_code=200)
def delete_pago(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    return pago_service.eliminar_pago(db, pago_id)

@router.post("/{pago_id}/set-to-borrador", summary="DEBUG: Establecer pago a estado BORRADOR")
def set_pago_to_borrador(pago_id: uuid.UUID, db: Session = Depends(get_db)):
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
    return {"message": f"Pago {pago_id} establecido a BORRADOR.", "pago_estatus": pago.estatus}

@router.get("/clientes/{cliente_id}/facturas-pendientes", response_model=List[FacturaOut])
def listar_facturas_pendientes_por_cliente(cliente_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Obtiene todas las facturas de un cliente que tienen estatus de pago 'NO_PAGADA'
    y que han sido timbradas.
    """
    facturas = db.query(Factura).filter(
        Factura.cliente_id == cliente_id,
        Factura.status_pago == 'NO_PAGADA',
        Factura.estatus == 'TIMBRADA'
    ).order_by(Factura.fecha_emision.desc()).all()
    
    return facturas

@router.post("/{pago_id}/timbrar", summary="Timbrar un complemento de pago")
def timbrar_pago_endpoint(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    return pago_service.timbrar_pago(db, pago_id)

@router.get("/{pago_id}/pdf", summary="Obtener el PDF del pago")
def get_pago_pdf(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        pdf_bytes = render_pago_pdf_bytes_from_model(db, pago_id, preview=True)
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        folio_str = f"{pago.serie}-{pago.folio}" if pago and pago.serie else str(pago.folio) if pago else str(pago_id)
        filename = f"Pago-{folio_str}.pdf"
        
        headers = {
            'Content-Disposition': f'inline; filename="{filename}"'
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Idealmente, aquí se registraría el error `e` en un sistema de logging
        raise HTTPException(status_code=500, detail=f"No se pudo generar el PDF del pago: {e}")

@router.get("/{pago_id}/xml", summary="Descargar el XML del pago")
def get_pago_xml(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    xml_path, filename = pago_service.obtener_ruta_xml_pago(db, pago_id)
    
    if not os.path.exists(xml_path):
        raise HTTPException(status_code=404, detail=f"El archivo XML para el pago no fue encontrado en la ruta: {xml_path}")

    return FileResponse(path=xml_path, media_type="application/xml", filename=filename)

@router.post("/{pago_id}/enviar-email", summary="Enviar complemento de pago por correo electrónico")
async def enviar_pago_por_email(
    pago_id: uuid.UUID,
    email_data: SendEmailIn,
    db: Session = Depends(get_db)
):
    try:
        # Generar el PDF del pago
        pdf_bytes = render_pago_pdf_bytes_from_model(db, pago_id)
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        folio_str = f"{pago.serie}-{pago.folio}" if pago and pago.serie else str(pago.folio) if pago else str(pago_id)
        pdf_filename = f"Pago-{folio_str}.pdf"

        # Obtener el XML del pago
        xml_path, xml_filename = pago_service.obtener_ruta_xml_pago(db, pago_id)
        xml_content = None
        if not os.path.exists(xml_path):
            raise HTTPException(status_code=404, detail=f"XML para el pago no encontrado, no se puede enviar el correo.")
        
        with open(xml_path, "rb") as f:
            xml_content = f.read()

        # Enviar correo
        await send_pago_email(
            db=db,
            pago_id=pago_id,
            recipients=email_data.recipients,
            subject=email_data.subject,
            body=email_data.body,
            pdf_content=pdf_bytes,
            pdf_filename=pdf_filename,
            xml_content=xml_content,
            xml_filename=xml_filename
        )
        return {"message": "Complemento de pago enviado por correo electrónico exitosamente."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EmailSendingError as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar el correo electrónico: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")