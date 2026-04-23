# app/schemas/mantenimiento_unidad.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, condecimal

from app.utils.datetime_utils import TijuanaDatetime

TipoMantenimiento = Literal["PREVENTIVO", "CORRECTIVO"]


class MantenimientoCreate(BaseModel):
    tipo: TipoMantenimiento = "PREVENTIVO"
    fecha_realizado: date
    kilometraje_actual: Optional[int] = Field(None, ge=0)
    descripcion: Optional[str] = None
    costo: Optional[condecimal(ge=0, max_digits=12, decimal_places=2)] = None  # type: ignore[valid-type]
    proveedor: Optional[str] = Field(None, max_length=150)
    proxima_fecha: Optional[date] = None
    proximo_kilometraje: Optional[int] = Field(None, ge=0)


class MantenimientoUpdate(BaseModel):
    tipo: Optional[TipoMantenimiento] = None
    fecha_realizado: Optional[date] = None
    kilometraje_actual: Optional[int] = Field(None, ge=0)
    descripcion: Optional[str] = None
    costo: Optional[condecimal(ge=0, max_digits=12, decimal_places=2)] = None  # type: ignore[valid-type]
    proveedor: Optional[str] = Field(None, max_length=150)
    proxima_fecha: Optional[date] = None
    proximo_kilometraje: Optional[int] = Field(None, ge=0)


class MantenimientoOut(BaseModel):
    id: UUID
    unidad_id: UUID
    tipo: str
    fecha_realizado: date
    kilometraje_actual: Optional[int] = None
    descripcion: Optional[str] = None
    costo: Optional[Decimal] = None
    proveedor: Optional[str] = None
    proxima_fecha: Optional[date] = None
    proximo_kilometraje: Optional[int] = None
    creado_en: TijuanaDatetime

    class Config:
        from_attributes = True


class MantenimientoPageOut(BaseModel):
    items: List[MantenimientoOut]
    total: int
    limit: int
    offset: int
