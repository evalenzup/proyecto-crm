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


def get_cliente(db: Session, cliente_id: UUID) -> Optional[Cliente]:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
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

    # 1. Validar que las empresas existan
    empresas_a_asociar = db.query(Empresa).filter(Empresa.id.in_(cliente_data.empresa_id)).all()
    if len(empresas_a_asociar) != len(cliente_data.empresa_id):
        raise HTTPException(status_code=404, detail="Una o más empresas no existen")

    # 2. Buscar cliente por NOMBRE COMERCIAL
    cliente_existente = db.query(Cliente).filter(
        Cliente.nombre_comercial == cliente_data.nombre_comercial
    ).first()

    if cliente_existente:
        # 3a. Si existe, añadir las nuevas empresas a la relación
        ids_empresas_actuales = {empresa.id for empresa in cliente_existente.empresas}
        
        for empresa in empresas_a_asociar:
            if empresa.id not in ids_empresas_actuales:
                cliente_existente.empresas.append(empresa)
        
        db.commit()
        db.refresh(cliente_existente)
        return cliente_existente
    else:
        # 3b. Si no existe, crear un nuevo cliente
        datos_cliente = cliente_data.model_dump(exclude={"empresa_id"})
        
        # Convertir listas a strings separados por comas
        if isinstance(datos_cliente.get('email'), list):
            datos_cliente['email'] = ','.join(datos_cliente['email'])
        if isinstance(datos_cliente.get('telefono'), list):
            datos_cliente['telefono'] = ','.join(datos_cliente['telefono'])
            
        nuevo_cliente = Cliente(**datos_cliente)
        nuevo_cliente.empresas = empresas_a_asociar
        
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return nuevo_cliente

def update_cliente(db: Session, cliente_id: UUID, cliente_data: ClienteUpdate) -> Optional[Cliente]:
    db_cliente = get_cliente(db, cliente_id)
    if not db_cliente:
        return None

    update_data = cliente_data.model_dump(exclude_unset=True)
    _validar_datos_cliente(
        db=db,
        rfc=update_data.get("rfc"),
        regimen_fiscal=update_data.get("regimen_fiscal"),
        codigo_postal=update_data.get("codigo_postal"),
        cliente_existente=db_cliente
    )
    
    # Convertir listas a strings separados por comas
    if 'email' in update_data and isinstance(update_data['email'], list):
        update_data['email'] = ','.join(update_data['email'])
    if 'telefono' in update_data and isinstance(update_data['telefono'], list):
        update_data['telefono'] = ','.join(update_data['telefono'])

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

def get_cliente_by_id(db: Session, cliente_id: UUID) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()