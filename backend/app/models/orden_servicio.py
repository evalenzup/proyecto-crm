# app/models/orden_servicio.py
import uuid
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Time, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class OrdenServicio(Base):
    __tablename__ = "ordenes_servicio"
    __table_args__ = (
        UniqueConstraint('folio_os', 'empresa_id', name='uq_os_folio_empresa'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    # ── Relaciones principales ───────────────────────────────────────────────
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True)
    tecnico_id = Column(UUID(as_uuid=True), ForeignKey("tecnicos.id"), nullable=True, index=True)
    unidad_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"), nullable=True, index=True)
    servicio_id = Column(UUID(as_uuid=True), ForeignKey("servicios_operativos.id"), nullable=True)
    presupuesto_id = Column(UUID(as_uuid=True), ForeignKey("presupuestos.id"), nullable=True)

    # ── Folio ────────────────────────────────────────────────────────────────
    folio_os = Column(String(20), nullable=False, index=True)   # OS-0001

    # ── Programación ────────────────────────────────────────────────────────
    fecha_programada = Column(Date, nullable=False, index=True)
    hora_inicio = Column(Time, nullable=True)
    hora_fin = Column(Time, nullable=True)
    duracion_minutos = Column(Integer, nullable=True)

    # ── Estado y prioridad ───────────────────────────────────────────────────
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    # PENDIENTE | ASIGNADO | EN_CAMINO | EN_PROGRESO | COMPLETADO | CANCELADO | REAGENDADO

    prioridad = Column(String(10), nullable=False, default="MEDIA")
    # BAJA | MEDIA | ALTA | URGENTE

    # ── Ubicación del servicio ───────────────────────────────────────────────
    direccion_servicio = Column(Text, nullable=True)
    latitud = Column(Numeric(10, 7), nullable=True)
    longitud = Column(Numeric(10, 7), nullable=True)

    # ── Información financiera ───────────────────────────────────────────────
    precio_acordado = Column(Numeric(12, 2), nullable=True)

    # ── Notas ────────────────────────────────────────────────────────────────
    notas_tecnico = Column(Text, nullable=True)     # instrucciones al técnico
    notas_internas = Column(Text, nullable=True)    # solo visibles en el sistema
    notas_cierre = Column(Text, nullable=True)      # llenadas al completar

    # ── Control ─────────────────────────────────────────────────────────────
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # ── ORM Relationships ────────────────────────────────────────────────────
    empresa = relationship("Empresa", lazy="selectin")
    cliente = relationship("Cliente", lazy="selectin")
    tecnico = relationship("Tecnico", lazy="selectin")
    unidad = relationship("Unidad", lazy="selectin")
    servicio = relationship("ServicioOperativo", lazy="selectin")
    historial = relationship(
        "HistorialEstadoOS",
        back_populates="orden",
        order_by="HistorialEstadoOS.creado_en",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<OrdenServicio(folio={self.folio_os}, estado={self.estado})>"


class HistorialEstadoOS(Base):
    __tablename__ = "historial_estados_os"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orden_id = Column(UUID(as_uuid=True), ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    estado_anterior = Column(String(20), nullable=True)
    estado_nuevo = Column(String(20), nullable=False)
    notas = Column(Text, nullable=True)

    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orden = relationship("OrdenServicio", back_populates="historial")
    usuario = relationship("Usuario", lazy="selectin")
