# app/schemas/servicio_operativo.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime


class ServicioOperativoSimpleOut(BaseModel):
    """Referencia compacta usada como nested en Tecnico y Unidad."""
    id: UUID
    nombre: str
    activo: bool

    class Config:
        from_attributes = True


class ServicioOperativoCreate(BaseModel):
    empresa_id: UUID
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = None
    duracion_estimada_min: Optional[int] = None
    duracion_variable: bool = False
    personal_requerido: int = Field(1, ge=1)
    requiere_vehiculo: bool = False
    servicio_padre_id: Optional[UUID] = None
    observaciones: Optional[str] = None
    activo: bool = True


class ServicioOperativoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=150)
    descripcion: Optional[str] = None
    duracion_estimada_min: Optional[int] = None
    duracion_variable: Optional[bool] = None
    personal_requerido: Optional[int] = Field(None, ge=1)
    requiere_vehiculo: Optional[bool] = None
    servicio_padre_id: Optional[UUID] = None
    observaciones: Optional[str] = None
    activo: Optional[bool] = None


class ServicioOperativoOut(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    descripcion: Optional[str] = None
    duracion_estimada_min: Optional[int] = None
    duracion_variable: bool
    personal_requerido: int
    requiere_vehiculo: bool
    servicio_padre_id: Optional[UUID] = None
    observaciones: Optional[str] = None
    activo: bool
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime
    servicio_padre: Optional[ServicioOperativoSimpleOut] = None

    class Config:
        from_attributes = True


class ServicioOperativoPageOut(BaseModel):
    items: List[ServicioOperativoOut]
    total: int
    limit: int
    offset: int
