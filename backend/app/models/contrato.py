# app/models/contrato.py
import uuid
import sqlalchemy as sa
from sqlalchemy import Column, String, Text, Date, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

# JSONB en PostgreSQL, JSON plano en otros dialectos (tests con SQLite)
_JSON_TYPE = sa.JSON().with_variant(JSONB(), "postgresql")


class Contrato(Base):
    """
    Contrato de prestación de servicios entre una empresa (prestador) y un cliente.
    La generación del documento (docx/PDF) se hace en Fase 0b a partir de estos datos.
    """

    __tablename__ = "contratos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True)
    # Origen opcional: si el contrato se precargó desde un presupuesto aceptado
    presupuesto_id = Column(UUID(as_uuid=True), ForeignKey("presupuestos.id"), nullable=True, index=True)

    numero_contrato = Column(String(40), nullable=True)        # identificador visible (opcional)
    fecha_contrato = Column(Date, nullable=True)               # fecha de firma
    vigencia_desde = Column(Date, nullable=True)
    vigencia_hasta = Column(Date, nullable=True)

    # Folio del certificado de aplicación referenciado en el contrato
    certificado_folio = Column(String(40), nullable=True)

    # Valores manuales del contrato, keyed por el nombre del placeholder de la
    # plantilla de la empresa: { "precio_fumigacion": 3146, "vigencia_texto": "...", ... }
    datos = Column(_JSON_TYPE, nullable=True)
    # (en desuso) campos fijos previos; se conserva la columna por compatibilidad
    servicios = Column(_JSON_TYPE, nullable=True)
    # Personal asignado: lista de tecnico_ids (los datos NSS/CURP/salario se leen del técnico al generar)
    personal_asignado = Column(_JSON_TYPE, nullable=True)

    exclusiones = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)

    estado = Column(String(20), nullable=False, default="BORRADOR")  # BORRADOR | GENERADO | FIRMADO
    archivo_docx = Column(String(255), nullable=True)          # documento generado (data/contratos/)
    archivo_pdf = Column(String(255), nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")

    def __repr__(self):
        return f"<Contrato(cliente_id={self.cliente_id}, estado={self.estado})>"
