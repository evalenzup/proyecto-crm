from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Tabla intermedia para relación muchos a muchos
cliente_empresa = Table(
    'cliente_empresa', Base.metadata,
    Column('cliente_id', UUID(as_uuid=True), ForeignKey('clientes.id'), primary_key=True),
    Column('empresa_id', UUID(as_uuid=True), ForeignKey('empresas.id'), primary_key=True)
)

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_comercial = Column(String(255), nullable=False)
    nombre_razon_social = Column(String(255), nullable=False)
    tipo_identificacion = Column(String(20), nullable=False)
    numero_identificacion = Column(String(50), unique=True, nullable=False)
    direccion = Column(Text)
    telefono = Column(String(50))
    email = Column(String(100))
    rfc = Column(String(13), nullable=False)
    regimen_fiscal = Column(String(100), nullable=False)
    codigo_postal_domicilio = Column(String(10))
    creado_en = Column(TIMESTAMP, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    empresas = relationship("Empresa", secondary=cliente_empresa, back_populates="clientes")
