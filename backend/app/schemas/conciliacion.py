# app/schemas/conciliacion.py
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.conciliacion import AREAS


class FacturaEnlazada(BaseModel):
    """Factura que compone un movimiento, como se muestra en la pantalla."""
    id: UUID
    folio: str                      # "A-1585"
    total: Decimal
    fecha_emision: Optional[datetime.date] = None
    cliente_nombre: Optional[str] = None
    empresa_nombre: Optional[str] = None
    estatus: str

    model_config = {"from_attributes": True}


class MovimientoOut(BaseModel):
    id: UUID
    orden: int
    fecha: datetime.date
    concepto: str
    deposito: Optional[Decimal] = None
    retiro: Optional[Decimal] = None
    comentario: Optional[str] = None
    area: Optional[str] = None
    conciliado: bool
    facturas: List[FacturaEnlazada] = []
    # Suma de las facturas enlazadas; la pantalla la compara contra el importe
    # pero no impide guardar si difiere: a veces la diferencia es real.
    suma_facturas: Decimal = Decimal("0")

    model_config = {"from_attributes": True}


class MovimientoUpdate(BaseModel):
    comentario: Optional[str] = None
    area: Optional[str] = None
    conciliado: Optional[bool] = None

    @field_validator("area")
    @classmethod
    def validar_area(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        claves = [p.strip().upper() for p in v.split(",") if p.strip()]
        malas = [c for c in claves if c not in AREAS]
        if malas:
            raise ValueError(
                f"Área no reconocida: {', '.join(malas)}. "
                f"Válidas: {', '.join(f'{k} ({n})' for k, n in AREAS.items())}"
            )
        # Se normaliza el orden para que "F,A" y "A,F" queden iguales
        return ",".join(sorted(set(claves)))


class ConciliacionListOut(BaseModel):
    id: UUID
    periodo_inicio: datetime.date
    periodo_fin: datetime.date
    banco: str
    cuenta: Optional[str] = None
    estado: str
    saldo_inicial: Decimal
    saldo_final: Decimal
    total_depositos: Decimal
    total_retiros: Decimal
    n_depositos: int
    n_retiros: int
    total_movimientos: int = 0
    conciliados: int = 0
    tiene_archivo: bool = False
    creado_en: datetime.datetime

    model_config = {"from_attributes": True}


class ConciliacionDetalleOut(ConciliacionListOut):
    movimientos: List[MovimientoOut] = []


class EnlaceFacturas(BaseModel):
    """Facturas que se asignan a un movimiento. Reemplaza las que tuviera."""
    factura_ids: List[UUID] = Field(default_factory=list)


class AreaOut(BaseModel):
    clave: str
    nombre: str
