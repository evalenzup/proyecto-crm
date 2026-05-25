# app/services/orden_servicio_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from datetime import date

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.orden_servicio import OrdenServicio, HistorialEstadoOS
from app.schemas.orden_servicio import (
    OrdenServicioCreate,
    OrdenServicioUpdate,
    CambioEstadoOS,
)


# ── Folio ────────────────────────────────────────────────────────────────────

def _generar_folio(db: Session, empresa_id: UUID) -> str:
    """Genera folio correlativo por empresa: OS-0001, OS-0002, ..."""
    count = (
        db.query(OrdenServicio)
        .filter(OrdenServicio.empresa_id == empresa_id)
        .count()
    )
    return f"OS-{count + 1:04d}"


# ── CRUD ─────────────────────────────────────────────────────────────────────

def list_ordenes(
    db: Session,
    empresa_id: UUID,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    tecnico_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = True,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[OrdenServicio], int]:
    query = db.query(OrdenServicio).filter(OrdenServicio.empresa_id == empresa_id)

    if activo is not None:
        query = query.filter(OrdenServicio.activo == activo)
    if fecha_desde:
        query = query.filter(OrdenServicio.fecha_programada >= fecha_desde)
    if fecha_hasta:
        query = query.filter(OrdenServicio.fecha_programada <= fecha_hasta)
    if estado:
        query = query.filter(OrdenServicio.estado == estado)
    if prioridad:
        query = query.filter(OrdenServicio.prioridad == prioridad)
    if tecnico_id:
        query = query.filter(OrdenServicio.tecnico_id == tecnico_id)
    if cliente_id:
        query = query.filter(OrdenServicio.cliente_id == cliente_id)
    if q:
        query = query.filter(OrdenServicio.folio_os.ilike(f"%{q}%"))

    total = query.count()
    items = (
        query.order_by(OrdenServicio.fecha_programada, OrdenServicio.hora_inicio)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_orden(db: Session, orden_id: UUID) -> OrdenServicio:
    obj = db.query(OrdenServicio).filter(OrdenServicio.id == orden_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")
    return obj


def create_orden(
    db: Session,
    empresa_id: UUID,
    data: OrdenServicioCreate,
    usuario_id: Optional[UUID] = None,
) -> OrdenServicio:
    # Verificar conflicto de técnico (mismo día, misma hora)
    if data.tecnico_id and data.hora_inicio and data.hora_fin:
        _verificar_conflicto_tecnico(
            db, data.tecnico_id, data.fecha_programada,
            data.hora_inicio, data.hora_fin, exclude_id=None
        )

    folio = _generar_folio(db, empresa_id)
    obj = OrdenServicio(
        id=uuid4(),
        empresa_id=empresa_id,
        folio_os=folio,
        **data.model_dump(),
    )
    db.add(obj)
    db.flush()  # obtener id sin commit

    # Registrar en historial
    _registrar_historial(db, obj.id, None, obj.estado, usuario_id, notas="Orden creada")

    db.commit()
    db.refresh(obj)
    return obj


def update_orden(
    db: Session,
    orden_id: UUID,
    data: OrdenServicioUpdate,
    usuario_id: Optional[UUID] = None,
) -> OrdenServicio:
    obj = get_orden(db, orden_id)
    update_data = data.model_dump(exclude_unset=True)

    estado_anterior = obj.estado

    # Verificar conflicto si cambia técnico o fechas/horas
    tecnico_id = update_data.get("tecnico_id", obj.tecnico_id)
    fecha = update_data.get("fecha_programada", obj.fecha_programada)
    hora_inicio = update_data.get("hora_inicio", obj.hora_inicio)
    hora_fin = update_data.get("hora_fin", obj.hora_fin)

    if tecnico_id and hora_inicio and hora_fin:
        _verificar_conflicto_tecnico(db, tecnico_id, fecha, hora_inicio, hora_fin, exclude_id=orden_id)

    for field, value in update_data.items():
        setattr(obj, field, value)

    # Si el estado cambió, registrar en historial
    if "estado" in update_data and update_data["estado"] != estado_anterior:
        _registrar_historial(db, obj.id, estado_anterior, obj.estado, usuario_id)

    db.commit()
    db.refresh(obj)
    return obj


def cambiar_estado(
    db: Session,
    orden_id: UUID,
    payload: CambioEstadoOS,
    usuario_id: Optional[UUID] = None,
) -> OrdenServicio:
    obj = get_orden(db, orden_id)
    estado_anterior = obj.estado

    if estado_anterior == payload.estado:
        return obj  # sin cambio

    obj.estado = payload.estado
    _registrar_historial(db, obj.id, estado_anterior, payload.estado, usuario_id, notas=payload.notas)

    db.commit()
    db.refresh(obj)
    return obj


def delete_orden(db: Session, orden_id: UUID) -> None:
    """Soft delete."""
    obj = get_orden(db, orden_id)
    obj.activo = False
    db.commit()


# ── Helpers internos ──────────────────────────────────────────────────────────

def _registrar_historial(
    db: Session,
    orden_id: UUID,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    usuario_id: Optional[UUID],
    notas: Optional[str] = None,
) -> None:
    entrada = HistorialEstadoOS(
        id=uuid4(),
        orden_id=orden_id,
        usuario_id=usuario_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        notas=notas,
    )
    db.add(entrada)


def _verificar_conflicto_tecnico(
    db: Session,
    tecnico_id: UUID,
    fecha: date,
    hora_inicio,
    hora_fin,
    exclude_id: Optional[UUID],
) -> None:
    """
    Detecta si el técnico ya tiene una OS en el mismo día que se solape con el
    rango hora_inicio–hora_fin propuesto.
    Lanza HTTPException 409 si hay conflicto.
    """
    query = db.query(OrdenServicio).filter(
        OrdenServicio.tecnico_id == tecnico_id,
        OrdenServicio.fecha_programada == fecha,
        OrdenServicio.activo == True,
        OrdenServicio.estado.notin_(["CANCELADO", "COMPLETADO"]),
        OrdenServicio.hora_inicio.isnot(None),
        OrdenServicio.hora_fin.isnot(None),
        # Solapamiento: A.inicio < B.fin AND A.fin > B.inicio
        OrdenServicio.hora_inicio < hora_fin,
        OrdenServicio.hora_fin > hora_inicio,
    )
    if exclude_id:
        query = query.filter(OrdenServicio.id != exclude_id)

    conflicto = query.first()
    if conflicto:
        raise HTTPException(
            status_code=409,
            detail=f"El técnico ya tiene la orden {conflicto.folio_os} programada en ese horario.",
        )
