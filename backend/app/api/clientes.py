# app/api/clientes.py

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteOut, ClienteCreate, ClienteUpdate

router = APIRouter()

@router.get("/schema")
def get_form_schema(db: Session = Depends(get_db)):
    schema = ClienteCreate.schema()
    props = schema["properties"]
    # empresa_id como array de UUIDs con opciones
    props["empresa_id"]["type"] = "array"
    props["empresa_id"]["items"] = {"type": "string", "format": "uuid"}
    empresas = db.query(Empresa).all()
    props["empresa_id"]["x-options"] = [
        {"value": str(e.id), "label": e.nombre_comercial} for e in empresas
    ]
    # teléfono y email siguen siendo list<string>
    props["telefono"]["type"] = "array"
    props["telefono"]["items"] = {"type": "string"}
    props["email"]["type"] = "array"
    props["email"]["items"] = {"type": "string", "format": "email"}
    return {"properties": props, "required": schema.get("required", [])}

@router.get("/", response_model=List[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).all()

@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(id: UUID = Path(...), db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente

@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    empresas = db.query(Empresa).filter(Empresa.id.in_(payload.empresa_id)).all()
    if len(empresas) != len(payload.empresa_id):
        raise HTTPException(404, "Alguna empresa no existe")
    datos = payload.model_dump(exclude={"empresa_id"})
    nuevo = Cliente(**datos)
    nuevo.empresas = empresas
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(
    id: UUID,
    payload: ClienteUpdate,
    db: Session = Depends(get_db)
):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    datos = payload.model_dump(exclude_none=True, exclude={"empresa_id"})
    for attr, val in datos.items():
        setattr(cliente, attr, val)
    if payload.empresa_id is not None:
        empresas = db.query(Empresa).filter(Empresa.id.in_(payload.empresa_id)).all()
        if len(empresas) != len(payload.empresa_id):
            raise HTTPException(404, "Alguna empresa no existe")
        cliente.empresas = empresas
    db.commit()
    db.refresh(cliente)
    return cliente

@router.delete("/{id}", status_code=204)
def eliminar_cliente(id: UUID, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    db.delete(cliente)
    db.commit()