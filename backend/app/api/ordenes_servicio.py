# app/api/ordenes_servicio.py
"""
Router Sprint 6 — Programación de Servicios
  /api/ordenes-servicio
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.orden_servicio import (
    CambioEstadoOS,
    OrdenServicioCreate,
    OrdenServicioListOut,
    OrdenServicioOut,
    OrdenServicioUpdate,
)
from app.services import orden_servicio_service as svc
from app.services import auditoria_service as audit_svc

router = APIRouter()


def _resolve_empresa_id(
    empresa_id: Optional[UUID],
    current_user: Usuario,
    db: Session,
) -> UUID:
    """Determina la empresa_id activa para el usuario."""
    if empresa_id:
        return empresa_id
    if current_user.empresa_id:
        return current_user.empresa_id
    raise HTTPException(status_code=400, detail="Se requiere empresa_id")


# ── Listar ────────────────────────────────────────────────────────────────────

@router.get("", response_model=dict)
def listar_ordenes(
    empresa_id: Optional[UUID] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    estado: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    tecnico_id: Optional[UUID] = Query(None),
    cliente_id: Optional[UUID] = Query(None),
    factura_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None),
    activo: Optional[bool] = Query(True),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    eid = _resolve_empresa_id(empresa_id, current_user, db)
    items, total = svc.list_ordenes(
        db,
        empresa_id=eid,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        prioridad=prioridad,
        tecnico_id=tecnico_id,
        cliente_id=cliente_id,
        factura_id=factura_id,
        q=q,
        activo=activo,
        limit=limit,
        offset=offset,
    )

    # Resumen de equipos de control por cliente (por tipo) — en lote
    from app.services.equipo_service import resumen_equipos_por_cliente
    cliente_ids = list({o.cliente_id for o in items if o.cliente_id})
    equipos_por_cliente = resumen_equipos_por_cliente(db, eid, cliente_ids) if cliente_ids else {}

    # Serializar a OrdenServicioListOut (versión reducida)
    result = []
    for o in items:
        result.append(
            OrdenServicioListOut(
                id=o.id,
                folio_os=o.folio_os,
                fecha_programada=o.fecha_programada,
                hora_inicio=o.hora_inicio,
                hora_fin=o.hora_fin,
                estado=o.estado,
                prioridad=o.prioridad,
                cliente_nombre=o.cliente.nombre_comercial if o.cliente else None,
                tecnico_nombre=o.tecnico.nombre_completo if o.tecnico else None,
                servicio_nombre=o.servicio.nombre if o.servicio else None,
                direccion_servicio=o.direccion_servicio,
                precio_acordado=o.precio_acordado,
                notas_tecnico=o.notas_tecnico,
                factura_id=o.factura_id,
                factura_folio=(f"{o.factura.serie}-{o.factura.folio}" if o.factura else None),
                factura_estatus=(o.factura.estatus if o.factura else None),
                cliente_id=o.cliente_id,
                equipos_resumen=equipos_por_cliente.get(o.cliente_id, []),
            )
        )

    return {"items": result, "total": total}


# ── Obtener uno ───────────────────────────────────────────────────────────────

@router.get("/{orden_id}", response_model=OrdenServicioOut)
def obtener_orden(
    orden_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.get_orden(db, orden_id)


# ── Crear ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=OrdenServicioOut, status_code=201)
def crear_orden(
    request: Request,
    empresa_id: Optional[UUID] = Query(None),
    data: OrdenServicioCreate = ...,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    eid = _resolve_empresa_id(empresa_id, current_user, db)
    obj = svc.create_orden(db, empresa_id=eid, data=data, usuario_id=current_user.id)
    audit_svc.registrar(
        db=db, accion=audit_svc.CREAR_ORDEN_SERVICIO, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=eid, entidad_id=str(obj.id),
        ip=audit_svc.get_ip(request),
        detalle={"folio_os": obj.folio_os, "fecha": str(obj.fecha_programada), "estado": obj.estado},
    )
    db.commit()
    db.refresh(obj)
    return obj


# ── Actualizar ────────────────────────────────────────────────────────────────

@router.put("/{orden_id}", response_model=OrdenServicioOut)
def actualizar_orden(
    orden_id: UUID,
    request: Request,
    data: OrdenServicioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.update_orden(db, orden_id=orden_id, data=data, usuario_id=current_user.id)
    audit_svc.registrar(
        db=db, accion=audit_svc.ACTUALIZAR_ORDEN_SERVICIO, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(orden_id),
        ip=audit_svc.get_ip(request),
        detalle={"folio_os": obj.folio_os, **data.model_dump(exclude_unset=True)},
    )
    db.commit()
    db.refresh(obj)
    return obj


# ── Cambio de estado ──────────────────────────────────────────────────────────

@router.patch("/{orden_id}/estado", response_model=OrdenServicioOut)
def cambiar_estado(
    orden_id: UUID,
    request: Request,
    payload: CambioEstadoOS,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.cambiar_estado(db, orden_id=orden_id, payload=payload, usuario_id=current_user.id)
    audit_svc.registrar(
        db=db, accion=audit_svc.CAMBIAR_ESTADO_ORDEN_SERVICIO, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(orden_id),
        ip=audit_svc.get_ip(request),
        detalle={"folio_os": obj.folio_os, "nuevo_estado": payload.estado, "notas": payload.notas},
    )
    db.commit()
    db.refresh(obj)
    return obj


# ── Eliminar (soft) ───────────────────────────────────────────────────────────

@router.delete("/{orden_id}", status_code=204)
def eliminar_orden(
    orden_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_orden(db, orden_id)
    audit_svc.registrar(
        db=db, accion=audit_svc.ELIMINAR_ORDEN_SERVICIO, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(orden_id),
        ip=audit_svc.get_ip(request),
        detalle={"folio_os": obj.folio_os, "estado": obj.estado},
    )
    svc.delete_orden(db, orden_id)


# ── Vínculo con factura ───────────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel
from app.schemas.orden_servicio import OrdenServicioOut


class VincularFacturaIn(_BaseModel):
    factura_id: UUID


@router.post("/{orden_id}/crear-factura", response_model=dict, status_code=201)
def crear_factura_desde_orden(
    orden_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Crea una factura BORRADOR ligada a la orden y devuelve su id para abrirla."""
    factura = svc.crear_factura_desde_orden(db, orden_id)
    audit_svc.registrar(
        db=db, accion="CREAR_FACTURA_DESDE_ORDEN", entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        entidad_id=str(orden_id), ip=audit_svc.get_ip(request),
        detalle={"factura_id": str(factura.id), "serie": factura.serie, "folio": factura.folio},
    )
    db.commit()
    return {"factura_id": str(factura.id), "serie": factura.serie, "folio": factura.folio}


@router.get("/{orden_id}/facturas-vinculables", response_model=list)
def facturas_vinculables(
    orden_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Facturas candidatas para vincular (mismo cliente o mismo RFC)."""
    return svc.facturas_vinculables(db, orden_id)


@router.post("/{orden_id}/vincular-factura", response_model=OrdenServicioOut)
def vincular_factura(
    orden_id: UUID,
    payload: VincularFacturaIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.vincular_factura(db, orden_id, payload.factura_id)


@router.delete("/{orden_id}/factura", response_model=OrdenServicioOut)
def desvincular_factura(
    orden_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.desvincular_factura(db, orden_id)
