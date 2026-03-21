# app/schemas/auditoria.py
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from app.utils.datetime_utils import TijuanaDatetime


class AuditoriaLogOut(BaseModel):
    id: UUID
    empresa_id: Optional[UUID] = None
    usuario_id: Optional[UUID] = None
    usuario_email: Optional[str] = None
    accion: str
    entidad: str
    entidad_id: Optional[str] = None
    detalle: Optional[str] = None
    ip: Optional[str] = None
    creado_en: TijuanaDatetime

    model_config = {"from_attributes": True}


class AuditoriaPageOut(BaseModel):
    items: List[AuditoriaLogOut]
    total: int
    limit: int
    offset: int
