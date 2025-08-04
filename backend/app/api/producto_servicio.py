from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.producto_servicio import (
    ProductoServicioOut, ProductoServicioCreate, ProductoServicioUpdate
)
from app.services import producto_servicio_service

router = APIRouter()

def x_options(items: list[dict], value_key="clave", label_key="descripcion"):
    return [{"value": str(i[value_key]), "label": f"{i[value_key]} — {i[label_key]}"} for i in items]

@router.get(
    "/schema",
    summary="Obtiene schema de modelo producto-servicio"
)
def get_form_schema(db: Session = Depends(get_db)):
    schema = ProductoServicioCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])

    props["tipo"]["x-options"] = [
        {"value": "PRODUCTO", "label": "PRODUCTO"},
        {"value": "SERVICIO", "label": "SERVICIO"},
    ]
    props["tipo"]["enum"] = ["PRODUCTO", "SERVICIO"]

    empresas = db.query(Empresa.id, Empresa.nombre_comercial).all()
    props["empresa_id"]["x-options"] = x_options(
        [{"id": str(e.id), "nombre_comercial": e.nombre_comercial} for e in empresas],
        value_key="id",
        label_key="nombre_comercial"
    )
    props["requiere_lote"]["x-options"] = [
        {"value": True, "label": "Sí"},
        {"value": False, "label": "No"},
    ]
    props["requiere_lote"]["enum"] = [True, False]
    
    return {"properties": props, "required": required}

@router.get("/", response_model=List[ProductoServicioOut], summary="Listar productos y servicios")
def listar_productos(db: Session = Depends(get_db)):
    return producto_servicio_service.get_all_productos(db)

@router.get("/{id}", response_model=ProductoServicioOut, summary="Obtener Prodcuto o Servicio por id")
def obtener_producto(id: UUID, db: Session = Depends(get_db)):
    prod = producto_servicio_service.get_producto_by_id(db, id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return prod

@router.post("/", status_code=201, response_model=ProductoServicioOut, summary="Crear producto o servicio")
def crear_producto(payload: ProductoServicioCreate, db: Session = Depends(get_db)):
    return producto_servicio_service.create_producto(db, payload)

@router.put("/{id}", response_model=ProductoServicioOut, summary="Editar producto o servicio")
def actualizar_producto(id: UUID, payload: ProductoServicioUpdate, db: Session = Depends(get_db)):
    prod = producto_servicio_service.update_producto(db, id, payload)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return prod

@router.delete("/{id}", status_code=204, summary="Elimina un producto o servicio")
def eliminar_producto(id: UUID, db: Session = Depends(get_db)):
    if not producto_servicio_service.delete_producto(db, id):
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
