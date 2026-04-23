# app/models/servicio_operativo.py
import uuid
from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.associations import tecnico_especialidades, unidad_servicios_compatibles


class ServicioOperativo(Base):
    __tablename__ = "servicios_operativos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    duracion_estimada_min = Column(Integer, nullable=True)       # minutos
    duracion_variable = Column(Boolean, nullable=False, default=False)
    personal_requerido = Column(Integer, nullable=False, default=1)
    requiere_vehiculo = Column(Boolean, nullable=False, default=False)
    servicio_padre_id = Column(UUID(as_uuid=True), ForeignKey("servicios_operativos.id"), nullable=True)
    observaciones = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    empresa = relationship("Empresa", lazy="selectin")
    servicio_padre = relationship("ServicioOperativo", remote_side="ServicioOperativo.id", lazy="selectin")
    tecnicos = relationship(
        "Tecnico",
        secondary=tecnico_especialidades,
        back_populates="especialidades",
        lazy="selectin",
    )
    unidades = relationship(
        "Unidad",
        secondary=unidad_servicios_compatibles,
        back_populates="servicios_compatibles",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<ServicioOperativo(nombre={self.nombre})>"
