# app/schemas/factura.py
from __future__ import annotations
from pydantic import BaseModel, Field, condecimal, constr, field_validator
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# --- Detalle ---

class FacturaDetalleIn(BaseModel):
    producto_servicio_id : Optional[UUID] = Field(None, title="Producto/Servicio")
    clave_producto       : constr(max_length=20)
    clave_unidad         : constr(max_length=20)
    descripcion          : constr(max_length=300)

    cantidad             : condecimal(ge=0, max_digits=18, decimal_places=6) = Decimal("1")
    valor_unitario       : condecimal(ge=0, max_digits=18, decimal_places=6) = Decimal("0")
    descuento            : condecimal(ge=0, max_digits=18, decimal_places=6) = Decimal("0")

    iva_tasa             : Optional[condecimal(ge=0, le=1, max_digits=6, decimal_places=4)] = None  # ej 0.1600
    ret_iva_tasa         : Optional[condecimal(ge=0, le=1, max_digits=6, decimal_places=4)] = None
    ret_isr_tasa         : Optional[condecimal(ge=0, le=1, max_digits=6, decimal_places=4)] = None

    @field_validator("descripcion")
    @classmethod
    def desc_trim(cls, v: str) -> str:
        return v.strip()

class FacturaDetalleOut(FacturaDetalleIn):
    id               : UUID
    # Importes calculados
    importe          : condecimal(ge=0, max_digits=18, decimal_places=6)
    iva_importe      : Optional[condecimal(ge=0, max_digits=18, decimal_places=6)] = None
    ret_iva_importe  : Optional[condecimal(ge=0, max_digits=18, decimal_places=6)] = None
    ret_isr_importe  : Optional[condecimal(ge=0, max_digits=18, decimal_places=6)] = None

    class Config:
        from_attributes = True

# --- Cabecera ---

class FacturaBase(BaseModel):
    serie               : Optional[constr(max_length=10)]  = None
    folio               : Optional[constr(max_length=20)]  = None

    empresa_id          : UUID
    cliente_id          : UUID

    tipo_comprobante    : Literal["I", "P"] = "I"
    forma_pago          : Optional[constr(max_length=3)] = None
    metodo_pago         : Optional[Literal["PUE", "PPD"]] = None
    uso_cfdi            : Optional[constr(max_length=3)] = None

    moneda              : Literal["MXN", "USD"] = "MXN"
    tipo_cambio         : Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    lugar_expedicion    : Optional[constr(max_length=5)] = None
    condiciones_pago    : Optional[str] = None

    # Fechas de pago/cobro y status
    fecha_pago          : Optional[datetime] = None    # programado
    fecha_cobro         : Optional[datetime] = None    # real
    status_pago         : Literal["PAGADA", "NO_PAGADA"] = "NO_PAGADA"

class FacturaCreate(FacturaBase):
    conceptos           : List[FacturaDetalleIn]

class FacturaUpdate(BaseModel):
    # Campos editables (opcionales)
    serie               : Optional[constr(max_length=10)]  = None
    folio               : Optional[constr(max_length=20)]  = None
    cliente_id          : Optional[UUID] = None
    forma_pago          : Optional[constr(max_length=3)] = None
    metodo_pago         : Optional[Literal["PUE", "PPD"]] = None
    uso_cfdi            : Optional[constr(max_length=3)] = None
    moneda              : Optional[Literal["MXN", "USD"]] = None
    tipo_cambio         : Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    lugar_expedicion    : Optional[constr(max_length=5)] = None
    condiciones_pago    : Optional[str] = None
    fecha_pago          : Optional[datetime] = None
    fecha_cobro         : Optional[datetime] = None
    status_pago         : Optional[Literal["PAGADA", "NO_PAGADA"]] = None
    conceptos           : Optional[List[FacturaDetalleIn]] = None  # si llega, se reemplazan

class FacturaOut(FacturaBase):
    id                      : UUID
    estatus                 : Literal["BORRADOR", "TIMBRADA", "CANCELADA"]
    cfdi_uuid               : Optional[str] = None
    fecha_timbrado          : Optional[datetime] = None
    no_certificado          : Optional[str] = None
    no_certificado_sat      : Optional[str] = None
    xml_path                : Optional[str] = None
    pdf_path                : Optional[str] = None

    # Totales
    subtotal                : condecimal(ge=0, max_digits=18, decimal_places=6)
    descuento               : condecimal(ge=0, max_digits=18, decimal_places=6)
    impuestos_trasladados   : condecimal(ge=0, max_digits=18, decimal_places=6)
    impuestos_retenidos     : condecimal(ge=0, max_digits=18, decimal_places=6)
    total                   : condecimal(ge=0, max_digits=18, decimal_places=6)

    creado_en               : datetime
    actualizado_en          : datetime

    conceptos               : List[FacturaDetalleOut]

    class Config:
        from_attributes = True