# app/api/factura.py
from __future__ import annotations
import logging
import os
from uuid import UUID
from typing import List, Optional, Literal
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, selectinload

from app.utils.excel import generate_excel

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
from app.models.email_config import EmailConfig
from app.core.limiter import limiter
from app.services import auditoria_service as audit_svc

# Catálogos para exportación
from app.catalogos_sat.facturacion import (
    METODO_PAGO, 
    FORMA_PAGO, 
    USO_CFDI
)
from app.catalogos_sat.regimenes_fiscales import REGIMENES_FISCALES_SAT

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
    result = srv.crear_factura(db, payload)
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.CREAR_FACTURA, entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=result.empresa_id, entidad_id=str(result.id),
            detalle={"serie": result.serie, "folio": result.folio, "total": str(result.total)},
        )
        db.commit()
    except Exception:
        pass
    return result



@router.get("/export-excel")
def exportar_facturas_excel(
    db: Session = Depends(get_db),
    empresa_id: Optional[UUID] = Query(None),
    cliente_id: Optional[UUID] = Query(None),
    serie: Optional[str] = Query(None),
    folio: Optional[int] = Query(None),
    folio_min: Optional[int] = Query(None),
    folio_max: Optional[int] = Query(None),
    estatus: Optional[Literal["BORRADOR", "TIMBRADA", "CANCELADA"]] = Query(None),
    status_pago: Optional[Literal["PAGADA", "NO_PAGADA"]] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    # Obtener todos los registros (sin paginación estricta, pero ponemos un límite seguro)
    items, _ = srv.listar_facturas(
        db,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        serie=serie,
        folio=folio,
        folio_min=folio_min,
        folio_max=folio_max,
        estatus=estatus,
        status_pago=status_pago,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        order_by="fecha",
        order_dir="desc",
        limit=1000000, # Límite aumentado para exportar todo
        offset=0,
    )

    # Preparar mapas de catálogos
    map_metodos = {i["clave"]: i["descripcion"] for i in METODO_PAGO}
    # map_formas = {i["clave"]: i["descripcion"] for i in FORMA_PAGO} # Si se usa forma_pago
    
    # Preparar datos para Excel
    data_list = []
    for f in items:
        cliente_nombre = "—"
        if f.cliente:
            cliente_nombre = f.cliente.nombre_comercial or f.cliente.nombre_razon_social or "—"
        
        # Obtener descripción de método de pago si existe
        metodo_desc = f.metodo_pago
        if f.metodo_pago and f.metodo_pago in map_metodos:
            metodo_desc = f"{f.metodo_pago} - {map_metodos[f.metodo_pago]}"

        data_list.append({
            "folio_completo": f"{f.serie or ''}-{f.folio or ''}",
            "fecha": f.fecha_emision,
            "cliente": cliente_nombre,
            "rfc": f.cliente.rfc if f.cliente else "",
            "metodo_pago": metodo_desc,
            "total": f.total,
            "moneda": f.moneda,
            "estatus": f.estatus,
            "status_pago": f.status_pago,
        })

    headers = {
        "folio_completo": "Folio",
        "fecha": "Fecha Emisión",
        "cliente": "Cliente",
        "rfc": "RFC Receptor",
        "metodo_pago": "Método Pago",
        "total": "Total",
        "moneda": "Moneda",
        "estatus": "Estatus CFDI",
        "status_pago": "Estatus Pago",
    }

    excel_file = generate_excel(data_list, headers, sheet_name="Facturas")
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.EXPORTAR_EXCEL, entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=empresa_id, detalle={"registros": len(data_list)},
        )
        db.commit()
    except Exception:
        pass
    headers_resp = {
        "Content-Disposition": 'attachment; filename="facturas.xlsx"'
    }
    return StreamingResponse(excel_file, headers=headers_resp, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


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
        # payload.empresa_id = current_user.empresa_id # Prevenir cambio de empresa - REDUNDANTE y causa error 500


    return srv.actualizar_factura(db, id, payload)


@router.post("/{id}/duplicar", response_model=FacturaOut, status_code=status.HTTP_201_CREATED)
def duplicar_factura_endpoint(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = srv.obtener_factura(db, id)
    if not factura:
         raise HTTPException(status_code=404, detail="Factura no encontrada")
         
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
         raise HTTPException(status_code=404, detail="Factura no encontrada")

    return srv.duplicar_factura(db, id)


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
    folio: Optional[int] = Query(None),
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
        folio=folio,
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

    result = srv.eliminar_factura(db, id=id)
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.ELIMINAR_FACTURA, entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={"serie": factura.serie, "folio": factura.folio},
        )
        db.commit()
    except Exception:
        pass
    return result


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
@limiter.limit("10/minute")
def timbrar_endpoint(
    request: Request,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = srv.obtener_factura(db, id)
    if not factura: 
         raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    result = srv.timbrar_factura(db, id)
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.TIMBRAR_FACTURA, entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={"serie": factura.serie, "folio": factura.folio},
        )
        db.commit()
    except Exception:
        pass
    return result


@router.post("/{id}/cancelar")
def solicitar_cancelacion_endpoint(
    id: UUID, payload: CancelarIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = srv.obtener_factura(db, id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    result = srv.solicitar_cancelacion_cfdi(
        db, id, payload.motivo_cancelacion, payload.folio_fiscal_sustituto
    )
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.CANCELAR_FACTURA, entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={"motivo": payload.motivo_cancelacion, "serie": factura.serie, "folio": factura.folio},
        )
        db.commit()
    except Exception:
        pass
    return result


# --- Verificación SAT y reversión de cancelación ---


@router.post("/{id}/verificar-sat", summary="Consulta el estado del CFDI en el SAT y actualiza el estatus")
def verificar_estado_sat(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    from app.services import sat_cfdi_service as sat_svc
    from datetime import datetime

    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus not in ("EN_CANCELACION", "TIMBRADA", "CANCELADA"):
        raise HTTPException(status_code=400, detail="Solo se puede verificar facturas TIMBRADAS o EN_CANCELACION")
    if not factura.cfdi_uuid:
        raise HTTPException(status_code=400, detail="La factura no tiene UUID fiscal")

    rfc_emisor = getattr(getattr(factura, "empresa", None), "rfc", None) or ""
    rfc_receptor = getattr(getattr(factura, "cliente", None), "rfc", None) or ""
    total = float(factura.total or 0)

    try:
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_emisor.strip().upper(),
            rfc_receptor=rfc_receptor.strip().upper(),
            total=total,
            uuid=factura.cfdi_uuid,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Error al consultar SAT: {e}")

    estatus_anterior = factura.estatus
    nuevo_estatus = estatus_anterior  # por defecto no cambia

    if not acuse.encontrado:
        raise HTTPException(status_code=404, detail=f"CFDI no encontrado en SAT: {acuse.codigo_estatus}")

    if acuse.cancelado_por_sat:
        nuevo_estatus = "CANCELADA"
        factura.fecha_solicitud_cancelacion = None
    elif acuse.en_proceso:
        nuevo_estatus = "EN_CANCELACION"
        if not factura.fecha_solicitud_cancelacion:
            factura.fecha_solicitud_cancelacion = datetime.utcnow()
    else:
        # Vigente (receptor rechazó o nunca se inició cancelación)
        if estatus_anterior == "EN_CANCELACION":
            nuevo_estatus = "TIMBRADA"
            factura.fecha_solicitud_cancelacion = None

    factura.estatus = nuevo_estatus
    db.add(factura)
    db.commit()
    db.refresh(factura)

    return {
        "id": str(factura.id),
        "estatus_anterior": estatus_anterior,
        "estatus_nuevo": nuevo_estatus,
        "sat_codigo": acuse.codigo_estatus,
        "sat_estado": acuse.estado,
        "sat_es_cancelable": acuse.es_cancelable,
        "sat_estatus_cancelacion": acuse.estatus_cancelacion,
        "actualizado": estatus_anterior != nuevo_estatus,
    }


@router.post("/{id}/revertir-cancelacion", summary="Revierte EN_CANCELACION a TIMBRADA (receptor rechazó la cancelación)")
def revertir_cancelacion(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "EN_CANCELACION":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede revertir una factura EN_CANCELACION"
        )

    factura.estatus = "TIMBRADA"
    factura.motivo_cancelacion = None
    factura.folio_fiscal_sustituto = None
    factura.fecha_solicitud_cancelacion = None
    db.add(factura)
    db.commit()
    db.refresh(factura)

    try:
        audit_svc.registrar(
            db=db, accion="REVERTIR_CANCELACION", entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={"serie": factura.serie, "folio": factura.folio},
        )
        db.commit()
    except Exception:
        pass

    from app.schemas.factura import FacturaOut
    return FacturaOut.model_validate(factura)


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

def _send_emails_background(
    db: Session,
    empresa_id: UUID,
    factura_id: UUID,
    recipient_emails: list[str],
    send_function: callable,
    email_type: str,
):
    """Tarea de fondo: envía correos a cada destinatario y registra resultados en el log."""
    for email in recipient_emails:
        try:
            send_function(db=db, empresa_id=empresa_id, factura_id=factura_id, recipient_email=email)
            logger.info("Correo de %s para factura %s enviado a %s", email_type, factura_id, email)
        except EmailSendingError as e:
            logger.error("Error al enviar %s para factura %s a %s: %s", email_type, factura_id, email, e)
        except Exception as e:
            logger.error("Error inesperado al enviar %s para factura %s a %s: %s", email_type, factura_id, email, e)


def _handle_send_email(
    id: UUID,
    payload: FlexibleSendEmailIn,
    db: Session,
    background_tasks: BackgroundTasks,
    send_function: callable,
    email_type: str,
    current_user: Optional[Usuario] = None,
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

    # Validar configuración de email antes de encolar (feedback inmediato)
    email_config = db.query(EmailConfig).filter(EmailConfig.empresa_id == factura.empresa_id).first()
    if not email_config:
        raise HTTPException(
            status_code=400,
            detail="La empresa no tiene una configuración de correo electrónico.",
        )

    background_tasks.add_task(
        _send_emails_background,
        db, factura.empresa_id, id, recipient_emails, send_function, email_type,
    )
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.ENVIAR_FACTURA_EMAIL, entidad="factura",
            usuario_id=current_user.id if current_user else None,
            usuario_email=current_user.email if current_user else None,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={"tipo": email_type, "destinatarios": recipient_emails},
        )
        db.commit()
    except Exception:
        pass

    return {
        "message": f"Correo programado para envío a: {', '.join(recipient_emails)}"
    }


@router.post(
    "/{id}/send-preview-email",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar vista previa de factura por correo electrónico",
)
def send_preview_factura_by_email(
    id: UUID, payload: FlexibleSendEmailIn, background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Programa el envío de la vista previa de la factura (PDF) en segundo plano."""
    return _handle_send_email(
        id, payload, db, background_tasks, email_sender.send_preview_invoice_email, "Vista previa de factura", current_user
    )


@router.post(
    "/{id}/send-email",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar factura por correo electrónico",
)
def send_factura_by_email(
    id: UUID, payload: FlexibleSendEmailIn, background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Programa el envío de la factura (PDF y XML) en segundo plano."""
    return _handle_send_email(
        id, payload, db, background_tasks, email_sender.send_invoice_email, "Factura", current_user
    )
