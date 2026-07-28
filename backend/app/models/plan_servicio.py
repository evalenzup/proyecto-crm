# app/models/plan_servicio.py
"""
Plan de servicio (contrato/póliza) para clientes con fumigación recurrente.

No genera órdenes por adelantado: el tablero mensual calcula los periodos según
la periodicidad y el usuario los programa (crea la OrdenServicio) cuando toca.
Ligado opcionalmente al certificado del cliente.
"""
import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

# Periodicidades soportadas y su intervalo en meses (quincenal es caso aparte).
PERIODICIDADES = ("QUINCENAL", "MENSUAL", "BIMESTRAL", "TRIMESTRAL")


class PlanServicio(Base):
    __tablename__ = "planes_servicio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True)

    # Qué servicio cumple el plan y quién lo suele atender (ambos opcionales).
    servicio_id = Column(UUID(as_uuid=True), ForeignKey("servicios_operativos.id"), nullable=True)
    tecnico_id = Column(UUID(as_uuid=True), ForeignKey("tecnicos.id"), nullable=True)

    # Vigencia del contrato.
    vigencia_desde = Column(Date, nullable=False)
    vigencia_hasta = Column(Date, nullable=True)  # None = indefinido

    periodicidad = Column(String(20), nullable=False, default="MENSUAL")
    # Día preferido del mes (1-31); para QUINCENAL se usa ese día y +15.
    dia_preferido = Column(Integer, nullable=True)

    precio_pactado = Column(Numeric(12, 2), nullable=True)

    # Vínculo opcional al certificado de servicio del cliente.
    certificado_id = Column(
        UUID(as_uuid=True),
        ForeignKey("certificados_servicio.id", ondelete="SET NULL"),
        nullable=True,
    )

    notas = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    empresa = relationship("Empresa", lazy="selectin")
    cliente = relationship("Cliente", lazy="selectin")
    servicio = relationship("ServicioOperativo", lazy="selectin")
    tecnico = relationship("Tecnico", lazy="selectin")
    certificado = relationship("CertificadoServicio", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PlanServicio(cliente={self.cliente_id}, periodicidad={self.periodicidad})>"
