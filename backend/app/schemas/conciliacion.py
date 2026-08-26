# app/schemas/conciliacion.py
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.conciliacion import AREAS


class ComplementoPago(BaseModel):
    """Complemento que documenta el cobro de una factura PPD."""
    id: UUID
    folio: str                      # "P-857"
    fecha_pago: Optional[datetime.date] = None
    imp_pagado: Decimal


class FacturaEnlazada(BaseModel):
    """Factura que compone un movimiento, como se muestra en la pantalla."""
    id: UUID
    folio: str                      # "A-1585"
    total: Decimal
    fecha_emision: Optional[datetime.date] = None
    cliente_nombre: Optional[str] = None
    empresa_nombre: Optional[str] = None
    estatus: str
    metodo_pago: Optional[str] = None      # PUE | PPD
    # En una PPD el complemento es el documento que cuenta; en una PUE no existe
    complementos: List[ComplementoPago] = []

    model_config = {"from_attributes": True}


class EgresoEnlazado(BaseModel):
    """Gasto que compone un retiro."""
    id: UUID
    proveedor: Optional[str] = None
    descripcion: Optional[str] = None
    monto: Decimal
    fecha_egreso: Optional[datetime.date] = None
    categoria: Optional[str] = None
    empresa_nombre: Optional[str] = None
    # Ruta del comprobante, para poder verlo sin salir de la conciliación
    archivo_pdf: Optional[str] = None

    model_config = {"from_attributes": True}


class FacturaDeComplemento(BaseModel):
    """Factura cubierta por un complemento, con lo que se le aplicó."""
    id: UUID
    folio: str
    imp_pagado: Decimal


class Sugerencia(BaseModel):
    """Candidata que el sistema propone para un movimiento.

    Viene con su origen y su confianza porque no es lo mismo un folio escrito
    por el propio cliente que una coincidencia de monto entre cinco facturas.
    """
    tipo: str                    # "complemento" | "factura" | "egreso"
    id: UUID
    folio: str
    total: Decimal
    fecha: Optional[datetime.date] = None
    descripcion: Optional[str] = None
    empresa: Optional[str] = None
    origen: str
    confianza: str               # "alta" | "media" | "baja"
    # Comprobante del egreso; en las facturas el PDF se arma con el id
    archivo_pdf: Optional[str] = None


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
    egresos: List[EgresoEnlazado] = []
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
    # Para saber si el original se puede ver en pantalla (PDF) o sólo descargar
    archivo_nombre: Optional[str] = None
    creado_en: datetime.datetime

    model_config = {"from_attributes": True}


class ConciliacionDetalleOut(ConciliacionListOut):
    movimientos: List[MovimientoOut] = []


class EnlaceFacturas(BaseModel):
    """Facturas que se asignan a un movimiento. Reemplaza las que tuviera."""
    factura_ids: List[UUID] = Field(default_factory=list)


class EnlaceEgresos(BaseModel):
    """Gastos que se asignan a un retiro. Reemplaza los que tuviera."""
    egreso_ids: List[UUID] = Field(default_factory=list)


class AreaOut(BaseModel):
    clave: str
    nombre: str
