# app/models/poliza_seguro.py
import uuid
from sqlalchemy import Boolean, Column, Date, String, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class PolizaSeguro(Base):
    __tablename__ = "polizas_seguro"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unidad_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False, index=True)

    num_poliza = Column(String(60), nullable=False)
    compania = Column(String(100), nullable=False)
    fecha_expedicion = Column(Date, nullable=True)
    fecha_vencimiento = Column(Date, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    documento = Column(String(255), nullable=True)             # póliza (archivo en data/unidades_docs/)
    documento_factura = Column(String(255), nullable=True)     # factura de la póliza
    documento_complemento = Column(String(255), nullable=True) # complemento de pago de la póliza

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    unidad = relationship("Unidad", back_populates="polizas_seguro")

    def __repr__(self):
        return f"<PolizaSeguro(num_poliza={self.num_poliza}, compania={self.compania})>"
