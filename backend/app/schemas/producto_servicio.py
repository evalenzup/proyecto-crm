# app/schemas/producto_servicio.py

from pydantic import BaseModel, Field, condecimal, constr
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

Numeric = condecimal(max_digits=18, decimal_places=2)

class ProductoServicioBase(BaseModel):
    tipo              : Literal['PRODUCTO', 'SERVICIO']  = Field(..., title="Tipo")
    clave_producto    : constr(max_length=8)             = Field(..., title="Clave de Producto/Servicio", description="Clave SAT 8 dígitos")
    clave_unidad      : constr(max_length=8)             = Field(..., title="Clave de Unidad", description="Clave SAT 8 dígitos")
    descripcion       : constr(max_length=1000)          = Field(..., title="Descripción")
    valor_unitario    : Numeric                          = Field(..., title="Valor Unitario", ge=0)  # type: ignore
    empresa_id        : UUID                             = Field(..., title="Empresa", description="ID de la empresa", example="123e4567-e89b-12d3-a456-426614174000")

    # Inventario (solo requeridos si tipo == PRODUCTO)
    cantidad          : Optional[Numeric]                = Field(None, title="Cantidad", ge=0)         # type: ignore
    stock_actual      : Optional[Numeric]                = Field(None, title="Stock Actual", ge=0)     # type: ignore
    stock_minimo      : Optional[Numeric]                = Field(None, title="Stock Mínimo", ge=0)     # type: ignore
    unidad_inventario : Optional[constr(max_length=8)]   = Field(None, title="Unidad de Inventario")
    ubicacion         : Optional[constr(max_length=255)] = Field(None, title="Ubicación")
    requiere_lote     : bool                             = Field(False, title="Requiere Lote", description="Si requiere lote para el inventario")

class ProductoServicioCreate(ProductoServicioBase):
    pass

class ProductoServicioOut(ProductoServicioBase):
    id             : UUID     = Field(..., title="ID")
    creado_en      : datetime = Field(..., title="Creado en")
    actualizado_en : datetime = Field(..., title="Actualizado en")

    class Config:
        orm_mode = True

class ProductoServicioUpdate(BaseModel):
    tipo              : Optional[Literal['PRODUCTO', 'SERVICIO']] = Field(None, title="Tipo")
    clave_producto    : Optional[constr(max_length=8)]            = Field(None, title="Clave de Producto/Servicio")
    clave_unidad      : Optional[constr(max_length=8)]            = Field(None, title="Clave de Unidad")
    descripcion       : Optional[constr(max_length=1000)]         = Field(None, title="Descripción")
    valor_unitario    : Optional[Numeric]                         = Field(None, title="Valor Unitario", ge=0)  # type: ignore
    empresa_id        : Optional[UUID]                            = Field(None, title="Empresa")
    cantidad          : Optional[Numeric]                         = Field(None, title="Cantidad", ge=0) # type: ignore
    stock_actual      : Optional[Numeric]                         = Field(None, title="Stock Actual", ge=0) # type: ignore
    stock_minimo      : Optional[Numeric]                         = Field(None, title="Stock Mínimo", ge=0) # type: ignore
    unidad_inventario : Optional[constr(max_length=8)]            = Field(None, title="Unidad de Inventario")
    ubicacion         : Optional[constr(max_length=255)]          = Field(None, title="Ubicación")
    requiere_lote     : Optional[bool]                            = Field(None, title="Requiere Lote")
