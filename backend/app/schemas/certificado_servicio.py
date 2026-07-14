# app/schemas/certificado_servicio.py
from __future__ import annotations

import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

TipoCertificado = Literal["PLAGUICIDAS", "SANITIZACION"]


class CertificadoServicioBase(BaseModel):
    empresa_id: UUID
    cliente_id: Optional[UUID] = None
    tipo: TipoCertificado = "PLAGUICIDAS"
    fecha: datetime.date
    fecha_vencimiento: Optional[datetime.date] = None

    nombre_razon_social: str = Field(..., max_length=255)
    domicilio: Optional[str] = None
    telefono: Optional[str] = Field(None, max_length=50)
    actividad: Optional[str] = Field(None, max_length=255)

    areas: Optional[Dict[str, str]] = None
    plagas: Optional[Dict[str, str]] = None
    aplicaciones: Optional[Dict[str, str]] = None
    observaciones: Optional[str] = None
    gerente_nombre: Optional[str] = Field(None, max_length=255)


class CertificadoServicioCreate(CertificadoServicioBase):
    # Opcional: para arrancar/continuar la numeración existente en papel.
    # Si no se envía, se asigna el consecutivo automáticamente.
    folio: Optional[int] = Field(None, ge=1)


class CertificadoServicioUpdate(BaseModel):
    cliente_id: Optional[UUID] = None
    fecha: Optional[datetime.date] = None
    fecha_vencimiento: Optional[datetime.date] = None
    nombre_razon_social: Optional[str] = Field(None, max_length=255)
    domicilio: Optional[str] = None
    telefono: Optional[str] = Field(None, max_length=50)
    actividad: Optional[str] = Field(None, max_length=255)
    areas: Optional[Dict[str, str]] = None
    plagas: Optional[Dict[str, str]] = None
    aplicaciones: Optional[Dict[str, str]] = None
    observaciones: Optional[str] = None
    gerente_nombre: Optional[str] = Field(None, max_length=255)


class CertificadoServicioOut(CertificadoServicioBase):
    id: UUID
    folio: int
    creado_en: datetime.datetime

    model_config = {"from_attributes": True}


class CertificadoServicioPageOut(BaseModel):
    items: List[CertificadoServicioOut]
    total: int
    limit: int
    offset: int
