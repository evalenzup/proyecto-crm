# app/schemas/equipo.py
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime

TipoDato = Literal["TEXTO", "NUMERO", "FECHA", "BOOLEANO", "LISTA"]


# ---------------------------------------------------------------------------
# TipoEquipoCampo (campos personalizados de un tipo)
# ---------------------------------------------------------------------------
class TipoEquipoCampoBase(BaseModel):
    etiqueta: str = Field(..., max_length=100)
    clave: str = Field(..., max_length=60)
    tipo_dato: TipoDato = "TEXTO"
    opciones: Optional[List[str]] = None
    requerido: bool = False
    orden: int = 0


class TipoEquipoCampoCreate(TipoEquipoCampoBase):
    pass


class TipoEquipoCampoOut(TipoEquipoCampoBase):
    id: UUID
    tipo_equipo_id: UUID

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# TipoEquipo
# ---------------------------------------------------------------------------
class TipoEquipoCreate(BaseModel):
    empresa_id: UUID
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    orden: int = 0
    activo: bool = True
    campos: List[TipoEquipoCampoCreate] = []


class TipoEquipoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None
    # Si se envía, reemplaza el set completo de campos del tipo
    campos: Optional[List[TipoEquipoCampoCreate]] = None


class TipoEquipoOut(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    descripcion: Optional[str] = None
    orden: int
    activo: bool
    campos: List[TipoEquipoCampoOut] = []
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# EstadoEquipo
# ---------------------------------------------------------------------------
class EstadoEquipoCreate(BaseModel):
    empresa_id: UUID
    nombre: str = Field(..., max_length=60)
    orden: int = 0
    activo: bool = True


class EstadoEquipoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=60)
    orden: Optional[int] = None
    activo: Optional[bool] = None


class EstadoEquipoOut(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    orden: int
    activo: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# EquipoControl
# ---------------------------------------------------------------------------
class EquipoControlCreate(BaseModel):
    empresa_id: UUID
    cliente_id: UUID
    tipo_equipo_id: UUID
    estado_id: Optional[UUID] = None
    identificador: Optional[str] = Field(None, max_length=60)
    area: Optional[str] = Field(None, max_length=150)
    fecha_instalacion: Optional[datetime.date] = None
    notas: Optional[str] = None
    activo: bool = True
    valores: Optional[Dict[str, Any]] = None


class EquipoControlUpdate(BaseModel):
    tipo_equipo_id: Optional[UUID] = None
    estado_id: Optional[UUID] = None
    identificador: Optional[str] = Field(None, max_length=60)
    area: Optional[str] = Field(None, max_length=150)
    fecha_instalacion: Optional[datetime.date] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None
    valores: Optional[Dict[str, Any]] = None


class EquipoControlOut(BaseModel):
    id: UUID
    empresa_id: UUID
    cliente_id: UUID
    tipo_equipo_id: UUID
    tipo_equipo_nombre: Optional[str] = None
    estado_id: Optional[UUID] = None
    estado_nombre: Optional[str] = None
    identificador: Optional[str] = None
    area: Optional[str] = None
    fecha_instalacion: Optional[datetime.date] = None
    notas: Optional[str] = None
    activo: bool
    valores: Optional[Dict[str, Any]] = None
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime

    class Config:
        from_attributes = True


class EquipoControlPageOut(BaseModel):
    items: List[EquipoControlOut]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Alta masiva (crear N equipos numerados en un área)
# ---------------------------------------------------------------------------
class EquipoControlBulkCreate(BaseModel):
    empresa_id: UUID
    cliente_id: UUID
    tipo_equipo_id: UUID
    estado_id: Optional[UUID] = None
    area: Optional[str] = Field(None, max_length=150)
    fecha_instalacion: Optional[datetime.date] = None
    cantidad: int = Field(..., ge=1, le=500)
    # Identificador: prefijo + numeración consecutiva (ej. "C-" -> C-1, C-2…)
    prefijo: Optional[str] = Field(None, max_length=40)
    numero_inicial: int = Field(1, ge=0)
    relleno_ceros: int = Field(0, ge=0, le=6)  # zero-pad del número (0 = sin relleno)
    valores: Optional[Dict[str, Any]] = None
