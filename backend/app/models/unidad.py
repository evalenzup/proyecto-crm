# app/models/unidad.py
import uuid
from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.associations import unidad_servicios_compatibles


class Unidad(Base):
    __tablename__ = "unidades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    nombre = Column(String(100), nullable=False)
    placa = Column(String(20), nullable=True)
    tipo = Column(String(20), nullable=False, default="OTRO")
    # SEDAN / PICKUP / CAMIONETA / MOTOCICLETA / OTRO
    max_servicios_dia = Column(Integer, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    notas = Column(Text, nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
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

    def __repr__(self):
        return f"<Unidad(nombre={self.nombre}, placa={self.placa})>"
