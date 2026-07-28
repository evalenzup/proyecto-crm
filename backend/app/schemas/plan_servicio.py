# app/schemas/plan_servicio.py
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Periodicidad = Literal["QUINCENAL", "MENSUAL", "BIMESTRAL", "TRIMESTRAL"]

PERIODICIDAD_LABELS = {
    "QUINCENAL": "Quincenal",
    "MENSUAL": "Mensual",
    "BIMESTRAL": "Bimestral",
    "TRIMESTRAL": "Trimestral",
}

# Estatus de un periodo en el tablero.
EstatusPeriodo = Literal[
    "SIN_PROGRAMAR", "PROGRAMADA", "COMPLETADA", "CANCELADA"
]


class PlanServicioBase(BaseModel):
    empresa_id: UUID
    cliente_id: UUID
    servicio_id: Optional[UUID] = None
    tecnico_id: Optional[UUID] = None
    vigencia_desde: date
    vigencia_hasta: Optional[date] = None
    periodicidad: Periodicidad = "MENSUAL"
    dia_preferido: Optional[int] = Field(None, ge=1, le=31)
    precio_pactado: Optional[Decimal] = None
    certificado_id: Optional[UUID] = None
    notas: Optional[str] = None
    activo: bool = True

    @field_validator("vigencia_hasta")
    @classmethod
    def _hasta_despues_de_desde(cls, v, info):
        desde = info.data.get("vigencia_desde")
        if v and desde and v < desde:
            raise ValueError("La vigencia final no puede ser anterior a la inicial.")
        return v


class PlanServicioCreate(PlanServicioBase):
    pass


class PlanServicioUpdate(BaseModel):
    servicio_id: Optional[UUID] = None
    tecnico_id: Optional[UUID] = None
    vigencia_desde: Optional[date] = None
    vigencia_hasta: Optional[date] = None
    periodicidad: Optional[Periodicidad] = None
    dia_preferido: Optional[int] = Field(None, ge=1, le=31)
    precio_pactado: Optional[Decimal] = None
    certificado_id: Optional[UUID] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class PlanServicioOut(PlanServicioBase):
    id: UUID
    creado_en: datetime
    actualizado_en: datetime
    # Campos denormalizados para la UI (evita N+1 en el frontend).
    cliente_nombre: Optional[str] = None
    servicio_nombre: Optional[str] = None
    tecnico_nombre: Optional[str] = None
    certificado_folio: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Tablero ──────────────────────────────────────────────────────────────────
class PeriodoTablero(BaseModel):
    """Un periodo esperado del plan dentro del mes consultado."""
    fecha_tentativa: date
    estatus: EstatusPeriodo
    orden_id: Optional[UUID] = None
    orden_folio: Optional[str] = None
    orden_estado: Optional[str] = None


class PlanTableroRow(BaseModel):
    plan_id: UUID
    cliente_id: UUID
    cliente_nombre: str
    servicio_nombre: Optional[str] = None
    tecnico_nombre: Optional[str] = None
    periodicidad: Periodicidad
    precio_pactado: Optional[Decimal] = None
    por_vencer: bool = False  # vigencia termina en ≤30 días
    vigencia_hasta: Optional[date] = None
    periodos: List[PeriodoTablero]


class TableroOut(BaseModel):
    anio: int
    mes: int
    planes: List[PlanTableroRow]


class ProgramarRequest(BaseModel):
    """Crear una orden a partir de un periodo del plan."""
    fecha: date
    hora_inicio: Optional[str] = None  # "HH:MM"
    tecnico_id: Optional[UUID] = None
