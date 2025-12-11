# app/api/factura.py
from __future__ import annotations
import logging
import os
from uuid import UUID
from typing import List, Optional, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.models.factura import Factura
from app.models.usuario import Usuario, RolUsuario
from app.api import deps
from app.schemas.factura import FacturaCreate, FacturaUpdate, FacturaOut

# Catálogos (se mantienen aquí por ser data de solo lectura para el schema del UI)

# Importaciones del nuevo servicio refactorizado
from app.services import factura_service as srv

# Importaciones para el envío de correo
from app.services import email_sender
from app.services.email_sender import EmailSendingError

logger = logging.getLogger("app")
router = APIRouter()

# ────────────────────────────────────────────────────────────────
# Modelos de Respuesta/Entrada específicos de la API


class FlexibleSendEmailIn(BaseModel):
    # Acepta múltiples formatos para compatibilidad hacia atrás con el frontend
    recipients: Optional[List[str]] = None
    recipient_email: Optional[str] = None
    recipient_emails: Optional[str] = None  # coma-separado
    subject: Optional[str] = None
    body: Optional[str] = None

    def normalized_recipients(self) -> List[str]:
        # Prioridad: lista -> recipient_emails (csv) -> recipient_email
        if self.recipients:
            return [e.strip() for e in self.recipients if e and e.strip()]
        if self.recipient_emails:
            return [
                e.strip() for e in self.recipient_emails.split(",") if e and e.strip()
            ]
        if self.recipient_email:
            return (
                [self.recipient_email.strip()] if self.recipient_email.strip() else []
            )
        return []


class FacturasPageOut(BaseModel):
    items: List[FacturaOut]
    total: int
    limit: int
    offset: int


class CancelarIn(BaseModel):
    motivo_cancelacion: str = "02"
    folio_fiscal_sustituto: str | None = None

    @field_validator("motivo_cancelacion")
    @classmethod
    def check_motivo(cls, v: str):
        v = (v or "").strip()
        if v not in {"01", "02", "03", "04"}:
            raise ValueError("Motivo inválido. Valores permitidos: 01, 02, 03, 04.")
        return v


# ────────────────────────────────────────────────────────────────
# Endpoints


@router.get("/schema", summary="Obtener el schema del modelo para UI")
def get_form_schema_factura():
    schema = FacturaCreate.schema()
    # ... (la lógica para enriquecer el schema se mantiene, es específica de la UI)
    return schema


@router.post("/", response_model=FacturaOut, status_code=status.HTTP_201_CREATED)
def crear_factura_endpoint(
    payload: FacturaCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
) -> Factura:
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="El usuario supervisor no tiene empresa asignada.")
        payload.empresa_id = current_user.empresa_id
    return srv.crear_factura(db, payload)


@router.put("/{id}", response_model=FacturaOut)
def actualizar_factura_endpoint(
    id: UUID, 
    payload: FacturaUpdate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
) -> Factura:
    factura = srv.obtener_factura(db, id) # Verificamos existencia y propiedad antes
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    if current_user.rol == RolUsuario.SUPERVISOR:
        if factura.empresa_id != current_user.empresa_id:
            raise HTTPException(status_code=404, detail="Factura no encontrada") # Ocultamos que existe
        payload.empresa_id = current_user.empresa_id # Prevenir cambio de empresa

    return srv.actualizar_factura(db, id, payload)


