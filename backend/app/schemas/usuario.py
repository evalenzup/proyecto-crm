# app/schemas/usuario.py
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import List, Optional
from datetime import time
from uuid import UUID
from enum import Enum


class RolUsuario(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    ESTANDAR = "estandar"
    OPERATIVO = "operativo"


# ── Restricciones de acceso ───────────────────────────────────────────────────
class RestriccionesAcceso(BaseModel):
    """Acotan a un usuario sin cambiarle el rol. Todas opcionales."""

    puede_eliminar: Optional[bool] = None
    horario_inicio: Optional[time] = None
    horario_fin: Optional[time] = None
    # ISO: 1=lunes … 7=domingo, separados por coma. Ej. "1,2,3,4,5"
    dias_laborales: Optional[str] = None
    # IPs o rangos CIDR separados por coma. Ej. "189.223.202.22, 192.168.1.0/24"
    ips_permitidas: Optional[str] = None

    @field_validator("dias_laborales")
    @classmethod
    def validar_dias(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        dias = []
        for parte in v.split(","):
            parte = parte.strip()
            if not parte:
                continue
            if not parte.isdigit() or not 1 <= int(parte) <= 7:
                raise ValueError("Los días van del 1 (lunes) al 7 (domingo)")
            dias.append(int(parte))
        return ",".join(str(d) for d in sorted(set(dias))) or None

    @field_validator("ips_permitidas")
    @classmethod
    def validar_ips(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        import ipaddress
        entradas = []
        for parte in v.split(","):
            parte = parte.strip()
            if not parte:
                continue
            try:
                ipaddress.ip_network(parte, strict=False)
            except ValueError:
                raise ValueError(f"«{parte}» no es una IP ni un rango CIDR válido")
            entradas.append(parte)
        return ", ".join(entradas) or None

    @model_validator(mode="after")
    def horario_completo(self) -> "RestriccionesAcceso":
        uno = self.horario_inicio is not None
        otro = self.horario_fin is not None
        if uno != otro:
            raise ValueError("El horario necesita hora de inicio y de fin")
        return self


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
    # Restricciones de acceso (opcional)
    restricciones: Optional[RestriccionesAcceso] = None

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
    # Restricciones de acceso (None en cada campo = no cambiar)
    restricciones: Optional[RestriccionesAcceso] = None

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
    puede_eliminar: bool = True
    horario_inicio: Optional[time] = None
    horario_fin: Optional[time] = None
    dias_laborales: Optional[str] = None
    ips_permitidas: Optional[str] = None

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
