# app/models/certificado_servicio.py
import uuid

from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Integer, String, Text, TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class CertificadoServicio(Base):
    """Certificado de servicio (p. ej. Aplicación de Plaguicidas) generado por el sistema.

    Folio consecutivo por empresa+tipo (mecánica de facturas). Los datos del
    establecimiento se copian como texto al certificado (v1: captura manual,
    con opción de prellenar desde un cliente).
    """

    __tablename__ = "certificados_servicio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True
    )
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    tipo = Column(String(20), nullable=False, default="PLAGUICIDAS")  # PLAGUICIDAS | SANITIZACION
    folio = Column(Integer, nullable=False)
    fecha = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)  # para determinar vigencia

    # Datos del establecimiento (texto plano en el certificado)
    nombre_razon_social = Column(String(255), nullable=False)
    domicilio = Column(Text, nullable=True)
    telefono = Column(String(50), nullable=True)
    actividad = Column(String(255), nullable=True)

    # Contenido del certificado — valores de texto libre ("X", números, etc.)
    areas = Column(JSONB, nullable=True)          # {"habitaciones": "X", ...}
    plagas = Column(JSONB, nullable=True)         # {"cucaracha": "X", ...}
    aplicaciones = Column(JSONB, nullable=True)   # {"tiempo_entrada": "2 HRS", ...}
    observaciones = Column(Text, nullable=True)   # líneas separadas por \n

    gerente_nombre = Column(String(255), nullable=True)  # quien firma

    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    empresa = relationship("Empresa", lazy="selectin")
    cliente = relationship("Cliente", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("empresa_id", "tipo", "folio", name="uq_certserv_folio_por_empresa_tipo"),
    )

    def __repr__(self):
        return f"<CertificadoServicio(tipo={self.tipo}, folio={self.folio})>"
