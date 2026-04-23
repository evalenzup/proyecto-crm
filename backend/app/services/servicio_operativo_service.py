# app/services/servicio_operativo_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.servicio_operativo import ServicioOperativo
from app.schemas.servicio_operativo import ServicioOperativoCreate, ServicioOperativoUpdate


def get_servicios_by_ids(
    db: Session, ids: List[UUID], empresa_id: UUID
) -> List[ServicioOperativo]:
    """Valida y devuelve ServicioOperativos verificando que pertenezcan a la empresa.
    Utilizado por tecnico_service y unidad_service para asignar M2M."""
    if not ids:
        return []
    servicios = (
        db.query(ServicioOperativo)
        .filter(
            ServicioOperativo.id.in_(ids),
            ServicioOperativo.empresa_id == empresa_id,
        )
        .all()
    )
    if len(servicios) != len(set(ids)):
        raise HTTPException(
            status_code=400,
            detail="Uno o más servicios operativos no existen o no pertenecen a la empresa.",
        )
    return servicios


def list_servicios(
    db: Session,
    empresa_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ServicioOperativo], int]:
    query = db.query(ServicioOperativo)
    if empresa_id:
        query = query.filter(ServicioOperativo.empresa_id == empresa_id)
    if q:
        query = query.filter(ServicioOperativo.nombre.ilike(f"%{q}%"))
    if activo is not None:
        query = query.filter(ServicioOperativo.activo == activo)
    total = query.count()
    items = query.order_by(ServicioOperativo.nombre).offset(offset).limit(limit).all()
    return items, total


def get_servicio(db: Session, servicio_id: UUID) -> ServicioOperativo:
    obj = (
        db.query(ServicioOperativo)
        .filter(ServicioOperativo.id == servicio_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Servicio operativo no encontrado.")
    return obj


def create_servicio(db: Session, data: ServicioOperativoCreate) -> ServicioOperativo:
    existing = (
        db.query(ServicioOperativo)
        .filter(
            ServicioOperativo.empresa_id == data.empresa_id,
            ServicioOperativo.nombre == data.nombre,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un servicio operativo con ese nombre en la empresa.",
        )
    obj = ServicioOperativo(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_servicio(
    db: Session, servicio_id: UUID, data: ServicioOperativoUpdate
) -> ServicioOperativo:
    obj = get_servicio(db, servicio_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_servicio(db: Session, servicio_id: UUID) -> None:
    obj = get_servicio(db, servicio_id)
    db.delete(obj)
    db.commit()
