import uuid
from pydantic import BaseModel, condecimal
from typing import Optional
from datetime import date
from app.models.egreso import CategoriaEgreso, EstatusEgreso


class EgresoBase(BaseModel):
    descripcion: str
    monto: condecimal(gt=0, max_digits=18, decimal_places=2)
    moneda: str = "MXN"
    fecha_egreso: date
    categoria: CategoriaEgreso
    estatus: EstatusEgreso
    proveedor: Optional[str] = None
    path_documento: Optional[str] = None
    archivo_xml: Optional[str] = None
    archivo_pdf: Optional[str] = None
    metodo_pago: Optional[str] = None


class EgresoCreate(EgresoBase):
    empresa_id: uuid.UUID


class EgresoUpdate(BaseModel):
    descripcion: Optional[str] = None
    monto: Optional[condecimal(gt=0, max_digits=18, decimal_places=2)] = None
    moneda: Optional[str] = None
    fecha_egreso: Optional[date] = None
    categoria: Optional[CategoriaEgreso] = None
    estatus: Optional[EstatusEgreso] = None
    proveedor: Optional[str] = None
    path_documento: Optional[str] = None
    archivo_xml: Optional[str] = None
    archivo_pdf: Optional[str] = None
    metodo_pago: Optional[str] = None


class Egreso(EgresoBase):
    id: uuid.UUID
    empresa_id: uuid.UUID

    class Config:
        from_attributes = True
