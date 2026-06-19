# app/services/equipo_service.py
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.equipo import (
    EquipoControl,
    EstadoEquipo,
    TipoEquipo,
    TipoEquipoCampo,
)
from app.schemas.equipo import (
    EquipoControlBulkCreate,
    EquipoControlCreate,
    EquipoControlUpdate,
    EstadoEquipoCreate,
    EstadoEquipoUpdate,
    TipoEquipoCampoCreate,
    TipoEquipoCreate,
    TipoEquipoUpdate,
)


# ===========================================================================
# Tipos de equipo (+ campos)
# ===========================================================================
def list_tipos_equipo(
    db: Session,
    empresa_id: UUID,
    activo: Optional[bool] = None,
) -> List[TipoEquipo]:
    query = db.query(TipoEquipo).filter(TipoEquipo.empresa_id == empresa_id)
    if activo is not None:
        query = query.filter(TipoEquipo.activo == activo)
    return query.order_by(TipoEquipo.orden, TipoEquipo.nombre).all()


def get_tipo_equipo(db: Session, tipo_id: UUID) -> TipoEquipo:
    obj = db.query(TipoEquipo).filter(TipoEquipo.id == tipo_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tipo de equipo no encontrado.")
    return obj


def _build_campo(data: TipoEquipoCampoCreate) -> TipoEquipoCampo:
    return TipoEquipoCampo(**data.model_dump())


def create_tipo_equipo(db: Session, data: TipoEquipoCreate) -> TipoEquipo:
    obj_data = data.model_dump(exclude={"campos"})
    obj = TipoEquipo(**obj_data)
    obj.campos = [_build_campo(c) for c in (data.campos or [])]
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_tipo_equipo(db: Session, tipo_id: UUID, data: TipoEquipoUpdate) -> TipoEquipo:
    obj = get_tipo_equipo(db, tipo_id)
    update_data = data.model_dump(exclude_unset=True)
    campos = update_data.pop("campos", None)
    for field, value in update_data.items():
        setattr(obj, field, value)
    # Si se envían campos, reemplazan el set completo (delete-orphan se encarga)
    if campos is not None:
        obj.campos = [_build_campo(TipoEquipoCampoCreate(**c)) for c in campos]
    db.commit()
    db.refresh(obj)
    return obj


def delete_tipo_equipo(db: Session, tipo_id: UUID) -> None:
    obj = get_tipo_equipo(db, tipo_id)
    en_uso = (
        db.query(EquipoControl).filter(EquipoControl.tipo_equipo_id == tipo_id).count()
    )
    if en_uso:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar: {en_uso} equipo(s) usan este tipo. Desactívalo en su lugar.",
        )
    db.delete(obj)
    db.commit()


# ===========================================================================
# Estados de equipo
# ===========================================================================
def list_estados_equipo(
    db: Session,
    empresa_id: UUID,
    activo: Optional[bool] = None,
) -> List[EstadoEquipo]:
    query = db.query(EstadoEquipo).filter(EstadoEquipo.empresa_id == empresa_id)
    if activo is not None:
        query = query.filter(EstadoEquipo.activo == activo)
    return query.order_by(EstadoEquipo.orden, EstadoEquipo.nombre).all()


