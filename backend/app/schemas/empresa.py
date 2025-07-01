from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre: str
    ruc: str
    direccion: Optional[str]
    telefono: Optional[str]
    email: Optional[EmailStr]
    rfc: str
    regimen_fiscal: str
    codigo_postal: str

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nombre: Optional[str]
    ruc: Optional[str]
    direccion: Optional[str]
    telefono: Optional[str]
    email: Optional[EmailStr]
    rfc: Optional[str]
    regimen_fiscal: Optional[str]
    codigo_postal: Optional[str]

class EmpresaOut(EmpresaBase):
    id: UUID
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        orm_mode = True
