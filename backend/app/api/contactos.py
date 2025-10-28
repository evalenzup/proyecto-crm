
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.cliente import Cliente
from app.models.contacto import Contacto
from app.schemas.contacto import ContactoCreate, ContactoUpdate, ContactoOut

router = APIRouter()

@router.post("/clientes/{cliente_id}/contactos", response_model=ContactoOut, status_code=status.HTTP_201_CREATED)
def create_contacto_for_cliente(cliente_id: UUID, contacto: ContactoCreate, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    
    db_contacto = Contacto(**contacto.model_dump(), cliente_id=cliente_id)
    db.add(db_contacto)
    db.commit()
    db.refresh(db_contacto)
    return db_contacto

@router.get("/clientes/{cliente_id}/contactos", response_model=List[ContactoOut])
def read_contactos_for_cliente(cliente_id: UUID, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente.contactos

@router.put("/contactos/{contacto_id}", response_model=ContactoOut)
def update_contacto(contacto_id: UUID, contacto: ContactoUpdate, db: Session = Depends(get_db)):
    db_contacto = db.query(Contacto).filter(Contacto.id == contacto_id).first()
    if not db_contacto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    
    update_data = contacto.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_contacto, key, value)
    
    db.commit()
    db.refresh(db_contacto)
    return db_contacto

@router.delete("/contactos/{contacto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contacto(contacto_id: UUID, db: Session = Depends(get_db)):
    db_contacto = db.query(Contacto).filter(Contacto.id == contacto_id).first()
    if not db_contacto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    
    db.delete(db_contacto)
    db.commit()
    return
