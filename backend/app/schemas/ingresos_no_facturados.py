# app/schemas/ingresos_no_facturados.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class IngresoNoFacturadoRow(BaseModel):
    orden_id: UUID
    folio_os: str
    fecha_programada: date
    cliente_id: UUID
    cliente_nombre: str
    estado: str
    precio_acordado: Optional[Decimal] = None
    cobrado: bool
    fecha_cobro: Optional[date] = None
    forma_cobro: Optional[str] = None


class IngresosResumen(BaseModel):
    total_no_facturado: Decimal
    total_cobrado: Decimal
    total_pendiente: Decimal
    num_ordenes: int
    num_cobradas: int


class IngresosNoFacturadosOut(BaseModel):
    resumen: IngresosResumen
    items: List[IngresoNoFacturadoRow]


class MarcarCobroIn(BaseModel):
    cobrado: bool
    fecha_cobro: Optional[date] = None
    forma_cobro: Optional[str] = None
