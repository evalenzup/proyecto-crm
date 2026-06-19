# app/models/equipo.py
"""
Equipos de control por cliente (cebaderos, trampas, extintores, etc.).

Diseño configurable por empresa (giros distintos):
  - TipoEquipo     : catálogo de tipos por empresa (config).
  - TipoEquipoCampo: campos personalizados POR TIPO (form dinámico).
  - EstadoEquipo   : catálogo de estados por empresa (config).
  - EquipoControl  : equipo concreto instalado en un cliente, con valores
                     de los campos personalizados en JSON.
"""
import uuid

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

# JSONB en PostgreSQL, JSON plano en otros dialectos (tests con SQLite)
_JSON_TYPE = sa.JSON().with_variant(JSONB(), "postgresql")


class TipoEquipo(Base):
    """Tipo de equipo definido por cada empresa (p.ej. Cebadero, Trampa, Extintor PQS)."""

    __tablename__ = "tipos_equipo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    empresa = relationship("Empresa")
    campos = relationship(
        "TipoEquipoCampo",
        back_populates="tipo_equipo",
        cascade="all, delete-orphan",
        order_by="TipoEquipoCampo.orden",
    )

    def __repr__(self):
        return f"<TipoEquipo(nombre={self.nombre})>"


class TipoEquipoCampo(Base):
    """Campo personalizado de un tipo de equipo; define el form dinámico de captura."""

    __tablename__ = "tipos_equipo_campo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_equipo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tipos_equipo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    etiqueta = Column(String(100), nullable=False)            # texto visible
    clave = Column(String(60), nullable=False)                # llave en EquipoControl.valores
    tipo_dato = Column(String(20), nullable=False, default="TEXTO")  # TEXTO|NUMERO|FECHA|BOOLEANO|LISTA
    opciones = Column(_JSON_TYPE, nullable=True)              # lista de strings para tipo LISTA
    requerido = Column(Boolean, nullable=False, default=False)
    orden = Column(Integer, nullable=False, default=0)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    tipo_equipo = relationship("TipoEquipo", back_populates="campos")

    def __repr__(self):
        return f"<TipoEquipoCampo(clave={self.clave}, tipo={self.tipo_dato})>"


class EstadoEquipo(Base):
    """Estado posible de un equipo, configurable por empresa (Activo, Dañado, Extraviado…)."""

    __tablename__ = "estados_equipo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre = Column(String(60), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    empresa = relationship("Empresa")

    def __repr__(self):
        return f"<EstadoEquipo(nombre={self.nombre})>"


class EquipoControl(Base):
    """Equipo concreto instalado en la ubicación de un cliente."""

    __tablename__ = "equipos_control"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cliente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_equipo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tipos_equipo.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    estado_id = Column(
        UUID(as_uuid=True),
        ForeignKey("estados_equipo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    identificador = Column(String(60), nullable=True)   # número visible (ej. "C-01")
    area = Column(String(150), nullable=True)            # ubicación/área
    fecha_instalacion = Column(Date, nullable=True)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    # Valores de los campos personalizados, keyed por TipoEquipoCampo.clave
    valores = Column(_JSON_TYPE, nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    tipo_equipo = relationship("TipoEquipo")
    estado = relationship("EstadoEquipo")

    def __repr__(self):
        return f"<EquipoControl(identificador={self.identificador}, cliente_id={self.cliente_id})>"
