# app/schemas/orden_servicio.py

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import UUID
from datetime import date, datetime, time
from decimal import Decimal

# ── Literales ────────────────────────────────────────────────────────────────

EstadoOSLiteral = Literal[
    "PENDIENTE",
    "ASIGNADO",
    "EN_CAMINO",
    "EN_PROGRESO",
    "COMPLETADO",
    "CANCELADO",
    "REAGENDADO",
]

PrioridadOSLiteral = Literal["BAJA", "MEDIA", "ALTA", "URGENTE"]


# ── Schemas de entrada ────────────────────────────────────────────────────────

class OrdenServicioCreate(BaseModel):
    cliente_id: UUID
    tecnico_id: Optional[UUID] = None
    unidad_id: Optional[UUID] = None
    servicio_id: Optional[UUID] = None
    presupuesto_id: Optional[UUID] = None

    fecha_programada: date
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    duracion_minutos: Optional[int] = None

    estado: EstadoOSLiteral = "PENDIENTE"
    prioridad: PrioridadOSLiteral = "MEDIA"

    direccion_servicio: Optional[str] = None
    latitud: Optional[Decimal] = Field(None, max_digits=10, decimal_places=7)
    longitud: Optional[Decimal] = Field(None, max_digits=10, decimal_places=7)

    precio_acordado: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)

    notas_tecnico: Optional[str] = None
    notas_internas: Optional[str] = None
    notas_cierre: Optional[str] = None


class OrdenServicioUpdate(BaseModel):
    tecnico_id: Optional[UUID] = None
    unidad_id: Optional[UUID] = None
    servicio_id: Optional[UUID] = None
    presupuesto_id: Optional[UUID] = None

    fecha_programada: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    duracion_minutos: Optional[int] = None

    estado: Optional[EstadoOSLiteral] = None
    prioridad: Optional[PrioridadOSLiteral] = None

    direccion_servicio: Optional[str] = None
    latitud: Optional[Decimal] = Field(None, max_digits=10, decimal_places=7)
    longitud: Optional[Decimal] = Field(None, max_digits=10, decimal_places=7)

    precio_acordado: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)

    notas_tecnico: Optional[str] = None
    notas_internas: Optional[str] = None
    notas_cierre: Optional[str] = None


class CambioEstadoOS(BaseModel):
    estado: EstadoOSLiteral
    notas: Optional[str] = None


# ── Schemas de salida ─────────────────────────────────────────────────────────

class ClienteSimpleOut(BaseModel):
    id: UUID
    nombre_comercial: str
    telefono: Optional[str] = None

    model_config = {"from_attributes": True}


class TecnicoSimpleOut(BaseModel):
    id: UUID
    nombre_completo: str

    model_config = {"from_attributes": True}


class UnidadSimpleOut(BaseModel):
    id: UUID
    nombre: str
    placas: Optional[str] = None

    model_config = {"from_attributes": True}


class ServicioSimpleOut(BaseModel):
    id: UUID
    nombre: str

    model_config = {"from_attributes": True}


class HistorialEstadoOSOut(BaseModel):
    id: UUID
    estado_anterior: Optional[str]
    estado_nuevo: str
    notas: Optional[str]
    creado_en: datetime
    usuario_nombre: Optional[str] = None

    model_config = {"from_attributes": True}


class OrdenServicioOut(BaseModel):
    id: UUID
    empresa_id: UUID
    folio_os: str

    cliente_id: UUID
    tecnico_id: Optional[UUID]
    unidad_id: Optional[UUID]
    servicio_id: Optional[UUID]
    presupuesto_id: Optional[UUID]

    fecha_programada: date
    hora_inicio: Optional[time]
    hora_fin: Optional[time]
    duracion_minutos: Optional[int]

    estado: str
    prioridad: str

    direccion_servicio: Optional[str]
    latitud: Optional[Decimal]
    longitud: Optional[Decimal]

    precio_acordado: Optional[Decimal]

    notas_tecnico: Optional[str]
    notas_internas: Optional[str]
    notas_cierre: Optional[str]

    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    # Objetos relacionados (cargados por selectin)
    cliente: Optional[ClienteSimpleOut] = None
    tecnico: Optional[TecnicoSimpleOut] = None
    unidad: Optional[UnidadSimpleOut] = None
    servicio: Optional[ServicioSimpleOut] = None
    historial: List[HistorialEstadoOSOut] = []

    model_config = {"from_attributes": True}


class OrdenServicioListOut(BaseModel):
    """Versión reducida para listados y calendario."""
    id: UUID
    folio_os: str
    fecha_programada: date
    hora_inicio: Optional[time]
    hora_fin: Optional[time]
    estado: str
    prioridad: str
    cliente_nombre: Optional[str] = None
    tecnico_nombre: Optional[str] = None
    direccion_servicio: Optional[str]
    precio_acordado: Optional[Decimal]
    notas_tecnico: Optional[str] = None

    model_config = {"from_attributes": True}
