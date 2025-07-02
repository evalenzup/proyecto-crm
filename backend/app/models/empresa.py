from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.associations import cliente_empresa
from app.models.base import Base

class Empresa(Base):
    __tablename__ = 'empresas'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    nombre_comercial = Column(String(255)) 
    ruc = Column(String(20), unique=True, nullable=False)
    direccion = Column(Text)
    telefono = Column(String(50))
    email = Column(String(100))
    rfc = Column(String(13), nullable=False)
    regimen_fiscal = Column(String(100), nullable=False)
    codigo_postal = Column(String(10), nullable=False)
    archivo_cer = Column(String(255))  
    archivo_key = Column(String(255)) 
    creado_en = Column(TIMESTAMP, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    clientes = relationship("Cliente", secondary=cliente_empresa, back_populates="empresas")
