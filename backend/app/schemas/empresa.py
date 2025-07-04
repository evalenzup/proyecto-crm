from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre: str
    nombre_comercial: Optional[str] = None       # ✅ NUEVO
    ruc: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    rfc: str
    regimen_fiscal: str
    codigo_postal: str
    contrasena: str
    archivo_cer: Optional[str] = None            # ✅ NUEVO
    archivo_key: Optional[str] = None            # ✅ NUEVO

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    nombre_comercial: Optional[str] = None       # ✅ NUEVO
    ruc: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    rfc: Optional[str] = None
    regimen_fiscal: Optional[str] = None
    codigo_postal: Optional[str] = None
    contrasena: Optional[str] = None
    archivo_cer: Optional[str] = None            # ✅ NUEVO
    archivo_key: Optional[str] = None            # ✅ NUEVO

class EmpresaOut(EmpresaBase):
    id: UUID
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        orm_mode = True
