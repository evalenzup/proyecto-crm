import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class CobranzaNota(Base):
    __tablename__ = "cobranza_notas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True)
    
    # Opcional: Vincular a una factura específica
    factura_id = Column(UUID(as_uuid=True), ForeignKey("facturas.id"), nullable=True, index=True)
    
    nota = Column(Text, nullable=False)
    fecha_promesa_pago = Column(DateTime, nullable=True)
    
    creado_po = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    factura = relationship("Factura")
    usuario_creador = relationship("Usuario")
