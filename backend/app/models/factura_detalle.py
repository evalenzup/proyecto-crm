# app/models/factura_detalle.py

from sqlalchemy import (
    Column,
    String,
    Text,
    TIMESTAMP,
    Numeric,
    ForeignKey,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class FacturaDetalle(Base):
    __tablename__ = "facturas_detalle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relación con cabecera
    factura_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    factura = relationship("Factura", back_populates="conceptos")

    # (Opcional) relación con tu catálogo de productos/servicios
    producto_servicio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("productos_servicios.id"),
        nullable=True,
        index=True,
    )
    tipo = Column(String(50), nullable=True)
    requiere_lote = Column(Boolean, default=False)
    lote = Column(String(50), nullable=True)

    # Identificación de línea (útil en PDF/UX)
    no_identificacion = Column(String(50), nullable=True)  # SKU / código interno
    unidad = Column(String(20), nullable=True)  # Unidad comercial (texto)

    # CFDI requeridos del concepto
    clave_producto = Column(String(20), nullable=False)  # c_ClaveProdServ
    clave_unidad = Column(String(20), nullable=False)  # c_ClaveUnidad
    descripcion = Column(Text, nullable=False)

    cantidad = Column(Numeric(18, 6), nullable=False, default=1)
    valor_unitario = Column(Numeric(18, 6), nullable=False, default=0)
    descuento = Column(Numeric(18, 6), nullable=False, default=0)
    importe = Column(
        Numeric(18, 6), nullable=False, default=0
    )  # cantidad * valor_unitario - descuento

    # c_ObjetoImp (01=No objeto, 02=Sí objeto, 03=Sí objeto y no obligado al desglose, 04=Sí objeto y no causa)
    objeto_imp = Column(String(2), nullable=True, default="02")

    # ───────── Impuestos trasladados (IVA) ─────────
    base_iva = Column(Numeric(18, 6), nullable=True)  # Base usada para el cálculo
    iva_tipo_factor = Column(String(10), nullable=True)  # 'Tasa' | 'Cuota' | 'Exento'
    iva_tasa = Column(Numeric(18, 6), nullable=True)  # p.ej. 0.160000
    iva_importe = Column(Numeric(18, 6), nullable=True)

    # ───────── Retenciones ─────────
    ret_iva_base = Column(Numeric(18, 6), nullable=True)
    ret_iva_tipo_factor = Column(String(10), nullable=True)  # normalmente 'Tasa'
    ret_iva_tasa = Column(Numeric(18, 6), nullable=True)
    ret_iva_importe = Column(Numeric(18, 6), nullable=True)

    ret_isr_base = Column(Numeric(18, 6), nullable=True)
    ret_isr_tipo_factor = Column(String(10), nullable=True)  # normalmente 'Tasa'
    ret_isr_tasa = Column(Numeric(18, 6), nullable=True)
    ret_isr_importe = Column(Numeric(18, 6), nullable=True)

    # ───────── IEPS (opcional) ─────────
    ieps_base = Column(Numeric(18, 6), nullable=True)
    ieps_tipo_factor = Column(String(10), nullable=True)  # 'Tasa' | 'Cuota'
    ieps_tasa_cuota = Column(
        Numeric(18, 6), nullable=True
    )  # puede ser cuota específica
    ieps_importe = Column(Numeric(18, 6), nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_facturas_detalle_claves", "clave_producto", "clave_unidad"),
        Index("ix_facturas_detalle_no_ident", "no_identificacion"),
    )

    def __repr__(self) -> str:
        return f"<FacturaDetalle(clave={self.clave_producto}, importe={self.importe})>"
