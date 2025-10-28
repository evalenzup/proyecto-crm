from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.schemas.contacto import ContactoCreate, ContactoUpdate, ContactoOut
from app.services.contacto_service import contacto_repo

router = APIRouter()

class ContactoPageOut(BaseModel):
    items: List[ContactoOut]
    total: int
    limit: int
    offset: int

@router.post(
    "/clientes/{cliente_id}/contactos",
    response_model=ContactoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un contacto para un cliente",
)
def create_contacto_for_cliente(
    cliente_id: UUID, contacto: ContactoCreate, db: Session = Depends(get_db)
):
    return contacto_repo.create_for_cliente(db, cliente_id=cliente_id, obj_in=contacto)


@router.get(
    "/clientes/{cliente_id}/contactos",
    response_model=ContactoPageOut,
    summary="Listar contactos de un cliente",
)
def read_contactos_for_cliente(
    cliente_id: UUID,
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    items, total = contacto_repo.get_for_cliente(
        db, cliente_id=cliente_id, skip=offset, limit=limit
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.put("/contactos/{contacto_id}", response_model=ContactoOut, summary="Actualizar un contacto")
def update_contacto(
    contacto_id: UUID, contacto: ContactoUpdate, db: Session = Depends(get_db)
):
    db_contacto = contacto_repo.get(db, id=contacto_id)
    if not db_contacto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado"
        )
    return contacto_repo.update(db, db_obj=db_contacto, obj_in=contacto)


@router.delete("/contactos/{contacto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un contacto")
def delete_contacto(contacto_id: UUID, db: Session = Depends(get_db)):
    db_contacto = contacto_repo.remove(db, id=contacto_id)
    if not db_contacto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado"
        )
    return