# app/api/producto_servicio.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.producto_servicio import (
    ProductoServicioOut,
    ProductoServicioCreate,
    ProductoServicioUpdate,
)
from app.services.producto_servicio_service import (
    producto_servicio_repo,
)  # Importamos el nuevo repositorio
from pydantic import BaseModel


class ProductoServicioPageOut(BaseModel):
    items: List[ProductoServicioOut]
    total: int
    limit: int
    offset: int


router = APIRouter()


def x_options(items: list[dict], value_key="clave", label_key="descripcion"):
    # Genera [{ value, label }] sin repetir la clave en el label
    return [{"value": str(i[value_key]), "label": str(i[label_key])} for i in items]


@router.get("/schema", summary="Obtiene schema de modelo producto-servicio")
def get_form_schema(db: Session = Depends(get_db)):
    # Pydantic v2
    try:
        schema = ProductoServicioCreate.model_json_schema()
    except Exception:
        schema = ProductoServicioCreate.schema()

    props = schema["properties"]
    required = schema.get("required", [])

    # Campo 'tipo'
    props["tipo"]["x-options"] = [
        {"value": "PRODUCTO", "label": "PRODUCTO"},
        {"value": "SERVICIO", "label": "SERVICIO"},
    ]
    # Enum correcto para el tipo
    props["tipo"]["enum"] = ["PRODUCTO", "SERVICIO"]

    # Campo 'empresa_id' (x-options con empresas existentes)
    empresas = db.query(Empresa.id, Empresa.nombre_comercial).all()
    props["empresa_id"]["x-options"] = x_options(
        [{"id": str(e.id), "nombre_comercial": e.nombre_comercial} for e in empresas],
        value_key="id",
        label_key="nombre_comercial",
    )

    # Campo 'requiere_lote'
    props["requiere_lote"]["x-options"] = [
        {"value": True, "label": "Sí"},
        {"value": False, "label": "No"},
    ]
    props["requiere_lote"]["enum"] = [True, False]

    return {"properties": props, "required": required}


@router.get(
    "/",
    response_model=ProductoServicioPageOut,
    summary="Listar productos y servicios",
)
def listar_productos(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    empresa_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None, description="Término de búsqueda en clave o descripción"),
):
    items, total = producto_servicio_repo.get_multi(
        db,
        skip=offset,
        limit=limit,
        empresa_id=empresa_id,
        q=q,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/busqueda",
    response_model=List[ProductoServicioOut],
    summary="Buscar productos o servicios",
)
def buscar_productos(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    empresa_id: Optional[UUID] = Query(None, description="Filtrar por ID de empresa"),
    db: Session = Depends(get_db),
):
    """
    Busca productos o servicios que coincidan con el término `q` en su clave o descripción.
    Se puede filtrar opcionalmente por `empresa_id`.
    """
    productos = producto_servicio_repo.search_by_term(db, q=q, empresa_id=empresa_id)
    return productos


@router.get(
    "/{id}",
    response_model=ProductoServicioOut,
    summary="Obtener producto/servicio por ID",
)
def obtener_producto(id: UUID, db: Session = Depends(get_db)):
    prod = producto_servicio_repo.get(db, id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return prod


@router.post(
    "/",
    status_code=201,
    response_model=ProductoServicioOut,
    summary="Crear producto o servicio",
)
def crear_producto(payload: ProductoServicioCreate, db: Session = Depends(get_db)):
    return producto_servicio_repo.create(db, obj_in=payload)


@router.put(
    "/{id}", response_model=ProductoServicioOut, summary="Editar producto o servicio"
)
def actualizar_producto(
    id: UUID, payload: ProductoServicioUpdate, db: Session = Depends(get_db)
):
    prod = producto_servicio_repo.get(db, id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return producto_servicio_repo.update(db, db_obj=prod, obj_in=payload)


@router.delete("/{id}", status_code=204, summary="Eliminar producto o servicio")
def eliminar_producto(id: UUID, db: Session = Depends(get_db)):
    ok = producto_servicio_repo.remove(db, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return Response(status_code=204)
