# app/api/factura.py
from __future__ import annotations
import logging
import os
from uuid import UUID
from typing import List, Optional, Literal
from datetime import date

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query,
    Request, Response, UploadFile, status,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.utils.excel import generate_excel

from app.config import settings
from app.database import get_db
from app.models.factura import Factura
from app.models.usuario import Usuario, RolUsuario
from app.api import deps
from app.schemas.factura import (
    FacturaCreate, FacturaUpdate, FacturaOut, FacturaRelacionableOut,
)

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
    estatus: Optional[Literal["BORRADOR", "TIMBRADA", "EN_CANCELACION", "CANCELADA"]] = Query(None),
    status_pago: Optional[Literal["PAGADA", "NO_PAGADA"]] = Query(None),
    cancelacion: Optional[
        Literal["con_solicitud", "atorada", "en_tramite", "sin_registro_sat", "cancelada"]
    ] = Query(
        None,
        description=(
            "Filtra por el estado del TRÁMITE de cancelación, que no es el "
            "estatus del documento: 'atorada' son las que se pidió cancelar y "
            "siguen vigentes, 'sin_registro_sat' las que el PAC acusó y el SAT "
            "nunca registró."
        ),
    ),
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
        cancelacion=cancelacion,
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
) -> Factura:
    from app.services import historial_documento_service as hist

    factura = srv.obtener_factura(db, id) # Verificamos existencia y propiedad antes
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    if current_user.rol == RolUsuario.SUPERVISOR:
        if factura.empresa_id != current_user.empresa_id:
            raise HTTPException(status_code=404, detail="Factura no encontrada") # Ocultamos que existe
        # payload.empresa_id = current_user.empresa_id # Prevenir cambio de empresa - REDUNDANTE y causa error 500

    # Foto antes de tocar nada. Las modificaciones no se auditaban —un registro
    # en toda la historia contra 478 creaciones—, así que abrir una factura y
    # cambiarle el receptor o los importes no dejaba rastro de qué había antes.
    antes = hist.snapshot(factura)

    actualizada = srv.actualizar_factura(db, id, payload)

    cambios = hist.diff(antes, hist.snapshot(actualizada))
    if cambios:
        audit_svc.registrar(
            db=db,
            accion=audit_svc.ACTUALIZAR_FACTURA,
            entidad="factura",
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            empresa_id=actualizada.empresa_id,
            entidad_id=str(id),
            detalle={
                "serie": actualizada.serie,
                "folio": actualizada.folio,
                "estatus": getattr(actualizada.estatus, "value", actualizada.estatus),
                "cambios": cambios,
            },
            ip=audit_svc.get_ip(request),
        )
        db.commit()

    return actualizada


