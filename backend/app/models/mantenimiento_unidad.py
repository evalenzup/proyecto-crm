# app/models/mantenimiento_unidad.py
import uuid
from sqlalchemy import Column, Date, Integer, Numeric, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class MantenimientoUnidad(Base):
    __tablename__ = "mantenimientos_unidad"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unidad_id = Column(
        UUID(as_uuid=True),
        ForeignKey("unidades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tipo = Column(String(20), nullable=False, default="PREVENTIVO")
    # PREVENTIVO / CORRECTIVO
    fecha_realizado = Column(Date, nullable=False)
    kilometraje_actual = Column(Integer, nullable=True)
    descripcion = Column(Text, nullable=True)
    costo = Column(Numeric(12, 2), nullable=True)
    proveedor = Column(String(150), nullable=True)
    proxima_fecha = Column(Date, nullable=True)
    proximo_kilometraje = Column(Integer, nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relaciones
    unidad = relationship("Unidad", back_populates="mantenimientos")

    def __repr__(self):
        return f"<MantenimientoUnidad(unidad_id={self.unidad_id}, tipo={self.tipo}, fecha={self.fecha_realizado})>"
