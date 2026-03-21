from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID
from app.utils.datetime_utils import TijuanaDatetime


class NotificacionOut(BaseModel):
    id: UUID
    empresa_id: UUID
    usuario_id: Optional[UUID]
    tipo: str
    titulo: str
    mensaje: str
    leida: bool
    metadata_: Optional[Dict[str, Any]] = None
    creada_en: TijuanaDatetime

    class Config:
        orm_mode = True
        fields = {"metadata_": "metadata"}


class NotificacionListResponse(BaseModel):
    items: List[NotificacionOut]
    total: int
    no_leidas: int
