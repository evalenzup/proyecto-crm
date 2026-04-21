# app/schemas/usuario.py
from pydantic import BaseModel, EmailStr, model_validator
from typing import List, Optional
from uuid import UUID
from enum import Enum


class RolUsuario(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    ESTANDAR = "estandar"
    OPERATIVO = "operativo"


# ── Shared properties ──────────────────────────────────────────────────────────
class UsuarioBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    nombre_completo: Optional[str] = None
    rol: RolUsuario = RolUsuario.SUPERVISOR
    empresa_id: Optional[UUID] = None


# ── Create ─────────────────────────────────────────────────────────────────────
class UsuarioCreate(UsuarioBase):
    email: EmailStr
    password: str
    # Para admin: lista de empresa_ids accesibles
    empresas_ids: Optional[List[UUID]] = None
    # Para estandar: lista de módulos permitidos
    permisos: Optional[List[str]] = None

    @model_validator(mode="after")
    def validar_empresa_segun_rol(self) -> "UsuarioCreate":
        if self.rol == RolUsuario.SUPERVISOR and not self.empresa_id:
            raise ValueError("Un supervisor debe tener una empresa asignada (empresa_id requerido)")
        if self.rol == RolUsuario.ESTANDAR and not self.empresa_id:
            raise ValueError("Un usuario estándar debe tener una empresa asignada (empresa_id requerido)")
        return self


# ── Update ─────────────────────────────────────────────────────────────────────
class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    nombre_completo: Optional[str] = None
    rol: Optional[RolUsuario] = None
    is_active: Optional[bool] = None
    empresa_id: Optional[UUID] = None
    # Para admin: lista de empresa_ids accesibles (None = no cambiar)
    empresas_ids: Optional[List[UUID]] = None
    # Para estandar: lista de módulos permitidos (None = no cambiar)
    permisos: Optional[List[str]] = None

    @model_validator(mode="after")
    def supervisor_no_puede_perder_empresa(self) -> "UsuarioUpdate":
        if (
            self.rol in (RolUsuario.SUPERVISOR, RolUsuario.ESTANDAR)
            and self.empresa_id is None
            and "empresa_id" in self.model_fields_set
        ):
            raise ValueError("Este rol necesita una empresa asignada (empresa_id requerido)")
        return self


# ── DB Base ────────────────────────────────────────────────────────────────────
# Pydantic v2 con from_attributes=True lee las @property del modelo ORM
# directamente: empresas_ids y permisos son properties en el modelo Usuario.
class UsuarioInDBBase(UsuarioBase):
    id: UUID
    empresas_ids: List[UUID] = []
    permisos: List[str] = []

    class Config:
        from_attributes = True


# ── API response ───────────────────────────────────────────────────────────────
class Usuario(UsuarioInDBBase):
    pass


# ── DB internal ───────────────────────────────────────────────────────────────
class UsuarioInDB(UsuarioInDBBase):
    hashed_password: str


# ── Contraseña propia ─────────────────────────────────────────────────────────
class ChangePassword(BaseModel):
    password_actual: str
    password_nuevo: str


# ── Preferencias ─────────────────────────────────────────────────────────────
class UsuarioPreferences(BaseModel):
    theme: str = "light"
    font_size: int = 14


class UsuarioPreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    font_size: Optional[int] = None


# ── Asignar empresas / permisos (endpoints dedicados) ─────────────────────────
class AsignarEmpresasIn(BaseModel):
    empresas_ids: List[UUID]


class AsignarPermisosIn(BaseModel):
    permisos: List[str]
