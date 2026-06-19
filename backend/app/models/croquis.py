# app/models/croquis.py
import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Croquis(Base):
    """Croquis (plano) de un cliente: general o por área. Archivo PDF adjunto.

    Configurable por empresa (un cliente puede tener croquis distintos por empresa).
    Se pueden subir varios por cliente.
    """

    __tablename__ = "croquis"

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

    titulo = Column(String(150), nullable=False)
    area = Column(String(150), nullable=True)          # opcional: croquis por área
    descripcion = Column(Text, nullable=True)
    archivo = Column(String(255), nullable=False)      # nombre de archivo en data/croquis/

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")

    def __repr__(self):
        return f"<Croquis(titulo={self.titulo}, cliente_id={self.cliente_id})>"
