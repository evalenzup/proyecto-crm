# app/services/producto_servicio_service.py

from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import or_, func

from app.models.empresa import Empresa
from app.models.producto_servicio import ProductoServicio
from app.schemas.producto_servicio import ProductoServicioCreate, ProductoServicioUpdate
from app.catalogos_sat.productos import validar_clave_producto
from app.catalogos_sat.unidades import validar_clave_unidad


def _check_empresa_exists(db: Session, empresa_id: UUID):
    if not db.query(Empresa).filter(Empresa.id == empresa_id).first():
        raise HTTPException(status_code=404, detail=f"Empresa {empresa_id} no encontrada")

def _validar_campos_sat(clave_producto: str, clave_unidad: str):
    if not validar_clave_producto(clave_producto):
        raise HTTPException(status_code=400, detail="Clave de producto no válida")
    if not validar_clave_unidad(clave_unidad):
        raise HTTPException(status_code=400, detail="Clave de unidad no válida")

def _limpiar_campos_inventario(data: dict):
    data.update({
        "cantidad": None,
        "stock_actual": None,
        "stock_minimo": None,
        "unidad_inventario": None,
        "ubicacion": None,
        "requiere_lote": False,
    })

def _validar_datos_producto(data: dict):
    if data.get("stock_actual") is None or data["stock_actual"] < 0:
        raise HTTPException(status_code=400, detail="Stock actual debe ser >= 0 para productos")
    if not data.get("unidad_inventario"):
        raise HTTPException(status_code=400, detail="Unidad de inventario requerida para productos")
    if data.get("cantidad") is None or data["cantidad"] <= 0:
        raise HTTPException(status_code=400, detail="Cantidad requerida y debe ser mayor a 0 para productos")

def _validar_descripcion_unica(db: Session, descripcion: str, empresa_id: UUID, producto_id: Optional[UUID] = None):
    query = db.query(ProductoServicio).filter(
        ProductoServicio.descripcion == descripcion,
        ProductoServicio.empresa_id == empresa_id
    )
    if producto_id:
        query = query.filter(ProductoServicio.id != producto_id)
    
    if query.first():
        raise HTTPException(status_code=400, detail="Ya existe un producto o servicio con esa descripción para esta empresa")

def get_producto_by_id(db: Session, producto_id: UUID) -> Optional[ProductoServicio]:
    return db.query(ProductoServicio).filter(ProductoServicio.id == producto_id).first()

def get_all_productos(db: Session) -> List[ProductoServicio]:
    return db.query(ProductoServicio).all()

def create_producto(db: Session, payload: ProductoServicioCreate) -> ProductoServicio:
    data = payload.dict()
    _check_empresa_exists(db, data["empresa_id"])
    _validar_campos_sat(data["clave_producto"], data["clave_unidad"])
    _validar_descripcion_unica(db, data["descripcion"], data["empresa_id"])

    if data["tipo"] == "PRODUCTO":
        _validar_datos_producto(data)
    else:
        _limpiar_campos_inventario(data)

    nuevo_producto = ProductoServicio(**data)
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto

def update_producto(db: Session, producto_id: UUID, payload: ProductoServicioUpdate) -> Optional[ProductoServicio]:
    producto = get_producto_by_id(db, producto_id)
    if not producto:
        return None

    data = payload.dict(exclude_unset=True)

    if "empresa_id" in data:
        _check_empresa_exists(db, data["empresa_id"])
    
    if "descripcion" in data:
        _validar_descripcion_unica(db, data["descripcion"], data.get("empresa_id", producto.empresa_id), producto_id)

    if "clave_producto" in data or "clave_unidad" in data:
        clave_prod = data.get("clave_producto", producto.clave_producto)
        clave_uni = data.get("clave_unidad", producto.clave_unidad)
        _validar_campos_sat(clave_prod, clave_uni)

    tipo = data.get("tipo", producto.tipo)
    if tipo == "PRODUCTO":
        _validar_datos_producto(data)
    else:
        _limpiar_campos_inventario(data)

    for field, value in data.items():
        setattr(producto, field, value)

    db.commit()
    db.refresh(producto)
    return producto

def delete_producto(db: Session, producto_id: UUID) -> bool:
    producto = get_producto_by_id(db, producto_id)
    if not producto:
        return False
    
    db.delete(producto)
    db.commit()
    return True

def search_productos_by_term(db: Session, q: str, empresa_id: Optional[UUID] = None, limit: int = 20) -> List[ProductoServicio]:
    """
    Busca productos/servicios por un término `q` en la clave o descripción.
    Puede filtrar por empresa.
    """
    query = db.query(ProductoServicio)
    
    if empresa_id:
        query = query.filter(ProductoServicio.empresa_id == empresa_id)

    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(ProductoServicio.clave_producto).like(search_term),
                func.lower(ProductoServicio.descripcion).like(search_term)
            )
        )
        
    return query.limit(limit).all()

