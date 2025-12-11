# app/schemas/usuario.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from enum import Enum

class RolUsuario(str, Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"

# Shared properties
class UsuarioBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    nombre_completo: Optional[str] = None
    rol: RolUsuario = RolUsuario.SUPERVISOR
    empresa_id: Optional[UUID] = None

# Properties to receive via API on creation
class UsuarioCreate(UsuarioBase):
    email: EmailStr
    password: str

# Properties to receive via API on update
class UsuarioUpdate(UsuarioBase):
    password: Optional[str] = None

class UsuarioInDBBase(UsuarioBase):
    id: UUID

    class Config:
        from_attributes = True

# Additional properties to return via API
class Usuario(UsuarioInDBBase):
    pass

# Additional properties stored in DB
class UsuarioInDB(UsuarioInDBBase):
    hashed_password: str

# Preferences
class UsuarioPreferences(BaseModel):
    theme: str = "light"

class UsuarioPreferencesUpdate(BaseModel):
    theme: str
