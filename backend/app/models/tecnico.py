# app/models/tecnico.py
import uuid
from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.associations import tecnico_especialidades


class Tecnico(Base):
    __tablename__ = "tecnicos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    nombre_completo = Column(String(200), nullable=False)
    telefono = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)
    max_servicios_dia = Column(Integer, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    notas = Column(Text, nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    empresa = relationship("Empresa", lazy="selectin")
    especialidades = relationship(
        "ServicioOperativo",
        secondary=tecnico_especialidades,
        back_populates="tecnicos",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Tecnico(nombre={self.nombre_completo})>"
