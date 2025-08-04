# app/models/cliente.py
from sqlalchemy import Column, String, Text, TIMESTAMP, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.associations import cliente_empresa
from app.models.base import Base

class Cliente(Base):
    """
    Modelo para representar a un cliente.
    """

    __tablename__ = 'clientes'
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #Nombres
    nombre_comercial    = Column(String(255), nullable=False)
    nombre_razon_social = Column(String(255), nullable=False)
    #Datos fiscales
    rfc                 = Column(String(13),  nullable=False)
    regimen_fiscal      = Column(String(100), nullable=False)
    #Datos de contacto
    #direccion           = Column(Text)
    calle               = Column(String(100))
    numero_exterior     = Column(String(50))
    numero_interior     = Column(String(50))
    colonia             = Column(String(100))
    codigo_postal       = Column(String(10), nullable=False)
    telefono            = Column(String(50))
    email               = Column(ARRAY(String))
    #Datos para pago
    dias_credito        = Column(Integer, default=0)
    dias_recepcion      = Column(Integer, default=0)
    dias_pago           = Column(Integer, default=0)
    #Datos para ubicar tipo de cliente
    tamano              = Column(String(15)) #Chico, Mediano, Grande
    actividad           = Column(String(15)) #Residencial, Comercial, Industrial

    creado_en           = Column(TIMESTAMP, server_default=func.now())
    actualizado_en      = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    empresas            = relationship("Empresa", secondary=cliente_empresa, back_populates="clientes")

    def __repr__(self):
        return (f"<Cliente(nombre_comercial={self.nombre_comercial}, "
                f"rfc={self.rfc})>")
