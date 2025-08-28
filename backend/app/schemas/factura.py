# app/schemas/factura.py
from __future__ import annotations
from pydantic import BaseModel, Field, condecimal, constr, field_validator
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# --- Detalle ---

class FacturaDetalleIn(BaseModel):
    tipo                 : Optional[str] = Field(None, title="Tipo")
    producto_servicio_id : Optional[UUID] = Field(None, title="Producto/Servicio")
    clave_producto       : constr(max_length=20)
    clave_unidad         : constr(max_length=20)
    descripcion          : constr(max_length=300)
    requiere_lote        : Optional[bool] = Field(False, title="Requiere Lote")
    lote                 : Optional[str] = Field(None, title="Lote")

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

class FacturaDetalleOut(BaseModel):
    id                   : UUID
    tipo                 : Optional[str] = Field(None, title="Tipo")
    producto_servicio_id : Optional[UUID] = Field(None, title="Producto/Servicio")
    clave_producto       : constr(max_length=20)
    clave_unidad         : constr(max_length=20)
    descripcion          : constr(max_length=300)
    requiere_lote        : Optional[bool] = Field(False, title="Requiere Lote")
    lote                 : Optional[str] = Field(None, title="Lote")
    cantidad             : condecimal(ge=0, max_digits=18, decimal_places=6) = Decimal("1")
    valor_unitario       : condecimal(ge=0, max_digits=18, decimal_places=6) = Decimal("0")
    descuento            : condecimal(ge=0, max_digits=18, decimal_places=6) = Decimal("0")
    importe              : condecimal(ge=0, max_digits=18, decimal_places=6)

    # Impuestos
    iva_tasa             : Optional[condecimal(ge=0, le=1, max_digits=6, decimal_places=4)] = None
    iva_importe          : Optional[condecimal(ge=0, max_digits=18, decimal_places=6)] = None
    ret_iva_tasa         : Optional[condecimal(ge=0, le=1, max_digits=6, decimal_places=4)] = None
    ret_iva_importe      : Optional[condecimal(ge=0, max_digits=18, decimal_places=6)] = None
    ret_isr_tasa         : Optional[condecimal(ge=0, le=1, max_digits=6, decimal_places=4)] = None
    ret_isr_importe      : Optional[condecimal(ge=0, max_digits=18, decimal_places=6)] = None

    class Config:
        from_attributes = True

# --- Cabecera ---

class FacturaBase(BaseModel):
    serie               : Optional[constr(max_length=10)]  = None
    folio               : Optional[int]  = None

    empresa_id          : UUID
    cliente_id          : UUID

    tipo_comprobante    : Literal["I", "P"] = "I"
    forma_pago          : Optional[constr(max_length=3)] = None
    metodo_pago         : Optional[Literal["PUE", "PPD"]] = None
    uso_cfdi            : Optional[constr(max_length=3)] = None
    fecha_emision       : Optional[datetime] = None  # fecha y hora de emisión del CFDI
    moneda              : Literal["MXN", "USD"] = "MXN"
    tipo_cambio         : Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    lugar_expedicion    : Optional[constr(max_length=5)] = None
    condiciones_pago    : Optional[str] = None

    # Fechas de pago/cobro y status
    fecha_pago          : Optional[datetime] = None    # programado
    fecha_cobro         : Optional[datetime] = None    # real
    status_pago         : Literal["PAGADA", "NO_PAGADA"] = "NO_PAGADA"
    observaciones       : Optional[str] = None
    rfc_proveedor_sat   : Optional[constr(max_length=13)] = None

class FacturaCreate(FacturaBase):
    conceptos           : List[FacturaDetalleIn]

class FacturaUpdate(BaseModel):
    # Campos editables (opcionales)
    serie               : Optional[constr(max_length=10)]  = None
    folio               : Optional[int]  = None
    cliente_id          : Optional[UUID] = None
    forma_pago          : Optional[constr(max_length=3)] = None
    metodo_pago         : Optional[Literal["PUE", "PPD"]] = None
    uso_cfdi            : Optional[constr(max_length=3)] = None
    moneda              : Optional[Literal["MXN", "USD"]] = None
    tipo_cambio         : Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    lugar_expedicion    : Optional[constr(max_length=5)] = None
    condiciones_pago    : Optional[str] = None
    fecha_emision       : Optional[datetime] = None
    fecha_pago          : Optional[datetime] = None
    fecha_cobro         : Optional[datetime] = None
    status_pago         : Optional[Literal["PAGADA", "NO_PAGADA"]] = None
    conceptos           : Optional[List[FacturaDetalleIn]] = None  # si llega, se reemplazan
    observaciones       : Optional[str] = None
    rfc_proveedor_sat   : Optional[constr(max_length=13)] = None


class FacturaCancel(BaseModel):
    motivo_cancelacion: constr(max_length=2)
    folio_fiscal_sustituto: Optional[constr(max_length=36)] = None


class ClienteSimpleOut(BaseModel):
    id: UUID
    nombre_comercial: str

    class Config:
        from_attributes = True


class FacturaOut(FacturaBase):
    id                      : UUID
    estatus                 : Literal["BORRADOR", "TIMBRADA", "CANCELADA"]
    motivo_cancelacion      : Optional[str] = None
    folio_fiscal_sustituto  : Optional[str] = None
    cfdi_uuid               : Optional[str] = None
    fecha_timbrado          : Optional[datetime] = None
    no_certificado          : Optional[str] = None
    no_certificado_sat      : Optional[str] = None
    xml_path                : Optional[str] = None
    pdf_path                : Optional[str] = None
    fecha_emision           : Optional[datetime] = None
    rfc_proveedor_sat       : Optional[str] = None
    

    # Totales
    subtotal                : condecimal(ge=0, max_digits=18, decimal_places=6)
    descuento               : condecimal(ge=0, max_digits=18, decimal_places=6)
    impuestos_trasladados   : condecimal(ge=0, max_digits=18, decimal_places=6)
    impuestos_retenidos     : condecimal(ge=0, max_digits=18, decimal_places=6)
    total                   : condecimal(ge=0, max_digits=18, decimal_places=6)

    creado_en               : datetime
    actualizado_en          : datetime

    conceptos               : List[FacturaDetalleOut]
    cliente                 : Optional[ClienteSimpleOut] = None

    class Config:
        from_attributes = True