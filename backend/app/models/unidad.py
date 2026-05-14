# app/models/unidad.py
import uuid
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.associations import unidad_servicios_compatibles


class Unidad(Base):
    __tablename__ = "unidades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    # ── Campos originales ────────────────────────────────────────────────────
    nombre = Column(String(100), nullable=False)
    placa = Column(String(20), nullable=True)
    tipo = Column(String(30), nullable=False, default="OTRO")
    max_servicios_dia = Column(Integer, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    notas = Column(Text, nullable=True)

    # ── Información del vehículo ─────────────────────────────────────────────
    numero_serie = Column(String(50), nullable=True)        # VIN
    marca = Column(String(60), nullable=True)
    version = Column(String(60), nullable=True)
    modelo_anio = Column(Integer, nullable=True)
    capacidad_personas = Column(Integer, nullable=True, default=0)
    color = Column(String(30), nullable=True)
    numero_motor = Column(String(50), nullable=True)
    numero_economico = Column(String(30), nullable=True)
    propietario = Column(String(120), nullable=True)

    # ── Fotos del vehículo (nombre de archivo relativo a data/unidades_fotos/) ─
    foto_frontal = Column(String(255), nullable=True)
    foto_lateral = Column(String(255), nullable=True)
    foto_placa = Column(String(255), nullable=True)

    # ── Tarjeta de circulación ───────────────────────────────────────────────
    tarjeta_circulacion = Column(String(50), nullable=True)
    fecha_expedicion_tc = Column(Date, nullable=True)
    fecha_vencimiento_tc = Column(Date, nullable=True)
    doc_tarjeta_circulacion = Column(String(255), nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # ── Relaciones ───────────────────────────────────────────────────────────
    empresa = relationship("Empresa", lazy="selectin")
    servicios_compatibles = relationship(
        "ServicioOperativo",
        secondary=unidad_servicios_compatibles,
        back_populates="unidades",
        lazy="selectin",
    )
    mantenimientos = relationship(
        "MantenimientoUnidad",
        back_populates="unidad",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MantenimientoUnidad.fecha_realizado.desc()",
    )
    polizas_seguro = relationship(
        "PolizaSeguro",
        back_populates="unidad",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PolizaSeguro.fecha_vencimiento.desc()",
    )

    def __repr__(self):
        return f"<Unidad(nombre={self.nombre}, placa={self.placa})>"