@router.post("/{id}/duplicar", response_model=FacturaOut, status_code=status.HTTP_201_CREATED)
def duplicar_factura_endpoint(
    id: UUID,
    sustituta: bool = Query(
        False,
        description="Crea la copia ya relacionada al CFDI original con tipo 04 (sustitución)",
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = srv.obtener_factura(db, id)
    if not factura:
         raise HTTPException(status_code=404, detail="Factura no encontrada")

    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
         raise HTTPException(status_code=404, detail="Factura no encontrada")

    return srv.duplicar_factura(db, id, como_sustituta=sustituta)


@router.get(
    "/relacionables",
    response_model=List[FacturaRelacionableOut],
    summary="Facturas timbradas del cliente para elegir como CFDI relacionado",
)
def listar_relacionables(
    cliente_id: UUID = Query(..., description="Cliente al que se le factura"),
    empresa_id: Optional[UUID] = Query(None),
    solo_vigentes: bool = Query(
        True, description="Solo TIMBRADAS (para sustitución tipo 04)"
    ),
    excluir_id: Optional[UUID] = Query(None, description="No incluir esta factura"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Alimenta el selector de CFDI relacionados para que el usuario elija la
    factura en vez de teclear el UUID (que es donde se cuelan los errores).
    """
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    q = db.query(Factura).filter(
        Factura.cliente_id == cliente_id,
        Factura.cfdi_uuid.isnot(None),
    )
    if empresa_id:
        q = q.filter(Factura.empresa_id == empresa_id)
    if solo_vigentes:
        q = q.filter(Factura.estatus == "TIMBRADA")
    else:
        q = q.filter(Factura.estatus.in_(["TIMBRADA", "EN_CANCELACION", "CANCELADA"]))
    if excluir_id:
        q = q.filter(Factura.id != excluir_id)

    return q.order_by(Factura.fecha_emision.desc()).limit(limit).all()


@router.get(
    "/{id}/puede-cancelarse",
    summary="Verifica en el SAT si el CFDI se puede cancelar y explica por qué no",
)
def puede_cancelarse(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return srv.diagnostico_cancelacion(db, factura)


@router.get(
    "/{id}/historial",
    summary="Todo lo que le pasó a esta factura: acciones y trámite fiscal",
)
def historial_factura(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Una sola línea de tiempo con los dos rastros que hasta ahora había que
    cruzar a mano en la base: lo que hizo la gente (auditoria_log) y lo que
    contestaron el PAC y el SAT en cada solicitud (cancelacion_intentos).

    Sustituye al antiguo /cancelacion-intentos, que sólo mostraba la mitad.
    """
    from app.services import historial_documento_service as hist

    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    return {
        # La misma forma que el historial de pagos: un solo componente los lee.
        "documento": {
            "id": str(factura.id),
            "serie": factura.serie,
            "folio": factura.folio,
            "estatus": getattr(factura.estatus, "value", factura.estatus),
            "cfdi_uuid": factura.cfdi_uuid,
        },
        "eventos": hist.linea_de_tiempo(db, factura),
    }


@router.get(
    "/{id}/sustitutas",
    response_model=List[FacturaRelacionableOut],
    summary="Facturas que declaran sustituir a ésta (relación tipo 04)",
)
def listar_sustitutas(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Busca las facturas que ya declaran la relación 04 hacia este CFDI, para
    prellenar el folio sustituto al cancelar con motivo 01.
    """
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if not factura.cfdi_uuid:
        return []

    return (
        db.query(Factura)
        .filter(
            Factura.empresa_id == factura.empresa_id,
            Factura.cfdi_relacionados_tipo == "04",
            func.upper(Factura.cfdi_relacionados).contains(factura.cfdi_uuid.upper()),
            Factura.cfdi_uuid.isnot(None),
            Factura.id != factura.id,
        )
        .order_by(Factura.fecha_emision.desc())
        .all()
    )


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
    estatus: Optional[Literal["BORRADOR", "TIMBRADA", "EN_CANCELACION", "CANCELADA"]] = Query(None),
    status_pago: Optional[Literal["PAGADA", "NO_PAGADA"]] = Query(None),
    cancelacion: Optional[
        Literal["con_solicitud", "atorada", "en_tramite", "sin_registro_sat", "cancelada"]
    ] = Query(
        None,
        description=(
            "Filtra por el estado del TRÁMITE de cancelación, que no es el "
            "estatus del documento: 'atorada' son las que se pidió cancelar y "
            "siguen vigentes, 'sin_registro_sat' las que el PAC acusó y el SAT "
            "nunca registró."
        ),
    ),
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
        cancelacion=cancelacion,
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
    current_user: Usuario = Depends(deps.get_current_active_user),
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


@router.post(
    "/{id}/registrar-cancelacion-portal",
    summary="Registra una cancelación tramitada en el portal del SAT",
)
def registrar_cancelacion_portal_endpoint(
    id: UUID,
    request: Request,
    motivo: Optional[str] = Form(default=None),
    folio_sustitucion: Optional[str] = Form(default=None),
    acuse: Optional[UploadFile] = File(
        default=None, description="Acuse XML sellado que entrega el portal del SAT"
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Fallback cuando el PAC acusa recibo sin transmitir la solicitud: el trámite
    se hace en el portal del SAT y aquí se deja constancia.

    El estatus no se toma de lo que diga el usuario sino de lo que el SAT
    reporte en este momento.
    """
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    contenido = acuse.file.read() if acuse is not None else None
    if contenido and b"<Acuse" not in contenido:
        raise HTTPException(
            status_code=400,
            detail="El archivo no parece el acuse XML del SAT (no contiene <Acuse>).",
        )

    resultado = srv.registrar_cancelacion_portal(
        db, factura,
        motivo=motivo, folio_sustitucion=folio_sustitucion, acuse_xml=contenido,
    )

    try:
        audit_svc.registrar(
            db=db, accion="REGISTRAR_CANCELACION_PORTAL", entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={"serie": factura.serie, "folio": factura.folio, **resultado},
            ip=audit_svc.get_ip(request),
        )
        db.commit()
    except Exception:
        pass

    return resultado


@router.get("/{id}/acuse-cancelacion", summary="Descarga el acuse de cancelación del SAT (PDF o XML)")
def descargar_acuse_cancelacion(
    id: UUID,
    fmt: str = Query("pdf", pattern="^(pdf|xml)$"),
    forzar: bool = Query(False, description="Re-descargar del PAC ignorando la caché"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    from app.services import acuse_cancelacion_service as acuse_svc

    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    if factura.estatus not in ("EN_CANCELACION", "CANCELADA"):
        raise HTTPException(
            status_code=400,
            detail="El acuse solo está disponible para facturas en cancelación o canceladas.",
        )

    try:
        contenido, media_type, filename = acuse_svc.obtener_acuse(factura, fmt, forzar=forzar)
    except acuse_svc.AcuseError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return Response(
        content=contenido,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Verificación SAT y reversión de cancelación ---


@router.post("/{id}/verificar-sat", summary="Consulta el estado del CFDI en el SAT y actualiza el estatus")
def verificar_estado_sat(
    id: UUID,
    request: Request,
    confirmar_retroceso: bool = Query(
        False,
        description=(
            "Aplica también los cambios que revierten el trámite (revivir una "
            "factura). Sin esto, esos casos se devuelven como propuesta."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Compara con el SAT y sincroniza, pero no todos los cambios pesan igual.

    Lo que el SAT ya consumó se aplica sin preguntar: la factura ya está así
    ante Hacienda y no reflejarlo sólo consigue que siga contando en cobranza
    algo que fiscalmente no existe. Lo que REVIVE una factura se devuelve como
    propuesta, porque tiene consecuencias que el sistema no puede evaluar solo:
    el cliente vuelve a deberla y puede haber una sustituta ya timbrada.
    """
    from app.services import sat_cfdi_service as sat_svc
    from app.services import auditoria_service as aud
    from app.services import cancelacion_intento_service as bitacora_svc

    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus not in ("EN_CANCELACION", "TIMBRADA", "CANCELADA"):
        raise HTTPException(
            status_code=400,
            detail="Solo se puede verificar una factura TIMBRADA, EN CANCELACIÓN o CANCELADA",
        )
    if not factura.cfdi_uuid:
        raise HTTPException(status_code=400, detail="La factura no tiene UUID fiscal")

    # Datos del XML timbrado (inmutables) con fallback a la BD
    rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(factura)

    try:
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_emisor,
            rfc_receptor=rfc_receptor,
            total=total,
            uuid=factura.cfdi_uuid,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Error al consultar SAT: {e}")

    if not acuse.encontrado:
        raise HTTPException(status_code=404, detail=f"CFDI no encontrado en SAT: {acuse.codigo_estatus}")

    estatus_anterior = factura.estatus
    nuevo_estatus, _ = sat_svc.aplicar_acuse_sat(factura, acuse)
    clasificacion = sat_svc.clasificar_cambio(estatus_anterior, nuevo_estatus)

    datos_sat = {
        "sat_codigo": acuse.codigo_estatus,
        "sat_estado": acuse.estado,
        "sat_es_cancelable": acuse.es_cancelable,
        "sat_estatus_cancelacion": acuse.estatus_cancelacion,
    }

    if clasificacion == sat_svc.RETROCESO and not confirmar_retroceso:
        # Se descartan los cambios que aplicar_acuse_sat dejó en el objeto. Es
        # más limpio que duplicar su lógica para simular el resultado sin tocar
        # la factura, y `expire` en vez de `rollback` porque sólo hay que
        # olvidar este objeto: nunca se llegó a escribir nada, y tumbar la
        # transacción entera se llevaría también la auditoría de aquí abajo.
        db.expire(factura)
        aud.registrar(
            db,
            accion=aud.VERIFICAR_SAT,
            entidad="factura",
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            empresa_id=factura.empresa_id,
            entidad_id=str(factura.id),
            detalle={
                "cfdi_uuid": factura.cfdi_uuid,
                "estatus_anterior": estatus_anterior,
                "estatus_propuesto": nuevo_estatus,
                "clasificacion": clasificacion,
                "actualizado": False,
                **datos_sat,
            },
            ip=aud.get_ip(request),
        )
        db.commit()
        return {
            "id": str(factura.id),
            "estatus_anterior": estatus_anterior,
            "estatus_nuevo": estatus_anterior,  # no se movió
            "estatus_propuesto": nuevo_estatus,
            "clasificacion": clasificacion,
            "requiere_confirmacion": True,
            "advertencia": sat_svc.explicar_retroceso(
                estatus_anterior, nuevo_estatus, acuse
            ),
            "actualizado": False,
            **datos_sat,
        }

    db.add(factura)
    bitacora_svc.cerrar_si_resuelto(db, factura, estatus_anterior, nuevo_estatus)

    aud.registrar(
        db,
        accion=aud.VERIFICAR_SAT,
        entidad="factura",
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        empresa_id=factura.empresa_id,
        entidad_id=str(factura.id),
        detalle={
            "cfdi_uuid": factura.cfdi_uuid,
            "estatus_anterior": estatus_anterior,
            "estatus_nuevo": nuevo_estatus,
            "clasificacion": clasificacion,
            "confirmado_por_usuario": bool(
                confirmar_retroceso and clasificacion == sat_svc.RETROCESO
            ),
            "actualizado": estatus_anterior != nuevo_estatus,
            **datos_sat,
        },
        ip=aud.get_ip(request),
    )

    db.commit()
    db.refresh(factura)

    return {
        "id": str(factura.id),
        "estatus_anterior": estatus_anterior,
        "estatus_nuevo": nuevo_estatus,
        "clasificacion": clasificacion,
        "requiere_confirmacion": False,
        "actualizado": estatus_anterior != nuevo_estatus,
        **datos_sat,
    }


@router.post("/{id}/revertir-cancelacion", summary="Revierte EN_CANCELACION a TIMBRADA (receptor rechazó la cancelación)")
def revertir_cancelacion(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    from app.services import sat_cfdi_service as sat_svc

    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if current_user.rol == RolUsuario.SUPERVISOR and factura.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "EN_CANCELACION":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede revertir una factura EN_CANCELACION"
        )

    # Antes se revertía a ciegas: si el CFDI sí estaba cancelado en el SAT, esto
    # recreaba el desfase entre el sistema y el SAT. Ahora se consulta primero.
    estado_sat = None
    try:
        rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(factura)
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_emisor, rfc_receptor=rfc_receptor,
            total=total, uuid=factura.cfdi_uuid,
        )
        if acuse.encontrado:
            estado_sat = acuse.estado
            if acuse.cancelado_por_sat:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No se puede revertir: el SAT ya tiene esta factura como "
                        "CANCELADA. Usa «Verificar con SAT» para dejar el estatus "
                        "igual al del SAT."
                    ),
                )
            if acuse.en_proceso:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No se puede revertir: el SAT reporta la cancelación en "
                        "proceso, esperando la respuesta del receptor. Si él la "
                        "rechaza, la factura vuelve a TIMBRADA automáticamente."
                    ),
                )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — si el SAT no responde, se permite revertir
        logger.info("No se pudo consultar el SAT antes de revertir: %s", exc)

    factura.estatus = "TIMBRADA"
    factura.fecha_solicitud_cancelacion = None
    # Se conservan motivo_cancelacion y folio_fiscal_sustituto: son la
    # trazabilidad del intento y alimentan el aviso de "cancelación no aplicada".
    db.add(factura)
    from app.services import cancelacion_intento_service as bitacora_svc

    bitacora_svc.cerrar_si_resuelto(db, factura, "EN_CANCELACION", "TIMBRADA")
    db.commit()
    db.refresh(factura)

    try:
        audit_svc.registrar(
            db=db, accion="REVERTIR_CANCELACION", entidad="factura",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=factura.empresa_id, entidad_id=str(id),
            detalle={
                "serie": factura.serie, "folio": factura.folio,
                "estado_sat": estado_sat,
            },
        )
        db.commit()
    except Exception:
        pass

    from app.schemas.factura import FacturaOut
    return FacturaOut.model_validate(factura)


# --- Endpoints de Archivos ---


@router.post("/{id}/xml-preview", summary="Genera XML CFDI 4.0 sin timbrar")
def generar_xml_preview(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    xml_bytes = srv.generar_xml_preview_bytes(db, id)
    return Response(content=xml_bytes, media_type="application/xml")


@router.get("/{id}/preview-pdf", summary="PDF de vista previa (marca BORRADOR)")
def preview_pdf(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    pdf_bytes = srv.generar_pdf_bytes(db, id, preview=True)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="preview-{id}.pdf"'},
    )


@router.get("/{id}/pdf", summary="PDF final (TIMBRADA o CANCELADA)")
def factura_pdf(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    pdf_bytes = srv.generar_pdf_bytes(db, id, preview=False)
    # El nombre del archivo se podría obtener del servicio también si se quisiera.
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="factura-{id}.pdf"'},
    )


@router.get("/{id}/xml", summary="Descargar XML timbrado")
def descargar_xml_timbrado(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
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
