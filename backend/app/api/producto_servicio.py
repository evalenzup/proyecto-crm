from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.producto_servicio import ProductoServicio
from app.models.empresa import Empresa
from app.schemas.producto_servicio import ProductoServicioOut, ProductoServicioCreate

router = APIRouter()

def check_empresa_exists(db: Session, empresa_id: UUID):
    """
    Verifica que la empresa con el ID dado exista.
    Lanza HTTPException 400 si no existe.
    """
    if not db.query(Empresa).filter(Empresa.id == empresa_id).first():
        raise HTTPException(status_code=400, detail=f"Empresa {empresa_id} no existe")

@router.get("/schema")
def get_form_schema():
    schema = ProductoServicioCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])

    # Campo 'tipo'
    props["tipo"]["x-options"] = [
        {"value": "PRODUCTO", "label": "PRODUCTO"},
        {"value": "SERVICIO", "label": "SERVICIO"},
    ]
    props["tipo"]["enum"] = ["PRODUCTO", "SERVICIO"]

    return {"properties": props, "required": required}

@router.get("/", response_model=List[ProductoServicioOut])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(ProductoServicio).all()

@router.get("/{id}", response_model=ProductoServicioOut)
def obtener_producto(
    id: UUID = Path(...),
    db: Session = Depends(get_db)
):
    prod = db.query(ProductoServicio).filter(ProductoServicio.id == id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    return prod

@router.post("/", response_model=ProductoServicioOut, status_code=201)
def crear_producto(
    payload: ProductoServicioCreate,
    db: Session = Depends(get_db)
):
    data = payload.dict()
    # Validar empresa
    check_empresa_exists(db, data["empresa_id"])

    # Validación según tipo
    if data["tipo"] == "PRODUCTO":
        # Campos de inventario obligatorios
        if data.get("stock_actual") is None or data["stock_actual"] < 0:
            raise HTTPException(status_code=400, detail="Stock actual debe ser >= 0 para productos")
        if not data.get("unidad_inventario"):
            raise HTTPException(status_code=400, detail="Unidad de inventario requerida para productos")
    else:
        # Para servicios, limpiamos inventario
        data.update({
            "stock_actual": None,
            "stock_minimo": None,
            "unidad_inventario": None,
            "ubicacion": None,
            "requiere_lote": False,
        })

    nuevo = ProductoServicio(**data)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{id}", response_model=ProductoServicioOut)
def actualizar_producto(
    id: UUID,
    payload: ProductoServicioCreate,
    db: Session = Depends(get_db)
):
    prod = db.query(ProductoServicio).filter(ProductoServicio.id == id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")

    data = payload.dict(exclude_unset=True)
    # Validar empresa si se cambia
    if "empresa_id" in data:
        check_empresa_exists(db, data["empresa_id"])

    # Validación según tipo
    tipo = data.get("tipo", prod.tipo)
    if tipo == "PRODUCTO":
        stock_actual = data.get("stock_actual", prod.stock_actual)
        if stock_actual is None or stock_actual < 0:
            raise HTTPException(status_code=400, detail="Stock actual debe ser >= 0 para productos")
        unidad_inv = data.get("unidad_inventario", prod.unidad_inventario)
        if not unidad_inv:
            raise HTTPException(status_code=400, detail="Unidad de inventario requerida para productos")
    else:
        # Limpiar inventario si cambia a servicio
        data.update({
            "stock_actual": None,
            "stock_minimo": None,
            "unidad_inventario": None,
            "ubicacion": None,
            "requiere_lote": False,
        })

    for attr, val in data.items():
        setattr(prod, attr, val)
    db.commit()
    db.refresh(prod)
    return prod

@router.delete("/{id}", status_code=204)
def eliminar_producto(
    id: UUID,
    db: Session = Depends(get_db)
):
    prod = db.query(ProductoServicio).filter(ProductoServicio.id == id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto/Servicio no encontrado")
    db.delete(prod)
    db.commit()
    return
