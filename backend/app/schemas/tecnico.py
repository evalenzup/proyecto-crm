# app/schemas/tecnico.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime
from app.schemas.servicio_operativo import ServicioOperativoSimpleOut


class TecnicoCreate(BaseModel):
    empresa_id: UUID
    nombre_completo: str = Field(..., max_length=200)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: bool = True
    notas: Optional[str] = None
    especialidades_ids: Optional[List[UUID]] = None


class TecnicoUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None
    notas: Optional[str] = None
    especialidades_ids: Optional[List[UUID]] = None


class TecnicoOut(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre_completo: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    max_servicios_dia: Optional[int] = None
    activo: bool
    notas: Optional[str] = None
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime
    especialidades: List[ServicioOperativoSimpleOut] = []

    class Config:
        from_attributes = True


class TecnicoPageOut(BaseModel):
    items: List[TecnicoOut]
    total: int
    limit: int
    offset: int
