# app/services/cliente_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.catalogos_sat import validar_regimen_fiscal
from app.catalogos_sat.codigos_postales import validar_codigo_postal
from app.validators.rfc import validar_rfc_por_regimen

def _validar_datos_cliente(
    db: Session,
    rfc: Optional[str] = None,
    regimen_fiscal: Optional[str] = None,
    codigo_postal: Optional[str] = None,
    cliente_existente: Optional[Cliente] = None
):
    if regimen_fiscal and not validar_regimen_fiscal(regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")
    if codigo_postal and not validar_codigo_postal(codigo_postal):
        raise HTTPException(status_code=400, detail="Código postal inválido.")
    if rfc:
        regimen = regimen_fiscal or getattr(cliente_existente, 'regimen_fiscal', None)
        if not validar_rfc_por_regimen(rfc, regimen):
            raise HTTPException(status_code=400, detail="RFC inválido para el régimen fiscal.")


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

def create_cliente(db: Session, cliente_data: ClienteCreate) -> Cliente:
    _validar_datos_cliente(
        db=db,
        rfc=cliente_data.rfc,
        regimen_fiscal=cliente_data.regimen_fiscal,
        codigo_postal=cliente_data.codigo_postal
    )

    empresa = db.query(Empresa).filter(Empresa.id == cliente_data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    cliente_existente = db.query(Cliente).filter(Cliente.nombre_comercial == cliente_data.nombre_comercial).first()

    if cliente_existente:
        if empresa in cliente_existente.empresas:
            raise HTTPException(status_code=400, detail="El cliente ya está asociado a esta empresa")
        cliente_existente.empresas.append(empresa)
        db.commit()
        db.refresh(cliente_existente)
        return cliente_existente
    else:
        nuevo_cliente = Cliente(**cliente_data.dict(exclude={"empresa_id"}))
        nuevo_cliente.empresas.append(empresa)
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return nuevo_cliente

def update_cliente(db: Session, cliente_id: UUID, cliente_data: ClienteUpdate, empresa_id: UUID) -> Optional[Cliente]:
    db_cliente = get_cliente(db, cliente_id, empresa_id)
    if not db_cliente:
        return None

    update_data = cliente_data.dict(exclude_unset=True)
    _validar_datos_cliente(
        db=db,
        rfc=update_data.get("rfc"),
        regimen_fiscal=update_data.get("regimen_fiscal"),
        codigo_postal=update_data.get("codigo_postal"),
        cliente_existente=db_cliente
    )
    
    for field, value in update_data.items():
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

def get_all_clientes(db: Session) -> List[Cliente]:
    return db.query(Cliente).all()