from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

# --- Schemas para Notas de Cobranza ---

class CobranzaNotaBase(BaseModel):
    nota: str
    fecha_promesa_pago: Optional[datetime] = None
    factura_id: Optional[UUID] = None

class CobranzaNotaCreate(CobranzaNotaBase):
    cliente_id: UUID

class CobranzaNotaOut(CobranzaNotaBase):
    id: UUID
    empresa_id: UUID
    cliente_id: UUID
    creado_po: Optional[UUID]
    creado_en: datetime
    nombre_creador: Optional[str] = None # Para mostrar quién creó la nota

    class Config:
        orm_mode = True

# --- Schemas para Reporte de Antigüedad (Aging) ---

class AgingBucket(BaseModel):
    rango: str # "0-30", "31-60", "61-90", "90+"
    monto: float
    cantidad_facturas: int

class ClienteAging(BaseModel):
    cliente_id: UUID
    nombre_cliente: str
    rfc: Optional[str]
    total_deuda: float
    por_vencer: float # No vencido aún
    vencido_0_30: float
    vencido_31_60: float
    vencido_61_90: float
    vencido_mas_90: float
    
    # Detalle opcional
    nota_mas_reciente: Optional[str] = None
    fecha_promesa: Optional[datetime] = None
    email: Optional[str] = None

class AgingReportResponse(BaseModel):
    total_general_vencido: float
    items: List[ClienteAging]

class CobranzaEmailRequest(BaseModel):
    cliente_id: UUID
    recipients: List[str]
