# app/api/clientes.py

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteOut, ClienteCreate, ClienteUpdate
from app.services import cliente_service

router = APIRouter()

# ────────────────────────────────────────────────────────────────
# /schema: JSON-Schema dinámico para el formulario de clientes
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

    # teléfono y email como list<string>
    props["telefono"]["type"] = "array"
    props["telefono"]["items"] = {"type": "string"}
    props["email"]["type"] = "array"
    props["email"]["items"] = {"type": "string", "format": "email"}

    return {"properties": props, "required": schema.get("required", [])}

# ────────────────────────────────────────────────────────────────
# NUEVO: Autocompletado de clientes por nombre comercial
# GET /api/clientes/busqueda?q=texto&limit=10
@router.get("/busqueda", response_model=List[ClienteOut])
def buscar_clientes(
    q: Optional[str] = Query(None, description="Texto a buscar en nombre_comercial (min 3 chars)"),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    db: Session = Depends(get_db),
):
    """
    Devuelve una lista de clientes cuyo nombre_comercial contenga `q` (ILIKE).
    - Si `q` tiene menos de 3 caracteres, regresa lista vacía (200) para evitar 422.
    - Pensado para autocompletado en el frontend (Select con showSearch).
    """
    if not q or len(q.strip()) < 3:
        return []  # Evita 422 y ruido de validación

    texto = f"%{q.strip()}%"
    rows = (
        db.query(Cliente)
        .filter(Cliente.nombre_comercial.ilike(texto))
        .order_by(Cliente.nombre_comercial.asc())
        .limit(limit)
        .all()
    )
    return rows

# ────────────────────────────────────────────────────────────────
# CRUD básico

@router.get("/", response_model=List[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).all()

# IMPORTANTE: /{id} va DESPUÉS de /busqueda para no capturar "busqueda" como id
@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(id: UUID = Path(...), db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente

@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    return cliente_service.create_cliente(db, payload)

@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(
    id: UUID,
    payload: ClienteUpdate,
    db: Session = Depends(get_db)
):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")

    # Actualiza campos simples (sin empresas)
    datos = payload.model_dump(exclude_none=True, exclude={"empresa_id"})
    for attr, val in datos.items():
        setattr(cliente, attr, val)

    # Si envían empresas, reasigna la relación many-to-many
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