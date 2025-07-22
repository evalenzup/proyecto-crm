from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.producto_servicio import ProductoServicio
from app.models.empresa import Empresa
from app.schemas.producto_servicio import ProductoServicioOut, ProductoServicioCreate
from app.catalogos_sat.productos import validar_clave_producto
from app.catalogos_sat.unidades import validar_clave_unidad

router = APIRouter()

# ────────────────────────────────────────────────────────────────
# HELPERS

def x_options(items: list[dict], value_key="clave", label_key="descripcion"):
    return [{"value": str(i[value_key]), "label": f"{i[value_key]} — {i[label_key]}"} for i in items]


# ────────────────────────────────────────────────────────────────
# VALIDACIONES

def check_empresa_exists(db: Session, empresa_id: UUID):
    if not db.query(Empresa).filter(Empresa.id == empresa_id).first():
        raise HTTPException(status_code=400, detail=f"Empresa {empresa_id} no existe")

def validar_campos_sat(clave_producto: str, clave_unidad: str):
    if not validar_clave_producto(clave_producto):
        raise HTTPException(status_code=400, detail="Clave de producto no válida")
    if not validar_clave_unidad(clave_unidad):
        raise HTTPException(status_code=400, detail="Clave de unidad no válida")

def limpiar_campos_inventario(data: dict):
    data.update({
        "cantidad": None,
        "stock_actual": None,
        "stock_minimo": None,
        "unidad_inventario": None,
        "ubicacion": None,
        "requiere_lote": False,
    })

def validar_datos_producto(data: dict):
    if data.get("stock_actual") is None or data["stock_actual"] < 0:
        raise HTTPException(status_code=400, detail="Stock actual debe ser >= 0 para productos")
    if not data.get("unidad_inventario"):
        raise HTTPException(status_code=400, detail="Unidad de inventario requerida para productos")
    if data.get("cantidad") is None or data["cantidad"] <= 0:
        raise HTTPException(status_code=400, detail="Cantidad requerida y debe ser mayor a 0 para productos")

# ────────────────────────────────────────────────────────────────
# SCHEMA DINÁMICO

@router.get("/schema")
def get_form_schema(db: Session = Depends(get_db)):
    schema = ProductoServicioCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])

    # Campo 'tipo'
    props["tipo"]["x-options"] = [
        {"value": "PRODUCTO", "label": "PRODUCTO"},
        {"value": "SERVICIO", "label": "SERVICIO"},
    ]
    props["tipo"]["enum"] = ["PRODUCTO", "SERVICIO"]

    # Campo 'empresa_id'
    empresas = db.query(Empresa.id, Empresa.nombre_comercial).all()
    props["empresa_id"]["x-options"] = x_options(
        [{"id": str(e.id), "nombre_comercial": e.nombre_comercial} for e in empresas],
        value_key="id",
        label_key="nombre_comercial"
    )

    return {"properties": props, "required": required}
# ────────────────────────────────────────────────────────────────
# CRUD

@router.get(
    "/",
    response_model=List[ProductoServicioOut],
    summary="Listar productos y servicios"
)
def listar_productos(db=Depends(get_db)):
    """
    Devuelve todos los productos y servicios registrados para todas las empresas.
    """
    return db.query(ProductoServicio).all()

@router.get(
    "/{id}", 
    response_model=ProductoServicioOut,
    summary="Obtener Prodcuto o Servicio por id"
)
def obtener_producto(id: UUID, db: Session = Depends(get_db)):
    """
    Obtiene la información de un producto o servicio existente a partir de su UUID.
    """
    prod = db.query(ProductoServicio).filter(ProductoServicio.id == id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return prod

@router.post(
    "/",
    status_code=201,
    response_model=ProductoServicioOut,
    summary="Crear producto o servicio"
)
def crear_producto(
    payload: ProductoServicioCreate,
    db=Depends(get_db)
):
    """
    Crea un nuevo producto o servicio asociado a una empresa.
    - **tipo**: \"PRODUCTO\" o \"SERVICIO\".  
    - **empresa_id**: UUID de la empresa propietaria.
    """
    data = payload.dict()

    check_empresa_exists(db, data["empresa_id"])
    validar_campos_sat(data["clave_producto"], data["clave_unidad"])

    if data["tipo"] == "PRODUCTO":
        validar_datos_producto(data)
    else:
        limpiar_campos_inventario(data)  # limpia cantidad, inventario, lote, etc.

    # Validar que no se repita la descripción por empresa
    existe = db.query(ProductoServicio).filter(
        ProductoServicio.descripcion == data["descripcion"],
        ProductoServicio.empresa_id == data["empresa_id"]
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un producto o servicio con esa descripción para esta empresa")

    nuevo = ProductoServicio(**data)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put(
    "/{id}", 
    response_model=ProductoServicioOut,
    summary="Editar producto o servicio"
)
def actualizar_producto(
    id: UUID, 
    payload: ProductoServicioCreate, 
    db: Session = Depends(get_db)):
    """
    Edita producto o servicio existente.
    - **tipo**: \"PRODUCTO\" o \"SERVICIO\".  
    """
    prod = db.query(ProductoServicio).filter(ProductoServicio.id == id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")

    data = payload.dict(exclude_unset=True)

    if "empresa_id" in data:
        check_empresa_exists(db, data["empresa_id"])

    if "clave_producto" in data or "clave_unidad" in data:
        clave_prod = data.get("clave_producto", prod.clave_producto)
        clave_uni = data.get("clave_unidad", prod.clave_unidad)
        validar_campos_sat(clave_prod, clave_uni)

    tipo = data.get("tipo", prod.tipo)
    if tipo == "PRODUCTO":
        validar_datos_producto(data)
    else:
        limpiar_campos_inventario(data)

    for attr, val in data.items():
        setattr(prod, attr, val)

    db.commit()
    db.refresh(prod)
    return prod

@router.delete(
    "/{id}", 
    status_code=204,
    summary="Elimina un producto o servicio"
)
def eliminar_producto(id: UUID, db: Session = Depends(get_db)):
    """
    Elimina producto o servicio asociado a una empresa.
    - **tipo**: \"PRODUCTO\" o \"SERVICIO\".  
    - **empresa_id**: UUID de la empresa propietaria.
    """
    prod = db.query(ProductoServicio).filter(ProductoServicio.id == id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    db.delete(prod)
    db.commit()