def get_estado_equipo(db: Session, estado_id: UUID) -> EstadoEquipo:
    obj = db.query(EstadoEquipo).filter(EstadoEquipo.id == estado_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Estado de equipo no encontrado.")
    return obj


def create_estado_equipo(db: Session, data: EstadoEquipoCreate) -> EstadoEquipo:
    obj = EstadoEquipo(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_estado_equipo(
    db: Session, estado_id: UUID, data: EstadoEquipoUpdate
) -> EstadoEquipo:
    obj = get_estado_equipo(db, estado_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_estado_equipo(db: Session, estado_id: UUID) -> None:
    obj = get_estado_equipo(db, estado_id)
    db.delete(obj)  # equipos.estado_id -> SET NULL
    db.commit()


# ===========================================================================
# Equipos de control
# ===========================================================================
def _validar_tipo(db: Session, tipo_equipo_id: UUID, empresa_id: UUID) -> TipoEquipo:
    tipo = get_tipo_equipo(db, tipo_equipo_id)
    if tipo.empresa_id != empresa_id:
        raise HTTPException(
            status_code=400, detail="El tipo de equipo no pertenece a la empresa."
        )
    return tipo


def _validar_valores(tipo: TipoEquipo, valores: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Valida los valores contra los campos requeridos del tipo y filtra claves desconocidas."""
    valores = valores or {}
    claves_validas = {c.clave for c in tipo.campos}
    limpio = {k: v for k, v in valores.items() if k in claves_validas}
    faltantes = [
        c.etiqueta
        for c in tipo.campos
        if c.requerido and (limpio.get(c.clave) in (None, "", []))
    ]
    if faltantes:
        raise HTTPException(
            status_code=422,
            detail="Faltan campos requeridos: " + ", ".join(faltantes),
        )
    return limpio


def list_equipos(
    db: Session,
    cliente_id: Optional[UUID] = None,
    empresa_id: Optional[UUID] = None,
    tipo_equipo_id: Optional[UUID] = None,
    estado_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[EquipoControl], int]:
    query = db.query(EquipoControl)
    if cliente_id:
        query = query.filter(EquipoControl.cliente_id == cliente_id)
    if empresa_id:
        query = query.filter(EquipoControl.empresa_id == empresa_id)
    if tipo_equipo_id:
        query = query.filter(EquipoControl.tipo_equipo_id == tipo_equipo_id)
    if estado_id:
        query = query.filter(EquipoControl.estado_id == estado_id)
    if activo is not None:
        query = query.filter(EquipoControl.activo == activo)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (EquipoControl.identificador.ilike(like))
            | (EquipoControl.area.ilike(like))
        )
    total = query.count()
    items = (
        query.order_by(EquipoControl.area, EquipoControl.identificador)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_equipo(db: Session, equipo_id: UUID) -> EquipoControl:
    obj = db.query(EquipoControl).filter(EquipoControl.id == equipo_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado.")
    return obj


def create_equipo(db: Session, data: EquipoControlCreate) -> EquipoControl:
    tipo = _validar_tipo(db, data.tipo_equipo_id, data.empresa_id)
    obj_data = data.model_dump()
    obj_data["valores"] = _validar_valores(tipo, obj_data.get("valores"))
    obj = EquipoControl(**obj_data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_equipo(db: Session, equipo_id: UUID, data: EquipoControlUpdate) -> EquipoControl:
    obj = get_equipo(db, equipo_id)
    update_data = data.model_dump(exclude_unset=True)
    nuevo_tipo_id = update_data.get("tipo_equipo_id", obj.tipo_equipo_id)
    tipo = _validar_tipo(db, nuevo_tipo_id, obj.empresa_id)
    if "valores" in update_data:
        update_data["valores"] = _validar_valores(tipo, update_data["valores"])
    for field, value in update_data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_equipo(db: Session, equipo_id: UUID) -> None:
    obj = get_equipo(db, equipo_id)
    db.delete(obj)
    db.commit()


def bulk_create_equipos(db: Session, data: EquipoControlBulkCreate) -> List[EquipoControl]:
    """Crea N equipos numerados consecutivamente en un área."""
    tipo = _validar_tipo(db, data.tipo_equipo_id, data.empresa_id)
    valores = _validar_valores(tipo, data.valores)
    prefijo = data.prefijo or ""
    creados: List[EquipoControl] = []
    for i in range(data.cantidad):
        numero = data.numero_inicial + i
        num_str = str(numero).zfill(data.relleno_ceros) if data.relleno_ceros else str(numero)
        obj = EquipoControl(
            empresa_id=data.empresa_id,
            cliente_id=data.cliente_id,
            tipo_equipo_id=data.tipo_equipo_id,
            estado_id=data.estado_id,
            identificador=f"{prefijo}{num_str}" if (prefijo or num_str) else None,
            area=data.area,
            fecha_instalacion=data.fecha_instalacion,
            activo=True,
            valores=dict(valores),
        )
        db.add(obj)
        creados.append(obj)
    db.commit()
    for obj in creados:
        db.refresh(obj)
    return creados


# ===========================================================================
# Helpers de serialización (nombres de relaciones para el Out)
# ===========================================================================
def to_out_dict(obj: EquipoControl) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "empresa_id": obj.empresa_id,
        "cliente_id": obj.cliente_id,
        "tipo_equipo_id": obj.tipo_equipo_id,
        "tipo_equipo_nombre": obj.tipo_equipo.nombre if obj.tipo_equipo else None,
        "estado_id": obj.estado_id,
        "estado_nombre": obj.estado.nombre if obj.estado else None,
        "identificador": obj.identificador,
        "area": obj.area,
        "fecha_instalacion": obj.fecha_instalacion,
        "notas": obj.notas,
        "activo": obj.activo,
        "valores": obj.valores,
        "creado_en": obj.creado_en,
        "actualizado_en": obj.actualizado_en,
    }
