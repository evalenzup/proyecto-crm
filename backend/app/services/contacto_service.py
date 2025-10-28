# app/services/contacto_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from uuid import UUID

from app.models.cliente import Cliente
from app.models.contacto import Contacto
from app.schemas.contacto import ContactoCreate, ContactoUpdate
from app.repository.base import BaseRepository


class ContactoRepository(BaseRepository[Contacto, ContactoCreate, ContactoUpdate]):
    def create_for_cliente(
        self, db: Session, *, cliente_id: UUID, obj_in: ContactoCreate
    ) -> Contacto:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado para crear contacto"
            )
        db_obj = self.model(**obj_in.model_dump(), cliente_id=cliente_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_for_cliente(
        self, db: Session, *, cliente_id: UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Contacto], int]:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado para listar contactos"
            )
        
        query = db.query(self.model).filter(self.model.cliente_id == cliente_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total


contacto_repo = ContactoRepository(Contacto)
