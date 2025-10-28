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
from app.schemas.factura import SendEmailIn
from app.config import settings

router = APIRouter()


@router.post("/", response_model=PagoSchema, status_code=201)
def crear_pago(pago: PagoCreate, db: Session = Depends(get_db)):
    return pago_service.crear_pago(db, pago)


@router.get("/siguiente-folio", response_model=int)
def get_siguiente_folio(
    empresa_id: uuid.UUID, serie: str = "P", db: Session = Depends(get_db)
):
    return pago_service.siguiente_folio_pago(db, empresa_id, serie)


@router.get("/debug-folios")
def debug_folios(
    empresa_id: uuid.UUID,
    serie: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Pago).filter(Pago.empresa_id == empresa_id)
    if serie:
        query = query.filter(Pago.serie == serie)
    else:
        query = query.filter(or_(Pago.serie.is_(None), Pago.serie == ""))

    pagos = query.order_by(cast(Pago.folio, Integer)).all()

    result = []
    for pago in pagos:
        result.append({"id": pago.id, "serie": pago.serie, "folio": pago.folio})
    return result


@router.get("/", response_model=PagoListResponse)
def listar_pagos(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=200),
    order_by: str = "fecha_pago",
    order_dir: str = "desc",
    empresa_id: Optional[uuid.UUID] = None,
    cliente_id: Optional[uuid.UUID] = None,
    estatus: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
):
    items, total = pago_service.listar_pagos(
        db,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        estatus=estatus,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{pago_id}", response_model=PagoSchema)
def leer_pago(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    return pago_service.leer_pago(db, pago_id)


@router.delete("/{pago_id}", status_code=200)
def delete_pago(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    return pago_service.eliminar_pago(db, pago_id)


@router.post(
    "/{pago_id}/set-to-borrador", summary="DEBUG: Establecer pago a estado BORRADOR"
)
def set_pago_to_borrador(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    pago = pago_service.set_pago_to_borrador(db, pago_id)
    return {
        "message": f"Pago {pago.id} establecido a BORRADOR.",
        "pago_estatus": pago.estatus,
    }


@router.get(
    "/clientes/{cliente_id}/facturas-pendientes", response_model=List[FacturaOut]
)
def listar_facturas_pendientes_por_cliente(
    cliente_id: uuid.UUID, db: Session = Depends(get_db)
):
    return pago_service.listar_facturas_pendientes_por_cliente(db, cliente_id)


@router.post("/{pago_id}/timbrar", summary="Timbrar un complemento de pago")
def timbrar_pago_endpoint(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    return pago_service.timbrar_pago(db, pago_id)


@router.get("/{pago_id}/pdf", summary="Obtener el PDF del pago")
def get_pago_pdf(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    pdf_bytes, filename = pago_service.get_pago_pdf(db, pago_id)
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/{pago_id}/xml", summary="Descargar el XML del pago")
def get_pago_xml(pago_id: uuid.UUID, db: Session = Depends(get_db)):
    xml_path_from_db, filename = pago_service.obtener_ruta_xml_pago(db, pago_id)

    # --- Path sanitization ---
    base_dir = os.path.realpath(getattr(settings, "DATA_DIR", "/data"))

    if os.path.isabs(xml_path_from_db):
        unsafe_path = xml_path_from_db
    else:
        unsafe_path = os.path.join(base_dir, xml_path_from_db.lstrip("/"))

    safe_path = os.path.realpath(unsafe_path)

    if not safe_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Acceso prohibido.")

    if not os.path.exists(safe_path):
        raise HTTPException(
            status_code=404,
            detail=f"El archivo XML para el pago no fue encontrado en la ruta: {safe_path}",
        )

    return FileResponse(path=safe_path, media_type="application/xml", filename=filename)


@router.post(
    "/{pago_id}/enviar-email",
    summary="Enviar complemento de pago por correo electrónico",
)
async def enviar_pago_por_email(
    pago_id: uuid.UUID, email_data: SendEmailIn, db: Session = Depends(get_db)
):
    return await pago_service.enviar_pago_por_email(
        db,
        pago_id,
        recipients=email_data.recipients,
        subject=email_data.subject,
        body=email_data.body,
    )
