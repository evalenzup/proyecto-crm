# app/models/factura.py

from sqlalchemy import (
    Column,
    String,
    Text,
    TIMESTAMP,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Index,
    DateTime,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class Factura(Base):
    __tablename__ = "facturas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificación / folio
    serie = Column(String(10), nullable=False, default="A")
    folio = Column(Integer, nullable=False)

    # Relaciones
    empresa_id = Column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True
    )
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True
    )

    # Datos CFDI
    fecha_emision = Column(DateTime, nullable=True)  # fecha y hora de emisión del CFDI
    tipo_comprobante = Column(String(1), nullable=False, default="I")  # I, E, P, N
    forma_pago = Column(String(3), nullable=True)  # c_FormaPago
    metodo_pago = Column(String(3), nullable=True)  # PUE/PPD
    uso_cfdi = Column(String(3), nullable=True)  # c_UsoCFDI (receptor)
    moneda = Column(String(3), nullable=False, default="MXN")
    tipo_cambio = Column(Numeric(18, 6), nullable=True)
    lugar_expedicion = Column(String(5), nullable=True)  # CP emisor
    condiciones_pago = Column(Text, nullable=True)

    # Relación CFDI (cabecera) – guardado como texto
    cfdi_relacionados_tipo = Column(
        String(2), nullable=True
    )  # c_TipoRelacion (p.ej. 01, 02, ...)
    cfdi_relacionados = Column(Text, nullable=True)  # UUIDs separados por coma

    # Importes totales
    subtotal = Column(Numeric(18, 6), nullable=False, default=0)
    descuento = Column(Numeric(18, 6), nullable=False, default=0)
    impuestos_trasladados = Column(Numeric(18, 6), nullable=False, default=0)
    impuestos_retenidos = Column(Numeric(18, 6), nullable=False, default=0)
    total = Column(Numeric(18, 6), nullable=False, default=0)

    # Timbrado / estados CFDI
    estatus = Column(
        String(15), nullable=False, default="BORRADOR"
    )  # BORRADOR, TIMBRADA, CANCELADA
    motivo_cancelacion = Column(String(2), nullable=True)
    folio_fiscal_sustituto = Column(String(36), nullable=True)
    cfdi_uuid = Column(String(36), nullable=True)
    fecha_timbrado = Column(DateTime, nullable=True)
    no_certificado = Column(String(20), nullable=True)
    no_certificado_sat = Column(String(20), nullable=True)
    sello_cfdi = Column(Text, nullable=True)
    sello_sat = Column(Text, nullable=True)
    rfc_proveedor_sat = Column(String(13), nullable=True)

    # Pago / cobranza
    fecha_pago = Column(DateTime, nullable=True)  # programada / vencimiento
    fecha_cobro = Column(DateTime, nullable=True)  # real cobrada
    status_pago = Column(
        String(10), nullable=False, default="NO_PAGADA"
    )  # PAGADA | NO_PAGADA
    observaciones = Column(Text, nullable=True)

    # Archivos (opcional)
    xml_path = Column(String(255), nullable=True)
    pdf_path = Column(String(255), nullable=True)

    # Auditoría
    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones ORM (sin imports directos para evitar ciclos)
    empresa = relationship("Empresa", backref=backref("facturas", lazy="selectin"))
    cliente = relationship("Cliente", backref=backref("facturas", lazy="selectin"))
    conceptos = relationship(
        "FacturaDetalle",
        back_populates="factura",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    pagos_relacionados = relationship(
        "PagoDocumentoRelacionado", back_populates="factura", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "serie", "folio", name="uq_fact_serie_folio_por_empresa"
        ),
        Index("ix_facturas_serie_folio", "serie", "folio"),
        Index("ix_facturas_status_pago", "status_pago"),
        Index("ix_facturas_fechas_pago", "fecha_pago", "fecha_cobro"),
    )

    def __repr__(self) -> str:
        return f"<Factura(serie={self.serie}, folio={self.folio}, total={self.total}, status_pago={self.status_pago})>"
