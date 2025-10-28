
import uuid
import enum
from sqlalchemy import Column, String, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base

class TipoContacto(str, enum.Enum):
    ADMINISTRATIVO = "ADMINISTRATIVO"
    COBRANZA = "COBRANZA"
    OPERATIVO = "OPERATIVO"
    PRINCIPAL = "PRINCIPAL"
    OTRO = "OTRO"

class Contacto(Base):
    __tablename__ = 'contactos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    puesto = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    telefono = Column(String(50), nullable=True)
    tipo = Column(Enum(TipoContacto), nullable=False, default=TipoContacto.PRINCIPAL)

    cliente_id = Column(UUID(as_uuid=True), ForeignKey('clientes.id'), nullable=False)

    cliente = relationship("Cliente", back_populates="contactos")

    def __repr__(self):
        return f"<Contacto(nombre={self.nombre}, cliente_id={self.cliente_id})>"
