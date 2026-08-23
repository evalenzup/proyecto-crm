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
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.schemas.orden_servicio import (
    CambioEstadoOS,
    IncidenciaOS,
    OrdenServicioCreate,
    OrdenServicioListOut,
    OrdenServicioOut,
    OrdenServicioUpdate,
)
from app.services import orden_servicio_service as svc
from app.services import auditoria_service as audit_svc
from app.utils.excel import generate_excel
from app.core import operativo as op_rules
from app.services import notificacion_service as notif_svc

import logging

logger = logging.getLogger("app")

router = APIRouter()


# Roles atados a una sola empresa: el parámetro empresa_id de la petición no
# los puede sacar de ella.
_UNA_SOLA_EMPRESA = {RolUsuario.SUPERVISOR, RolUsuario.ESTANDAR, RolUsuario.OPERATIVO}


def _resolve_empresa_id(
    empresa_id: Optional[UUID],
    current_user: Usuario,
    db: Session,
) -> UUID:
    """Determina la empresa_id activa para el usuario.

    Para los roles de una sola empresa se ignora lo que venga en la petición y
    se usa la suya. Antes se tomaba tal cual, así que bastaba con mandar el
    empresa_id de otra para consultar sus órdenes.
    """
    if current_user.rol in _UNA_SOLA_EMPRESA:
        if not current_user.empresa_id:
            raise HTTPException(
                status_code=400,
                detail="Tu cuenta no tiene una empresa asignada.",
            )
        return current_user.empresa_id
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
    order_by: Optional[str] = Query(None),
    order_dir: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    eid = _resolve_empresa_id(empresa_id, current_user, db)

    # El técnico ve toda la agenda de su empresa —le sirve para saber cómo va el
    # equipo y cubrir a un compañero—, pero sólo puede mover el estado de las
    # órdenes que tiene asignadas. Ese candado va en cambiar_estado y en
    # reportar_incidencia; aquí basta con que la empresa esté fijada.
    if current_user.rol == RolUsuario.OPERATIVO and current_user.tecnico_id is None:
        raise HTTPException(
            status_code=400,
            detail="Tu cuenta todavía no está ligada a una ficha de técnico. "
                   "Pídele a la oficina que la asocie.",
        )

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
        order_by=order_by,
        order_dir=order_dir,
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
                tecnico_id=o.tecnico_id,
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


# ── Incidencia del técnico ────────────────────────────────────────────────────

