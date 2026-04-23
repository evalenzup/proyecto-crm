# app/services/mantenimiento_unidad_service.py
from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.mantenimiento_unidad import MantenimientoUnidad
from app.schemas.mantenimiento_unidad import MantenimientoCreate, MantenimientoUpdate
from app.services.unidad_service import get_unidad


def list_mantenimientos(
    db: Session,
    unidad_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[MantenimientoUnidad], int]:
    query = db.query(MantenimientoUnidad).filter(
        MantenimientoUnidad.unidad_id == unidad_id
    )
    total = query.count()
    items = (
        query.order_by(MantenimientoUnidad.fecha_realizado.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_mantenimiento(db: Session, mant_id: UUID) -> MantenimientoUnidad:
    obj = (
        db.query(MantenimientoUnidad)
        .filter(MantenimientoUnidad.id == mant_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Registro de mantenimiento no encontrado.")
    return obj


def create_mantenimiento(
    db: Session, unidad_id: UUID, data: MantenimientoCreate
) -> MantenimientoUnidad:
    get_unidad(db, unidad_id)  # verifica que la unidad existe
    obj = MantenimientoUnidad(unidad_id=unidad_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_mantenimiento(
    db: Session, mant_id: UUID, data: MantenimientoUpdate
) -> MantenimientoUnidad:
    obj = get_mantenimiento(db, mant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_mantenimiento(db: Session, mant_id: UUID) -> None:
    obj = get_mantenimiento(db, mant_id)
    db.delete(obj)
    db.commit()
