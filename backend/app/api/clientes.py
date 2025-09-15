# app/api/clientes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.cliente import ClienteOut, ClienteCreate, ClienteUpdate
from app.services.cliente_service import cliente_repo

router = APIRouter()

# El schema dinámico se mantiene por ahora, ya que está muy acoplado a la vista.
@router.get("/schema")
def get_form_schema(db: Session = Depends(get_db)):
    # Pydantic v2
    try:
        schema = ClienteCreate.model_json_schema()
    except Exception:
        schema = ClienteCreate.schema()
        
    props = schema["properties"]

    props["empresa_id"]["type"] = "array"
    props["empresa_id"]["items"] = {"type": "string", "format": "uuid"}
    empresas = db.query(Empresa).all()
    props["empresa_id"]["x-options"] = [
        {"value": str(e.id), "label": e.nombre_comercial} for e in empresas
    ]

    props["telefono"]["type"] = "array"
    props["telefono"]["items"] = {"type": "string"}
    props["email"]["type"] = "array"
    props["email"]["items"] = {"type": "string", "format": "email"}

    return {"properties": props, "required": schema.get("required", [])}

@router.get("/busqueda", response_model=List[ClienteOut])
def buscar_clientes(
    q: Optional[str] = Query(None, description="Texto a buscar en nombre_comercial (min 3 chars)"),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    db: Session = Depends(get_db),
):
    """Busca clientes por nombre comercial para autocompletado."""
    return cliente_repo.search_by_name(db, name_query=q, limit=limit)

@router.get("/", response_model=List[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    """Obtiene una lista de todos los clientes."""
    return cliente_repo.get_multi(db)

@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(id: UUID = Path(...), db: Session = Depends(get_db)):
    """Obtiene un cliente por su ID."""
    cliente = cliente_repo.get(db, id=id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    """Crea un nuevo cliente."""
    return cliente_repo.create(db, obj_in=payload)

@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(
    id: UUID,
    payload: ClienteUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza un cliente existente."""
    db_cliente = cliente_repo.get(db, id=id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente_repo.update(db, db_obj=db_cliente, obj_in=payload)

@router.delete("/{id}", status_code=204)
def eliminar_cliente(id: UUID, db: Session = Depends(get_db)):
    """Elimina un cliente."""
    cliente = cliente_repo.remove(db, id=id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return Response(status_code=204)
