# app/services/egreso_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import date

from app.models.egreso import Egreso as EgresoModel
from app.schemas.egreso import EgresoCreate, EgresoUpdate
from app.repository.base import BaseRepository


class EgresoRepository(BaseRepository[EgresoModel, EgresoCreate, EgresoUpdate]):
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        empresa_id: Optional[UUID] = None,
        proveedor: Optional[str] = None,
        categoria: Optional[str] = None,
        estatus: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ) -> Tuple[List[EgresoModel], int]:
        query = db.query(self.model)

        if empresa_id:
            query = query.filter(self.model.empresa_id == empresa_id)
        if proveedor:
            query = query.filter(self.model.proveedor.ilike(f"%{proveedor}%"))
        if categoria:
            query = query.filter(self.model.categoria == categoria)
        if estatus:
            query = query.filter(self.model.estatus == estatus)
        if fecha_desde:
            query = query.filter(self.model.fecha_egreso >= fecha_desde)
        if fecha_hasta:
            query = query.filter(self.model.fecha_egreso <= fecha_hasta)

        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total


egreso_repo = EgresoRepository(EgresoModel)