@router.post("/{orden_id}/incidencia", response_model=OrdenServicioOut)
def reportar_incidencia(
    orden_id: UUID,
    request: Request,
    payload: IncidenciaOS,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """El técnico avisa que el servicio no se pudo realizar.

    No cambia el estado a propósito: cancelar o reagendar arrastra consecuencias
    de facturación y cobranza que el técnico no ve. Queda constancia en el
    historial de la orden y le llega un aviso a la oficina, que decide.
    """
    obj = svc.get_orden(db, orden_id)

    if current_user.rol == RolUsuario.OPERATIVO and obj.tecnico_id != current_user.tecnico_id:
        raise HTTPException(status_code=403, detail="Esa orden no está asignada a ti.")

    quien = (current_user.nombre_completo or current_user.email)
    svc.registrar_incidencia(
        db, orden=obj, motivo=payload.motivo, usuario_id=current_user.id,
    )
    try:
        notif_svc.crear_notificacion(
            db,
            empresa_id=obj.empresa_id,
            tipo="ORDEN_SERVICIO",
            titulo=f"{obj.folio_os}: el servicio no se pudo realizar",
            mensaje=f"{quien} reportó: {payload.motivo}",
            metadata={"orden_id": str(obj.id), "folio_os": obj.folio_os},
        )
    except Exception:  # noqa: BLE001 — el aviso no debe tumbar el reporte
        logger.warning("No se pudo crear la notificación de incidencia de %s", obj.folio_os)

    audit_svc.registrar(
        db=db, accion=audit_svc.CAMBIAR_ESTADO_ORDEN_SERVICIO, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(orden_id),
        ip=audit_svc.get_ip(request),
        detalle={"folio_os": obj.folio_os, "incidencia": payload.motivo},
    )
    db.commit()
    db.refresh(obj)
    return obj


# ── Exportar ──────────────────────────────────────────────────────────────────
# Va antes de /{orden_id}: si se declarara después, esa ruta capturaría
# "export-excel" como si fuera un id.

@router.get("/export-excel")
def exportar_ordenes_excel(
    empresa_id: Optional[UUID] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    estado: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    tecnico_id: Optional[UUID] = Query(None),
    cliente_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None),
    activo: Optional[bool] = Query(True),
    order_by: Optional[str] = Query(None),
    order_dir: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Exporta a Excel las órdenes que cumplan los mismos filtros de la lista."""
    eid = _resolve_empresa_id(empresa_id, current_user, db)
    items, _ = svc.list_ordenes(
        db,
        empresa_id=eid,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        prioridad=prioridad,
        tecnico_id=tecnico_id,
        cliente_id=cliente_id,
        factura_id=None,
        q=q,
        activo=activo,
        limit=1000000,
        offset=0,
        order_by=order_by,
        order_dir=order_dir,
    )

    data_list = []
    for o in items:
        data_list.append({
            "folio_os": o.folio_os,
            "fecha_programada": o.fecha_programada,
            "horario": " a ".join(h.strftime("%H:%M") for h in (o.hora_inicio, o.hora_fin) if h),
            "cliente": o.cliente.nombre_comercial if o.cliente else None,
            "servicio": o.servicio.nombre if o.servicio else None,
            "tecnico": o.tecnico.nombre_completo if o.tecnico else None,
            "estado": getattr(o.estado, "value", o.estado),
            "prioridad": getattr(o.prioridad, "value", o.prioridad),
            "direccion_servicio": o.direccion_servicio,
            "precio_acordado": o.precio_acordado,
            "factura": f"{o.factura.serie}-{o.factura.folio}" if o.factura else None,
            "notas_tecnico": o.notas_tecnico,
        })

    headers = {
        "folio_os": "Folio",
        "fecha_programada": "Fecha",
        "horario": "Horario",
        "cliente": "Cliente",
        "servicio": "Servicio",
        "tecnico": "Técnico",
        "estado": "Estado",
        "prioridad": "Prioridad",
        "direccion_servicio": "Dirección",
        "precio_acordado": "Precio",
        "factura": "Factura",
        "notas_tecnico": "Notas",
    }

    excel_file = generate_excel(data_list, headers, sheet_name="Órdenes de servicio")
    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.EXPORTAR_EXCEL, entidad="orden_servicio",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=eid, detalle={"registros": len(data_list)},
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        excel_file,
        headers={"Content-Disposition": 'attachment; filename="ordenes-servicio.xlsx"'},
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Obtener uno ───────────────────────────────────────────────────────────────

@router.get("/{orden_id}", response_model=OrdenServicioOut)
def obtener_orden(
    orden_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    orden = svc.get_orden(db, orden_id)
    # El detalle no filtraba nada: con el id se podía leer una orden de otra
    # empresa. Los roles de una sola empresa quedan acotados a la suya; se
    # devuelve 404 y no 403 para no confirmar que ese id existe.
    if (current_user.rol in _UNA_SOLA_EMPRESA
            and orden.empresa_id != current_user.empresa_id):
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden


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
    # Reglas del técnico: sólo sus órdenes, sólo hacia adelante y sin cancelar.
    if current_user.rol == RolUsuario.OPERATIVO:
        actual = svc.get_orden(db, orden_id)
        if actual.tecnico_id != current_user.tecnico_id:
            raise HTTPException(
                status_code=403,
                detail="Esa orden no está asignada a ti.",
            )
        if not op_rules.transicion_permitida(actual.estado, payload.estado):
            raise HTTPException(
                status_code=409,
                detail=op_rules.explicar_transicion(actual.estado, payload.estado),
            )

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
