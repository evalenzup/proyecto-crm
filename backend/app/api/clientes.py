from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.database import get_db
from app.schemas.cliente import ClienteOut, ClienteCreate, ClienteUpdate
from app.services import cliente_service
from app.auth.security import get_current_user, User
from app.catalogos_sat import obtener_todos_regimenes

router = APIRouter()

@router.get(
    "/schema",
    summary="Obtener el schema del modelo")
def get_form_schema():
    """
    Devuelve el schema del modelo cliente
    """
    schema = ClienteCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])
    # Campo 'actividad'
    props["actividad"]["x-options"] = [
        {"value": "RESIDENCIAL", "label": "RESIDENCIAL"},
        {"value": "COMERCIAL", "label": "COMERCIAL"},
        {"value": "INDUSTRIAL", "label": "INDUSTRIAL"},
    ]
    # Campo 'tamano'
    props["tamano"]["x-options"] = [
        {"value": "CHICO", "label": "CHICO"},
        {"value": "MEDIANO", "label": "MEDIANO"},
        {"value": "GRANDE", "label": "GRANDE"},
    ]
    # Para los regimenes
    regimenes = obtener_todos_regimenes()
    props["regimen_fiscal"]["x-options"] = [
        {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"} for r in regimenes
    ]
    props["regimen_fiscal"]["enum"] = [r["clave"] for r in regimenes]
    return {"properties": props, "required": required}

@router.get("/", response_model=List[ClienteOut], summary="Obtener los clientes de una empresa")
def listar_clientes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return cliente_service.get_clientes_by_empresa(db, current_user.empresa_id)

@router.get("/{id}", response_model=ClienteOut)
def obtener_cliente(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cliente = cliente_service.get_cliente(db, id, current_user.empresa_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return cliente_service.create_cliente(db, cliente, current_user.empresa_id)

@router.put("/{id}", response_model=ClienteOut)
def actualizar_cliente(id: UUID, cliente: ClienteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_cliente = cliente_service.update_cliente(db, id, cliente, current_user.empresa_id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return db_cliente

@router.delete("/{id}", status_code=204)
def eliminar_cliente(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not cliente_service.delete_cliente(db, id, current_user.empresa_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return Response(status_code=204)
