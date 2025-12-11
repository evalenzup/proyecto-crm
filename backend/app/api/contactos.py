from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.schemas.contacto import ContactoCreate, ContactoUpdate, ContactoOut
from app.services.contacto_service import contacto_repo
from app.models.usuario import Usuario, RolUsuario
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.api import deps

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
    cliente_id: UUID, 
    contacto: ContactoCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    # Validar existencia del cliente y acceso
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if current_user.rol == RolUsuario.SUPERVISOR:
        # Verificar que el cliente pertenezca a la empresa del supervisor
        tiene_acceso = any(e.id == current_user.empresa_id for e in cliente.empresas)
        if not tiene_acceso:
             raise HTTPException(status_code=404, detail="Cliente no encontrado") # Ocultamos información

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
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    # Validar existencia del cliente y acceso
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if current_user.rol == RolUsuario.SUPERVISOR:
        tiene_acceso = any(e.id == current_user.empresa_id for e in cliente.empresas)
        if not tiene_acceso:
             raise HTTPException(status_code=404, detail="Cliente no encontrado")

    items, total = contacto_repo.get_for_cliente(
        db, cliente_id=cliente_id, skip=offset, limit=limit
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.put("/contactos/{contacto_id}", response_model=ContactoOut, summary="Actualizar un contacto")
def update_contacto(
    contacto_id: UUID, 
    contacto: ContactoUpdate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    db_contacto = contacto_repo.get(db, id=contacto_id)
    if not db_contacto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado"
        )
        
    if current_user.rol == RolUsuario.SUPERVISOR:
        # El contacto debe pertenecer a un cliente que pertenezca a la empresa del supervisor
        cliente = db_contacto.cliente
        tiene_acceso = any(e.id == current_user.empresa_id for e in cliente.empresas) if cliente else False
        if not tiene_acceso:
             raise HTTPException(status_code=404, detail="Contacto no encontrado")

    return contacto_repo.update(db, db_obj=db_contacto, obj_in=contacto)


@router.delete("/contactos/{contacto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un contacto")
def delete_contacto(
    contacto_id: UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    db_contacto = contacto_repo.get(db, id=contacto_id)
    if not db_contacto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado"
        )

    if current_user.rol == RolUsuario.SUPERVISOR:
        cliente = db_contacto.cliente
        tiene_acceso = any(e.id == current_user.empresa_id for e in cliente.empresas) if cliente else False
        if not tiene_acceso:
             raise HTTPException(status_code=404, detail="Contacto no encontrado")
             
    contacto_repo.remove(db, id=contacto_id)
    return