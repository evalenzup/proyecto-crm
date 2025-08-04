# app/models/producto_servicio.py

from sqlalchemy import (
    Column, String, Text, TIMESTAMP, Numeric, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class ProductoServicio(Base):
    """
    Modelo para representar un producto o servicio.
    """
    __tablename__ = 'productos_servicios'

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificación en CFDI
    tipo             = Column(String(10), nullable=False)  # 'PRODUCTO' o 'SERVICIO'
    clave_producto   = Column(String(20), nullable=False)
    clave_unidad     = Column(String(20), nullable=False)
    descripcion      = Column(Text,       nullable=False)

    # Cantidades y precios base
    cantidad         = Column(Numeric(18, 2), nullable=True)
    valor_unitario   = Column(Numeric(18, 2), nullable=False)

    # Relación con Empresa
    empresa_id       = Column(UUID(as_uuid=True), ForeignKey('empresas.id'), nullable=False)
    empresa          = relationship('Empresa', back_populates='productos_servicios')

    # --- Campos de inventario (solo obligatorios si tipo == 'PRODUCTO') ---
    stock_actual      = Column(Numeric(18, 2),  nullable=True, default=0)
    stock_minimo      = Column(Numeric(18, 2),  nullable=True)
    unidad_inventario = Column(String(20),      nullable=True)
    ubicacion         = Column(String(100),     nullable=True)
    requiere_lote     = Column(Boolean,         default=False)

    creado_en        = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en   = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('empresa_id', 'descripcion', name='uq_empresa_descripcion'),
    )

    def __repr__(self):
        return (f"<ProductoServicio(tipo={self.tipo}, "
                f"clave_producto={self.clave_producto}, "
                f"descripcion={self.descripcion})>")