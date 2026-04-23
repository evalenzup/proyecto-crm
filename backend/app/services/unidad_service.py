# app/services/unidad_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.unidad import Unidad
from app.schemas.unidad import UnidadCreate, UnidadUpdate
from app.services.servicio_operativo_service import get_servicios_by_ids


def list_unidades(
    db: Session,
    empresa_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Unidad], int]:
    query = db.query(Unidad)
    if empresa_id:
        query = query.filter(Unidad.empresa_id == empresa_id)
    if q:
        query = query.filter(Unidad.nombre.ilike(f"%{q}%"))
    if activo is not None:
        query = query.filter(Unidad.activo == activo)
    total = query.count()
    items = query.order_by(Unidad.nombre).offset(offset).limit(limit).all()
    return items, total


def get_unidad(db: Session, unidad_id: UUID) -> Unidad:
    obj = db.query(Unidad).filter(Unidad.id == unidad_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Unidad no encontrada.")
    return obj


def create_unidad(db: Session, data: UnidadCreate) -> Unidad:
    servicios_ids = data.servicios_ids or []
    obj_data = data.model_dump(exclude={"servicios_ids"})
    obj = Unidad(**obj_data)
    if servicios_ids:
        obj.servicios_compatibles = get_servicios_by_ids(db, servicios_ids, data.empresa_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_unidad(db: Session, unidad_id: UUID, data: UnidadUpdate) -> Unidad:
    obj = get_unidad(db, unidad_id)
    update_data = data.model_dump(exclude_unset=True)
    servicios_ids = update_data.pop("servicios_ids", None)
    for field, value in update_data.items():
        setattr(obj, field, value)
    if servicios_ids is not None:
        obj.servicios_compatibles = get_servicios_by_ids(db, servicios_ids, obj.empresa_id)
    db.commit()
    db.refresh(obj)
    return obj


def delete_unidad(db: Session, unidad_id: UUID) -> None:
    obj = get_unidad(db, unidad_id)
    db.delete(obj)
    db.commit()
