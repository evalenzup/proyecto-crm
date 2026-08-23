# app/models/usuario.py
import uuid
import sqlalchemy as sa
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, DateTime, Time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.models.base import Base

# JSONB en PostgreSQL, JSON plano en el resto (SQLite, que es donde corren los
# tests). Sin la variante, crear el esquema en SQLite falla con
# "can't render element of type JSONB" y se cae la suite entera.
_JSON_TYPE = sa.JSON().with_variant(JSONB(), "postgresql")


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

    # Ficha de técnico asociada. Sólo aplica al rol OPERATIVO: es lo que permite
    # filtrarle la agenda a sus propias órdenes. Única, para que una ficha no
    # tenga dos cuentas.
    tecnico_id = Column(UUID(as_uuid=True), ForeignKey("tecnicos.id", ondelete="SET NULL"),
                        nullable=True, unique=True)
    tecnico = relationship("Tecnico", lazy="selectin")

    # Empresa directa (supervisor / estandar / operativo)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True)

    empresa = relationship("Empresa", back_populates="usuarios")

    # ── Restricciones de acceso (opcionales, NULL = sin restricción) ─────────
    # Acotan a un usuario sin tener que bajarle el rol. Se aplican en
    # deps.get_current_active_user, que es la puerta por la que pasan todos
    # los endpoints protegidos.
    puede_eliminar = Column(Boolean, nullable=False, server_default="true", default=True)
    puede_exportar = Column(Boolean, nullable=False, server_default="true", default=True)
    horario_inicio = Column(Time, nullable=True)   # hora local de México
    horario_fin = Column(Time, nullable=True)
    dias_laborales = Column(String(20), nullable=True)   # ISO: "1,2,3,4,5" (1=lunes)
    # Horario distinto por día. Cuando está presente manda sobre los dos campos
    # de arriba. {"1": ["08:00","18:00"], "6": ["08:00","14:00"]} — un día que
    # no aparece en el mapa no tiene acceso.
    horario_semanal = Column(_JSON_TYPE, nullable=True)
    ips_permitidas = Column(String(500), nullable=True)  # IPs o CIDR separados por coma

    # Preferencias de UI (tema, fuente, etc.) almacenadas en BD
    preferences = Column(_JSON_TYPE, nullable=False,
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
