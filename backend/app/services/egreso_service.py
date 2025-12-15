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

    def search_proveedores(
        self,
        db: Session,
        mpresa_id: Optional[UUID] = None,
        q: str = ""
    ) -> List[str]:
        query = db.query(self.model.proveedor).distinct()
        if mpresa_id:
            query = query.filter(self.model.empresa_id == mpresa_id)
        if q:
            query = query.filter(self.model.proveedor.ilike(f"%{q}%"))
        
        # Limit to 20 suggestions
        results = query.limit(20).all()
        # results is a list of tuples like [('Prov A',), ('Prov B',)]
        return [r[0] for r in results if r[0]]


egreso_repo = EgresoRepository(EgresoModel)
