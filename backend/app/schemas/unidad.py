# app/schemas/unidad.py
from __future__ import annotations

import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime
from app.schemas.servicio_operativo import ServicioOperativoSimpleOut

TipoUnidad = Literal["SEDAN", "PICKUP", "CAMIONETA", "MOTOCICLETA", "VAN", "CAMION", "OTRO"]


# ─── Póliza de Seguro ─────────────────────────────────────────────────────────

class PolizaSeguroCreate(BaseModel):
    num_poliza: str = Field(..., max_length=60)
    compania: str = Field(..., max_length=100)
    fecha_expedicion: Optional[datetime.date] = None
    fecha_vencimiento: Optional[datetime.date] = None
    activo: bool = True


class PolizaSeguroUpdate(BaseModel):
    num_poliza: Optional[str] = Field(None, max_length=60)
    compania: Optional[str] = Field(None, max_length=100)
    fecha_expedicion: Optional[datetime.date] = None
    fecha_vencimiento: Optional[datetime.date] = None
    activo: Optional[bool] = None


class PolizaSeguroOut(BaseModel):
    id: UUID
    unidad_id: UUID
    num_poliza: str
    compania: str
    fecha_expedicion: Optional[datetime.date] = None
    fecha_vencimiento: Optional[datetime.date] = None
    activo: bool
    documento: Optional[str] = None
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime

    class Config:
        from_attributes = True


# ─── Unidad ───────────────────────────────────────────────────────────────────

class UnidadCreate(BaseModel):
    empresa_id: UUID
    nombre: str = Field(..., max_length=100)
    placa: Optional[str] = Field(None, max_length=20)
    tipo: TipoUnidad = "OTRO"
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: bool = True
    notas: Optional[str] = None
    servicios_ids: Optional[List[UUID]] = None

    # Nuevos campos vehículo
    numero_serie: Optional[str] = Field(None, max_length=50)
    marca: Optional[str] = Field(None, max_length=60)
    version: Optional[str] = Field(None, max_length=60)
    modelo_anio: Optional[int] = None
    capacidad_personas: Optional[int] = Field(None, ge=0)
    color: Optional[str] = Field(None, max_length=30)
    numero_motor: Optional[str] = Field(None, max_length=50)
    numero_economico: Optional[str] = Field(None, max_length=30)
    propietario: Optional[str] = Field(None, max_length=120)

    # Tarjeta de circulación
    tarjeta_circulacion: Optional[str] = Field(None, max_length=50)
    fecha_expedicion_tc: Optional[datetime.date] = None
    fecha_vencimiento_tc: Optional[datetime.date] = None


class UnidadUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    placa: Optional[str] = Field(None, max_length=20)
    tipo: Optional[TipoUnidad] = None
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None
    notas: Optional[str] = None
    servicios_ids: Optional[List[UUID]] = None

    # Nuevos campos vehículo
    numero_serie: Optional[str] = Field(None, max_length=50)
    marca: Optional[str] = Field(None, max_length=60)
    version: Optional[str] = Field(None, max_length=60)
    modelo_anio: Optional[int] = None
    capacidad_personas: Optional[int] = Field(None, ge=0)
    color: Optional[str] = Field(None, max_length=30)
    numero_motor: Optional[str] = Field(None, max_length=50)
    numero_economico: Optional[str] = Field(None, max_length=30)
    propietario: Optional[str] = Field(None, max_length=120)

    # Tarjeta de circulación
    tarjeta_circulacion: Optional[str] = Field(None, max_length=50)
    fecha_expedicion_tc: Optional[datetime.date] = None
    fecha_vencimiento_tc: Optional[datetime.date] = None


class UnidadOut(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    placa: Optional[str] = None
    tipo: str
    max_servicios_dia: Optional[int] = None
    activo: bool
    notas: Optional[str] = None

    # Nuevos campos vehículo
    numero_serie: Optional[str] = None
    marca: Optional[str] = None
    version: Optional[str] = None
    modelo_anio: Optional[int] = None
    capacidad_personas: Optional[int] = None
    color: Optional[str] = None
    numero_motor: Optional[str] = None
    numero_economico: Optional[str] = None
    propietario: Optional[str] = None
    foto_frontal: Optional[str] = None
    foto_lateral: Optional[str] = None
    foto_placa: Optional[str] = None

    # Tarjeta de circulación
    tarjeta_circulacion: Optional[str] = None
    fecha_expedicion_tc: Optional[datetime.date] = None
    fecha_vencimiento_tc: Optional[datetime.date] = None
    doc_tarjeta_circulacion: Optional[str] = None
    doc_comprobante_pago_tc: Optional[str] = None

    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime
    servicios_compatibles: List[ServicioOperativoSimpleOut] = []
    polizas_seguro: List[PolizaSeguroOut] = []

    class Config:
        from_attributes = True


class UnidadPageOut(BaseModel):
    items: List[UnidadOut]
    total: int
    limit: int
    offset: int
