# app/models/cliente_documento.py
import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ClienteDocumento(Base):
    """Documento adjunto de un cliente (contrato firmado, identificación, etc.)."""

    __tablename__ = "cliente_documentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tipo = Column(String(40), nullable=False, default="OTRO")  # CONTRATO, IDENTIFICACION, OTRO
    nombre = Column(String(255), nullable=False)               # nombre visible del documento
    archivo = Column(String(255), nullable=False)              # nombre de archivo en data/clientes_docs/

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    cliente = relationship("Cliente", back_populates="documentos")

    def __repr__(self):
        return f"<ClienteDocumento(tipo={self.tipo}, nombre={self.nombre})>"
