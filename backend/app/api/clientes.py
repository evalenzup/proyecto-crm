from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteOut, ClienteCreate, ClienteUpdate
from app.auth.security import get_current_user, User

router = APIRouter()

#Funcion para listar clientes de una empresa
@router.get("/", response_model=List[ClienteOut])
def listar_clientes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa.clientes

# Endpoints para manejar clientes asociados a una empresa
@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente or current_user.empresa_id not in [e.id for e in cliente.empresas]:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

# Endpoint para crear un nuevo cliente asociado a la empresa del usuario actual
@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    nueva_empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not nueva_empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    nuevo_cliente = Cliente(**cliente.dict())
    nuevo_cliente.empresas.append(nueva_empresa)
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente

# Endpoint para actualizar un cliente existente
@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(id: UUID, cliente: ClienteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not db_cliente or current_user.empresa_id not in [e.id for e in db_cliente.empresas]:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for campo, valor in cliente.dict(exclude_unset=True).items():
        setattr(db_cliente, campo, valor)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

# Endpoint para eliminar un cliente asociado a la empresa del usuario actual
@router.delete("/{id}", status_code=204)
def eliminar_cliente(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente or current_user.empresa_id not in [e.id for e in cliente.empresas]:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if empresa:
        cliente.empresas.remove(empresa)
        if not cliente.empresas:
            db.delete(cliente)
    db.commit()
    return Response(status_code=204)
