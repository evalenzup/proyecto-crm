import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    func,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class EstatusPago(str, enum.Enum):
    BORRADOR = "BORRADOR"
    TIMBRADO = "TIMBRADO"
    CANCELADO = "CANCELADO"


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True)

    # --- Datos generales del complemento ---
    serie = Column(String, nullable=True)
    folio = Column(String, nullable=False)
    fecha_pago = Column(DateTime, nullable=False)
    forma_pago_p = Column(String(2), nullable=False)  # Catálogo SAT c_FormaPago
    moneda_p = Column(String(3), nullable=False)  # Catálogo SAT c_Moneda
    monto = Column(Numeric(18, 4), nullable=False)
    tipo_cambio_p = Column(Numeric(18, 6), nullable=True)
    
    estatus = Column(SQLAlchemyEnum(EstatusPago), nullable=False, default=EstatusPago.BORRADOR)

    # --- Datos del timbrado (CFDI) ---
    uuid = Column(String, nullable=True, unique=True, index=True)
    fecha_timbrado = Column(DateTime, nullable=True)
    xml_path = Column(String(255), nullable=True)
    pdf_path = Column(String(255), nullable=True)
    cadena_original = Column(Text, nullable=True)
    qr_url = Column(Text, nullable=True)

    motivo_cancelacion = Column(String(2), nullable=True)
    folio_fiscal_sustituto = Column(String(36), nullable=True)
    no_certificado    = Column(String(20),   nullable=True)
    no_certificado_sat= Column(String(20),   nullable=True)
    sello_cfdi        = Column(Text,         nullable=True)
    sello_sat         = Column(Text,         nullable=True)
    rfc_proveedor_sat = Column(String(13),   nullable=True)

    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relaciones ---
    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    documentos_relacionados = relationship("PagoDocumentoRelacionado", back_populates="pago", cascade="all, delete-orphan")


class PagoDocumentoRelacionado(Base):
    __tablename__ = "pago_documentos_relacionados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pago_id = Column(UUID(as_uuid=True), ForeignKey("pagos.id"), nullable=False, index=True)
    factura_id = Column(UUID(as_uuid=True), ForeignKey("facturas.id"), nullable=False, index=True)

    # --- Datos del documento relacionado (del complemento) ---
    id_documento = Column(String, nullable=False)  # UUID de la factura relacionada
    serie = Column(String, nullable=True)
    folio = Column(String, nullable=True)
    moneda_dr = Column(String(3), nullable=False)
    num_parcialidad = Column(Numeric(10), nullable=False)
    imp_saldo_ant = Column(Numeric(18, 4), nullable=False)
    imp_pagado = Column(Numeric(18, 4), nullable=False)
    imp_saldo_insoluto = Column(Numeric(18, 4), nullable=False)
    tipo_cambio_dr = Column(Numeric(18, 6), nullable=True)

    # --- Relaciones ---
    pago = relationship("Pago", back_populates="documentos_relacionados")
    factura = relationship("Factura", back_populates="pagos_relacionados")
