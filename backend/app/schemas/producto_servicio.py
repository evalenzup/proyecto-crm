# app/schemas/producto_servicio.py

from pydantic import BaseModel, Field, condecimal
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

Numeric = condecimal(max_digits=18, decimal_places=2)

class ProductoServicioBase(BaseModel):
    tipo              : Literal['PRODUCTO','SERVICIO'] = Field(..., title="Tipo")
    clave_producto    : str     = Field(..., title="Clave de Producto/Servicio")
    clave_unidad      : str     = Field(..., title="Clave de Unidad")
    descripcion       : str     = Field(..., title="Descripción")
    cantidad          : Numeric = Field(..., title="Cantidad")
    valor_unitario    : Numeric = Field(..., title="Valor Unitario")
    empresa_id        : UUID    = Field(..., title="Empresa")
    # Inventario (solo requeridos si tipo == PRODUCTO)
    stock_actual      : Optional[Numeric] = Field(None, title="Stock Actual")
    stock_minimo      : Optional[Numeric] = Field(None, title="Stock Mínimo")
    unidad_inventario : Optional[str]    = Field(None, title="Unidad de Inventario")
    ubicacion         : Optional[str]    = Field(None, title="Ubicación")
    requiere_lote     : bool             = Field(False, title="Requiere Lote")

class ProductoServicioCreate(ProductoServicioBase):
    pass

class ProductoServicioOut(ProductoServicioBase):
    id               : UUID     = Field(..., title="ID")
    creado_en        : datetime = Field(..., title="Creado en")
    actualizado_en   : datetime = Field(..., title="Actualizado en")

    class Config:
        orm_mode = True