@router.get("/{id}", response_model=FacturaOut)
def obtener_factura(
    id: UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
) -> Factura:
    factura = srv.obtener_factura(db, id=id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    return factura


@router.get("/", response_model=FacturasPageOut)
def listar_facturas_endpoint(
    db: Session = Depends(get_db),
    empresa_id: Optional[UUID] = Query(None),
    cliente_id: Optional[UUID] = Query(None),
    serie: Optional[str] = Query(None),
    folio_min: Optional[int] = Query(None),
    folio_max: Optional[int] = Query(None),
    estatus: Optional[Literal["BORRADOR", "TIMBRADA", "CANCELADA"]] = Query(None),
    status_pago: Optional[Literal["PAGADA", "NO_PAGADA"]] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    order_by: Literal["serie_folio", "fecha", "total"] = Query("serie_folio"),
    order_dir: Literal["asc", "desc"] = Query("asc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    items, total = srv.listar_facturas(
        db,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        serie=serie,
        folio_min=folio_min,
        folio_max=folio_max,
        estatus=estatus,
        status_pago=status_pago,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_factura(
    id: UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = srv.obtener_factura(db, id) # Consulta previa para validar
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    return srv.eliminar_factura(db, id=id)


@router.patch("/{id}/pago", response_model=FacturaOut)
def marcar_pago(
    id: UUID,
    status: Literal["PAGADA", "NO_PAGADA"],
    fecha_pago: Optional[date] = Query(None),
    fecha_cobro: Optional[date] = Query(None),
    db: Session = Depends(get_db),
) -> Factura:
    return srv.marcar_pago_factura(db, id, status, fecha_pago, fecha_cobro)


@router.get("/por-folio", response_model=FacturaOut)
def obtener_por_folio_endpoint(
    empresa_id: UUID, serie: str, folio: int, db: Session = Depends(get_db)
) -> Factura:
    factura = srv.obtener_por_serie_folio(db, empresa_id, serie, folio)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura


# --- Endpoints de Acciones CFDI ---


@router.post("/{id}/timbrar", summary="Timbrar factura con PAC")
def timbrar_endpoint(
    id: UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = srv.obtener_factura(db, id)
    if not factura: 
         raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    return srv.timbrar_factura(db, id)


@router.post("/{id}/cancelar")
def solicitar_cancelacion_endpoint(
    id: UUID, payload: CancelarIn, db: Session = Depends(get_db)
):
    return srv.solicitar_cancelacion_cfdi(
        db, id, payload.motivo_cancelacion, payload.folio_fiscal_sustituto
    )


# --- Endpoints de Archivos ---


@router.post("/{id}/xml-preview", summary="Genera XML CFDI 4.0 sin timbrar")
def generar_xml_preview(id: UUID, db: Session = Depends(get_db)):
    xml_bytes = srv.generar_xml_preview_bytes(db, id)
    return Response(content=xml_bytes, media_type="application/xml")


@router.get("/{id}/preview-pdf", summary="PDF de vista previa (marca BORRADOR)")
def preview_pdf(id: UUID, db: Session = Depends(get_db)):
    pdf_bytes = srv.generar_pdf_bytes(db, id, preview=True)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="preview-{id}.pdf"'},
    )


@router.get("/{id}/pdf", summary="PDF final (TIMBRADA o CANCELADA)")
def factura_pdf(id: UUID, db: Session = Depends(get_db)):
    pdf_bytes = srv.generar_pdf_bytes(db, id, preview=False)
    # El nombre del archivo se podría obtener del servicio también si se quisiera.
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="factura-{id}.pdf"'},
    )


@router.get("/{id}/xml", summary="Descargar XML timbrado")
def descargar_xml_timbrado(id: UUID, db: Session = Depends(get_db)):
    xml_path_from_db, filename = srv.obtener_ruta_xml_timbrado(db, id)

    base_dir = os.path.realpath(getattr(settings, "DATA_DIR", "/data"))

    # Determine the full, unsafe path
    if os.path.isabs(xml_path_from_db):
        unsafe_path = xml_path_from_db
    else:
        unsafe_path = os.path.join(base_dir, xml_path_from_db.lstrip("/"))

    # Resolve the real path to prevent traversal attacks
    safe_path = os.path.realpath(unsafe_path)

    # Check if the resolved path is within the secure base directory
    if not safe_path.startswith(base_dir):
        raise HTTPException(
            status_code=403,
            detail="Acceso prohibido: intento de acceso fuera del directorio de datos.",
        )

    if not os.path.exists(safe_path):
        raise HTTPException(
            status_code=404, detail="El archivo XML no se encuentra en el servidor"
        )

    return FileResponse(path=safe_path, media_type="application/xml", filename=filename)


# --- Endpoint de Envío de Correo ---

def _handle_send_email(
    id: UUID,
    payload: FlexibleSendEmailIn,
    db: Session,
    send_function: callable,
    email_type: str,
):
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    recipient_emails = payload.normalized_recipients()
    if not recipient_emails:
        raise HTTPException(
            status_code=400,
            detail="No se encontraron correos electrónicos válidos para enviar.",
        )

    sent_to = []
    failed_to_send = []

    for email in recipient_emails:
        try:
            send_function(
                db=db,
                empresa_id=factura.empresa_id,
                factura_id=id,
                recipient_email=email,
            )
            sent_to.append(email)
        except EmailSendingError as e:
            failed_to_send.append(f"{email}: {e}")
        except Exception as e:
            logger.error(
                f"Error inesperado al enviar correo de {email_type} para factura {id} a {email}: {e}"
            )
            failed_to_send.append(f"{email}: Error inesperado en el servidor.")

    if failed_to_send:
        raise HTTPException(
            status_code=400,
            detail=f"Errores al enviar a algunos destinatarios: {'; '.join(failed_to_send)}. Enviado a: {', '.join(sent_to) if sent_to else 'ninguno'}.",
        )

    return {
        "message": f"{email_type.capitalize()} enviada correctamente a: {', '.join(sent_to)}"
    }


@router.post(
    "/{id}/send-preview-email",
    status_code=status.HTTP_200_OK,
    summary="Enviar vista previa de factura por correo electrónico",
)
def send_preview_factura_by_email(
    id: UUID, payload: FlexibleSendEmailIn, db: Session = Depends(get_db)
):
    """Envía la vista previa de la factura (PDF) a los correos especificados por el usuario."""
    return _handle_send_email(
        id, payload, db, email_sender.send_preview_invoice_email, "Vista previa de factura"
    )


@router.post(
    "/{id}/send-email",
    status_code=status.HTTP_200_OK,
    summary="Enviar factura por correo electrónico",
)
def send_factura_by_email(
    id: UUID, payload: FlexibleSendEmailIn, db: Session = Depends(get_db)
):
    """Envía la factura (PDF y XML) a los correos especificados por el usuario."""
    return _handle_send_email(
        id, payload, db, email_sender.send_invoice_email, "Factura"
    )
