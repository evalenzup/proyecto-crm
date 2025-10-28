import uuid
from pydantic import BaseModel, Field, condecimal, constr, field_validator
from typing import List, Optional, Any
from datetime import datetime
from app.models.pago import EstatusPago
from app.schemas.factura import FacturaSimpleOut
from app.schemas.cliente import ClienteSimpleOut

# --- Documento Relacionado ---


class PagoDocumentoRelacionadoBase(BaseModel):
    factura_id: uuid.UUID
    num_parcialidad: int = Field(..., gt=0)
    imp_saldo_ant: condecimal(ge=0, max_digits=18, decimal_places=2)
    imp_pagado: condecimal(gt=0, max_digits=18, decimal_places=2)
    imp_saldo_insoluto: condecimal(ge=0, max_digits=18, decimal_places=2)


class PagoDocumentoRelacionadoCreate(PagoDocumentoRelacionadoBase):
    pass


class PagoDocumentoRelacionado(PagoDocumentoRelacionadoBase):
    id: uuid.UUID
    pago_id: uuid.UUID
    id_documento: str  # UUID de la factura
    serie: Optional[str] = None
    folio: Optional[str] = None
    moneda_dr: str
    tipo_cambio_dr: Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    factura: Optional[FacturaSimpleOut] = None

    class Config:
        from_attributes = True


# --- Pago ---


class PagoBase(BaseModel):
    cliente_id: uuid.UUID
    fecha_pago: datetime
    forma_pago_p: constr(max_length=2)
    moneda_p: constr(max_length=3)
    monto: condecimal(gt=0, max_digits=18, decimal_places=2)
    tipo_cambio_p: Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    serie: Optional[constr(max_length=25)] = None
    folio: Optional[constr(max_length=40)] = None

    @field_validator("folio", mode="before")
    @classmethod
    def folio_to_string(cls, v: Any) -> str:
        if isinstance(v, int):
            return str(v)
        return v

    @field_validator("forma_pago_p", mode="before")
    @classmethod
    def forma_pago_pad_left_zero(cls, v: Any) -> Any:
        """Normaliza la forma de pago a 2 dígitos (e.g., '3' -> '03')."""
        if v is None:
            return v
        try:
            s = str(v).strip()
            if s.isdigit():
                return f"{int(s):02d}"
            return s
        except Exception:
            return v


class PagoCreate(PagoBase):
    empresa_id: uuid.UUID
    documentos: List[PagoDocumentoRelacionadoCreate]


class PagoUpdate(BaseModel):
    fecha_pago: Optional[datetime] = None
    forma_pago_p: Optional[constr(max_length=2)] = None
    moneda_p: Optional[constr(max_length=3)] = None
    monto: Optional[condecimal(gt=0, max_digits=18, decimal_places=2)] = None
    tipo_cambio_p: Optional[condecimal(gt=0, max_digits=18, decimal_places=6)] = None
    documentos: Optional[List[PagoDocumentoRelacionadoCreate]] = None

    @field_validator("forma_pago_p", mode="before")
    @classmethod
    def forma_pago_pad_left_zero_update(cls, v: Any) -> Any:
        if v is None:
            return v
        try:
            s = str(v).strip()
            if s.isdigit():
                return f"{int(s):02d}"
            return s
        except Exception:
            return v


class Pago(PagoBase):
    id: uuid.UUID
    empresa_id: uuid.UUID
    estatus: EstatusPago
    uuid: Optional[str] = None
    fecha_timbrado: Optional[datetime] = None
    creado_en: datetime
    actualizado_en: datetime
    documentos_relacionados: List[PagoDocumentoRelacionado] = []
    cliente: Optional[ClienteSimpleOut] = None

    motivo_cancelacion: Optional[constr(max_length=2)] = None
    folio_fiscal_sustituto: Optional[constr(max_length=36)] = None
    no_certificado: Optional[constr(max_length=20)] = None
    no_certificado_sat: Optional[constr(max_length=20)] = None
    sello_cfdi: Optional[str] = None
    sello_sat: Optional[str] = None
    rfc_proveedor_sat: Optional[constr(max_length=13)] = None

    class Config:
        from_attributes = True


class PagoOut(Pago):
    pass


class PagoListResponse(BaseModel):
    items: List[Pago]
    total: int
    limit: int
    offset: int
