# app/schemas/presupuestos.py

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from app.schemas.cliente import ClienteSimpleOut

# --- Enums and Literals ---

EstadoPresupuestoLiteral = Literal[
    "BORRADOR",
    "ENVIADO",
    "ACEPTADO",
    "RECHAZADO",
    "CADUCADO",
    "FACTURADO",
    "ARCHIVADO",
]

AccionPresupuestoLiteral = Literal[
    "CREADO",
    "EDITADO",
    "ENVIADO",
    "VISTO",
    "ACEPTADO",
    "RECHAZADO",
    "FACTURADO",
    "ARCHIVADO",
    "BORRADOR",
    "CADUCADO",
]

class StatusUpdatePayload(BaseModel):
    estado: EstadoPresupuestoLiteral

# --- Presupuesto Detalle ---

class PresupuestoDetalleBase(BaseModel):
    producto_servicio_id: Optional[UUID] = None
    descripcion: str
    cantidad: Decimal = Field(..., max_digits=18, decimal_places=2)
    unidad: Optional[str] = None
    precio_unitario: Decimal = Field(..., max_digits=18, decimal_places=2)
    tasa_impuesto: Decimal = Field(Decimal('0.08'), max_digits=10, decimal_places=4)
    costo_estimado: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)


class PresupuestoDetalleCreate(PresupuestoDetalleBase):
    pass


class PresupuestoDetalleUpdate(PresupuestoDetalleBase):
    pass


class PresupuestoDetalle(PresupuestoDetalleBase):
    id: UUID
    importe: Decimal = Field(..., max_digits=18, decimal_places=2)
    margen_estimado: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)

    class Config:
        from_attributes = True


# --- Presupuesto Adjunto ---


class PresupuestoAdjuntoBase(BaseModel):
    nombre: str
    tipo: Optional[str] = None


class PresupuestoAdjuntoCreate(PresupuestoAdjuntoBase):
    archivo: str  # Debería ser manejado como carga de archivo


class PresupuestoAdjunto(PresupuestoAdjuntoBase):
    id: UUID
    archivo: str  # URL al archivo
    fecha_subida: datetime

    class Config:
        from_attributes = True


# --- Presupuesto Evento ---


class PresupuestoEventoBase(BaseModel):
    accion: AccionPresupuestoLiteral
    comentario: Optional[str] = None


class PresupuestoEventoCreate(PresupuestoEventoBase):
    usuario_id: Optional[UUID] = None


class PresupuestoEvento(PresupuestoEventoBase):
    id: UUID
    usuario_id: Optional[UUID] = None
    fecha_evento: datetime

    class Config:
        from_attributes = True


# --- Presupuesto (Cabecera) ---


class PresupuestoBase(BaseModel):
    cliente_id: UUID
    empresa_id: UUID
    responsable_id: Optional[UUID] = None
    fecha_emision: date
    fecha_vencimiento: Optional[date] = None
    moneda: Literal["MXN", "USD"] = "MXN"
    tipo_cambio: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    condiciones_comerciales: Optional[str] = None
    notas_internas: Optional[str] = None
    firma_cliente: Optional[str] = None


class PresupuestoCreate(PresupuestoBase):
    folio: Optional[str] = None
    detalles: List[PresupuestoDetalleCreate]


class PresupuestoUpdate(BaseModel):
    cliente_id: Optional[UUID] = None
    responsable_id: Optional[UUID] = None
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    moneda: Optional[Literal["MXN", "USD"]] = None
    tipo_cambio: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    condiciones_comerciales: Optional[str] = None
    notas_internas: Optional[str] = None
    estado: Optional[EstadoPresupuestoLiteral] = None
    detalles: Optional[List[PresupuestoDetalleCreate]] = None


class PresupuestoSimpleOut(BaseModel):
    id: UUID
    folio: str
    version: int
    estado: str
    fecha_emision: date
    total: Decimal
    cliente: ClienteSimpleOut

    class Config:
        from_attributes = True


class PresupuestoPageOut(BaseModel):
    items: List[PresupuestoSimpleOut]
    total: int
    limit: int
    offset: int


class Presupuesto(PresupuestoBase):
    id: UUID
    folio: str
    version: int
    estado: str
    subtotal: Decimal
    descuento_total: Decimal
    impuestos: Decimal
    total: Decimal
    creado_en: datetime
    actualizado_en: datetime
    cliente: ClienteSimpleOut

    detalles: List[PresupuestoDetalle]
    adjuntos: List[PresupuestoAdjunto]
    eventos: List[PresupuestoEvento]

    class Config:
        from_attributes = True