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
from app.api import deps
from app.models.usuario import Usuario, RolUsuario
from pydantic import BaseModel


class ClientePageOut(BaseModel):
    items: List[ClienteOut]
    total: int
    limit: int
    offset: int


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
    q: Optional[str] = Query(
        None, description="Texto a buscar en nombre_comercial (min 3 chars)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    empresa_id: Optional[UUID] = Query(None, description="Filtrar por empresa"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Busca clientes por nombre comercial para autocompletado; admite filtro por empresa."""
    # Si es supervisor, forzar empresa_id
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    return cliente_repo.search_by_name(db, name_query=q, limit=limit, empresa_id=empresa_id)


@router.get("/", response_model=ClientePageOut)
def listar_clientes(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    empresa_id: Optional[UUID] = Query(None),
    rfc: Optional[str] = Query(None),
    nombre_comercial: Optional[str] = Query(None),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Obtiene una lista paginada y filtrada de todos los clientes."""
    # Si es supervisor, forzar empresa_id
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    items, total = cliente_repo.get_multi(
        db,
        skip=offset,
        limit=limit,
        empresa_id=empresa_id,
        rfc=rfc,
        nombre_comercial=nombre_comercial,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(
    id: UUID = Path(...), 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Obtiene un cliente por su ID."""
    cliente = cliente_repo.get(db, id=id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Validar acceso por empresa
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
             raise HTTPException(status_code=404, detail="Cliente no encontrado")
             
    return cliente


@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(
    payload: ClienteCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Crea un nuevo cliente."""
    # Si es supervisor, forzar la empresa
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="El usuario supervisor no tiene empresa asignada.")
        payload.empresa_id = [current_user.empresa_id]
        
    return cliente_repo.create(db, obj_in=payload)


@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(
    id: UUID, 
    payload: ClienteUpdate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Actualiza un cliente existente."""
    db_cliente = cliente_repo.get(db, id=id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # Validar acceso
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in db_cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        # No permitir cambiar empresa_id a otra cosa (mantiene solo la suya)
        payload.empresa_id = [current_user.empresa_id]

    return cliente_repo.update(db, db_obj=db_cliente, obj_in=payload)


@router.delete("/{id}", status_code=204)
def eliminar_cliente(
    id: UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
):
    """Elimina un cliente."""
    cliente = cliente_repo.get(db, id=id) # Verificar existencia primero para validar auth
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if current_user.rol == RolUsuario.SUPERVISOR:
        empresas_ids = [e.id for e in cliente.empresas]
        if current_user.empresa_id not in empresas_ids:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente_repo.remove(db, id=id)
    return
