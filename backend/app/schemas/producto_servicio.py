# app/schemas/producto_servicio.py

from pydantic import BaseModel, Field, condecimal
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

Numeric = condecimal(max_digits=18, decimal_places=2)

class ProductoServicioBase(BaseModel):
    tipo              : Literal['PRODUCTO','SERVICIO'] = Field(..., title="Tipo")
    clave_producto    : str     = Field(..., title="Clave de Producto/Servicio", description="Clave SAT 8 dígitos", max_length=8)
    clave_unidad      : str     = Field(..., title="Clave de Unidad", description="Clave SAT 8 dígitos", max_length=8)
    descripcion       : str     = Field(..., title="Descripción", max_length=1000)
    valor_unitario    : Numeric = Field(..., title="Valor Unitario", ge=0)
    empresa_id        : UUID    = Field(..., title="Empresa", description="ID de la empresa", example="123e4567-e89b-12d3-a456-426614174000")
    # Inventario (solo requeridos si tipo == PRODUCTO)
    cantidad          : Optional[Numeric] = Field(None, title="Cantidad", ge=0)
    stock_actual      : Optional[Numeric] = Field(None, title="Stock Actual", ge=0)
    stock_minimo      : Optional[Numeric] = Field(None, title="Stock Mínimo", ge=0)
    unidad_inventario : Optional[str]    = Field(None, title="Unidad de Inventario", max_length=8)
    ubicacion         : Optional[str]    = Field(None, title="Ubicación", max_length=255)
    requiere_lote     : bool             = Field(False, title="Requiere Lote", description="Si requiere lote para el inventario",)

class ProductoServicioCreate(ProductoServicioBase):
    pass

class ProductoServicioOut(ProductoServicioBase):
    id               : UUID     = Field(..., title="ID")
    creado_en        : datetime = Field(..., title="Creado en")
    actualizado_en   : datetime = Field(..., title="Actualizado en")

    class Config:
        orm_mode = True