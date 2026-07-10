# app/services/tecnico_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tecnico import Tecnico
from app.schemas.tecnico import TecnicoCreate, TecnicoUpdate
from app.services.servicio_operativo_service import get_servicios_by_ids


def _build_nombre_completo(nombre: Optional[str], primer_ap: Optional[str], segundo_ap: Optional[str]) -> str:
    partes = [p for p in [nombre, primer_ap, segundo_ap] if p]
    return " ".join(partes) or "Sin nombre"


def list_tecnicos(
    db: Session,
    empresa_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = None,
    tipo_personal: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order_by: Optional[str] = None,
    order_dir: Optional[str] = None,
) -> Tuple[List[Tecnico], int]:
    from app.services.ordering import apply_order
    query = db.query(Tecnico)
    if empresa_id:
        query = query.filter(Tecnico.empresa_id == empresa_id)
    if q:
        query = query.filter(Tecnico.nombre_completo.ilike(f"%{q}%"))
    if activo is not None:
        query = query.filter(Tecnico.activo == activo)
    if tipo_personal:
        query = query.filter(Tecnico.tipo_personal == tipo_personal)
    total = query.count()
    query = apply_order(
        query, Tecnico, order_by, order_dir,
        allowed={"nombre_completo", "tipo_personal", "puesto", "celular", "email", "activo"},
        default="nombre_completo",
    )
    items = query.offset(offset).limit(limit).all()
    return items, total


def get_tecnico(db: Session, tecnico_id: UUID) -> Tecnico:
    obj = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personal no encontrado.")
    return obj


def create_tecnico(db: Session, data: TecnicoCreate) -> Tecnico:
    especialidades_ids = data.especialidades_ids or []
    obj_data = data.model_dump(exclude={"especialidades_ids"})
    obj_data["nombre_completo"] = _build_nombre_completo(
        obj_data.get("nombre"), obj_data.get("primer_apellido"), obj_data.get("segundo_apellido")
    )
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
    # Recalcular nombre_completo si alguno de los campos de nombre cambió
    if any(k in update_data for k in ("nombre", "primer_apellido", "segundo_apellido")):
        obj.nombre_completo = _build_nombre_completo(obj.nombre, obj.primer_apellido, obj.segundo_apellido)
    if especialidades_ids is not None:
        obj.especialidades = get_servicios_by_ids(db, especialidades_ids, obj.empresa_id)
    db.commit()
    db.refresh(obj)
    return obj


def delete_tecnico(db: Session, tecnico_id: UUID) -> None:
    obj = get_tecnico(db, tecnico_id)
    db.delete(obj)
    db.commit()
