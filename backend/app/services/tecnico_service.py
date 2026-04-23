# app/services/tecnico_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tecnico import Tecnico
from app.schemas.tecnico import TecnicoCreate, TecnicoUpdate
from app.services.servicio_operativo_service import get_servicios_by_ids


def list_tecnicos(
    db: Session,
    empresa_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Tecnico], int]:
    query = db.query(Tecnico)
    if empresa_id:
        query = query.filter(Tecnico.empresa_id == empresa_id)
    if q:
        query = query.filter(Tecnico.nombre_completo.ilike(f"%{q}%"))
    if activo is not None:
        query = query.filter(Tecnico.activo == activo)
    total = query.count()
    items = query.order_by(Tecnico.nombre_completo).offset(offset).limit(limit).all()
    return items, total


def get_tecnico(db: Session, tecnico_id: UUID) -> Tecnico:
    obj = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Técnico no encontrado.")
    return obj


def create_tecnico(db: Session, data: TecnicoCreate) -> Tecnico:
    especialidades_ids = data.especialidades_ids or []
    obj_data = data.model_dump(exclude={"especialidades_ids"})
    obj = Tecnico(**obj_data)
    if especialidades_ids:
        obj.especialidades = get_servicios_by_ids(db, especialidades_ids, data.empresa_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_tecnico(db: Session, tecnico_id: UUID, data: TecnicoUpdate) -> Tecnico:
    obj = get_tecnico(db, tecnico_id)
    update_data = data.model_dump(exclude_unset=True)
    especialidades_ids = update_data.pop("especialidades_ids", None)
    for field, value in update_data.items():
        setattr(obj, field, value)
    if especialidades_ids is not None:
        obj.especialidades = get_servicios_by_ids(db, especialidades_ids, obj.empresa_id)
    db.commit()
    db.refresh(obj)
    return obj


def delete_tecnico(db: Session, tecnico_id: UUID) -> None:
    obj = get_tecnico(db, tecnico_id)
    db.delete(obj)
    db.commit()
