# app/schemas/common.py

from pydantic import BaseModel
from uuid import UUID

class EmpresaSimpleOut(BaseModel):
    """Schema simple para representar una empresa en una relación."""
    id: UUID
    nombre_comercial: str

    class Config:
        orm_mode = True

class ClienteSimpleOut(BaseModel):
    """Schema simple para representar un cliente en una relación."""
    id: UUID
    nombre_comercial: str

    class Config:
        orm_mode = True
