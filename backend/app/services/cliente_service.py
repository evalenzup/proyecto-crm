# app/services/cliente_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteCreate, ClienteUpdate

def get_cliente(db: Session, cliente_id: UUID, empresa_id: UUID) -> Optional[Cliente]:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente or empresa_id not in [e.id for e in cliente.empresas]:
        return None
    return cliente

def get_clientes_by_empresa(db: Session, empresa_id: UUID) -> List[Cliente]:
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        return []
    return empresa.clientes

def create_cliente(db: Session, cliente_data: ClienteCreate, empresa_id: UUID) -> Cliente:
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    nuevo_cliente = Cliente(**cliente_data.dict())
    nuevo_cliente.empresas.append(empresa)
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente

def update_cliente(db: Session, cliente_id: UUID, cliente_data: ClienteUpdate, empresa_id: UUID) -> Optional[Cliente]:
    db_cliente = get_cliente(db, cliente_id, empresa_id)
    if not db_cliente:
        return None
    
    for field, value in cliente_data.dict(exclude_unset=True).items():
        setattr(db_cliente, field, value)
    
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

def delete_cliente(db: Session, cliente_id: UUID, empresa_id: UUID) -> bool:
    cliente = get_cliente(db, cliente_id, empresa_id)
    if not cliente:
        return False
    
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if empresa:
        cliente.empresas.remove(empresa)
        if not cliente.empresas:
            db.delete(cliente)
    
    db.commit()
    return True