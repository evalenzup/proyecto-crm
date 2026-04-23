# app/schemas/unidad.py
from __future__ import annotations

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime
from app.schemas.servicio_operativo import ServicioOperativoSimpleOut

TipoUnidad = Literal["SEDAN", "PICKUP", "CAMIONETA", "MOTOCICLETA", "OTRO"]


class UnidadCreate(BaseModel):
    empresa_id: UUID
    nombre: str = Field(..., max_length=100)
    placa: Optional[str] = Field(None, max_length=20)
    tipo: TipoUnidad = "OTRO"
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: bool = True
    notas: Optional[str] = None
    servicios_ids: Optional[List[UUID]] = None


class UnidadUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    placa: Optional[str] = Field(None, max_length=20)
    tipo: Optional[TipoUnidad] = None
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None
    notas: Optional[str] = None
    servicios_ids: Optional[List[UUID]] = None


class UnidadOut(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    placa: Optional[str] = None
    tipo: str
    max_servicios_dia: Optional[int] = None
    activo: bool
    notas: Optional[str] = None
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime
    servicios_compatibles: List[ServicioOperativoSimpleOut] = []

    class Config:
        from_attributes = True


class UnidadPageOut(BaseModel):
    items: List[UnidadOut]
    total: int
    limit: int
    offset: int
