# app/schemas/contrato.py
from __future__ import annotations

from datetime import date
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime


class ContratoBase(BaseModel):
    empresa_id: UUID = Field(..., title="Empresa (prestador)")
    cliente_id: UUID = Field(..., title="Cliente")
    presupuesto_id: Optional[UUID] = Field(None, title="Presupuesto de origen")
    numero_contrato: Optional[str] = Field(None, max_length=40)
    fecha_contrato: Optional[date] = None
    vigencia_desde: Optional[date] = None
    vigencia_hasta: Optional[date] = None
    certificado_folio: Optional[str] = Field(None, max_length=40)
    # valores manuales keyed por placeholder de la plantilla de la empresa
    datos: Optional[dict] = None
    # lista de tecnico_ids
    personal_asignado: Optional[List[UUID]] = None
    exclusiones: Optional[str] = None
    notas: Optional[str] = None


class ContratoCreate(ContratoBase):
    pass


class ContratoUpdate(BaseModel):
    numero_contrato: Optional[str] = Field(None, max_length=40)
    fecha_contrato: Optional[date] = None
    vigencia_desde: Optional[date] = None
    vigencia_hasta: Optional[date] = None
    certificado_folio: Optional[str] = Field(None, max_length=40)
    datos: Optional[dict] = None
    personal_asignado: Optional[List[UUID]] = None
    exclusiones: Optional[str] = None
    notas: Optional[str] = None


class ContratoOut(ContratoBase):
    id: UUID
    estado: str
    archivo_docx: Optional[str] = None
    archivo_pdf: Optional[str] = None
    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime

    class Config:
        from_attributes = True
