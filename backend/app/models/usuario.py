# app/models/usuario.py
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.models.base import Base


class RolUsuario(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    ESTANDAR = "estandar"
    OPERATIVO = "operativo"


class UsuarioEmpresa(Base):
    """Junction table: admin/superadmin ↔ empresas accesibles."""
    __tablename__ = "usuario_empresas"

    usuario_id = Column(UUID(as_uuid=True),
                        ForeignKey("usuarios.id", ondelete="CASCADE"),
                        primary_key=True, nullable=False)
    empresa_id = Column(UUID(as_uuid=True),
                        ForeignKey("empresas.id", ondelete="CASCADE"),
                        primary_key=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UsuarioPermiso(Base):
    """Permisos de módulo para usuarios ESTANDAR."""
    __tablename__ = "usuario_permisos"

    usuario_id = Column(UUID(as_uuid=True),
                        ForeignKey("usuarios.id", ondelete="CASCADE"),
                        primary_key=True, nullable=False)
    modulo = Column(String(50), primary_key=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre_completo = Column(String, nullable=True)
    rol = Column(Enum(RolUsuario), default=RolUsuario.SUPERVISOR, nullable=False)
    is_active = Column(Boolean, default=True)

    # Empresa directa (supervisor / estandar / operativo)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True)

    empresa = relationship("Empresa", back_populates="usuarios")

    # Preferencias de UI (tema, fuente, etc.) almacenadas en BD
    preferences = Column(JSONB, nullable=False,
                         server_default='{"theme": "light", "font_size": 14}')

    # Empresas accesibles para admin/superadmin (muchos a muchos)
    empresas_accesibles = relationship(
        "Empresa",
        secondary="usuario_empresas",
        primaryjoin="Usuario.id == UsuarioEmpresa.usuario_id",
        secondaryjoin="UsuarioEmpresa.empresa_id == Empresa.id",
        lazy="selectin",
    )

    # Permisos de módulo para ESTANDAR (relación interna; usar permisos_modulos para el schema)
    _permisos_rel = relationship("UsuarioPermiso", cascade="all, delete-orphan",
                                 lazy="selectin")

    @property
    def empresas_ids(self):
        """IDs de empresas accesibles — leído por Pydantic con from_attributes=True."""
        return [e.id for e in (self.empresas_accesibles or [])]

    @property
    def permisos(self):
        """Lista de módulos permitidos — leído por Pydantic con from_attributes=True."""
        return [p.modulo for p in (self._permisos_rel or [])]
