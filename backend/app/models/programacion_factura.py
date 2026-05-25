# app/models/programacion_factura.py
import uuid
from sqlalchemy import (
    Column, String, Boolean, Date, DateTime, Integer, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ProgramacionFactura(Base):
    """
    Plantilla para generación automática (y opcional timbrado + envío) de facturas
    en una fecha determinada o de forma recurrente.
    """
    __tablename__ = "programacion_facturas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Relaciones ────────────────────────────────────────────────────────────
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True)

    # ── Datos fiscales de la factura a generar ────────────────────────────────
    serie           = Column(String(10), nullable=True, default="A")
    tipo_comprobante = Column(String(1), nullable=False, default="I")
    forma_pago      = Column(String(3), nullable=True)
    metodo_pago     = Column(String(3), nullable=True)
    uso_cfdi        = Column(String(3), nullable=True)
    moneda          = Column(String(3), nullable=False, default="MXN")
    lugar_expedicion = Column(String(5), nullable=True)
    condiciones_pago = Column(Text, nullable=True)
    observaciones   = Column(Text, nullable=True)

    # Retención local opcional
    retencion_local_desc = Column(String(100), nullable=True)
    retencion_local_tasa = Column(String(20), nullable=True)   # guardada como str para evitar precisión flotante

    # ── Conceptos (copia de FacturaDetalleIn serializada) ────────────────────
    # Lista de dicts: [{clave_producto, clave_unidad, descripcion, cantidad,
    #                   valor_unitario, descuento, iva_tasa, ...}, ...]
    conceptos = Column(JSONB, nullable=False, default=list)

    # ── Programación ─────────────────────────────────────────────────────────
    # 'unica' | 'semanal' | 'quincenal' | 'mensual' | 'bimestral' | 'trimestral' | 'semestral' | 'anual'
    periodicidad        = Column(String(20), nullable=False, default="mensual")
    proxima_ejecucion   = Column(Date, nullable=False, index=True)
    fecha_fin           = Column(Date, nullable=True)   # None = indefinido

    # ── Automatización ────────────────────────────────────────────────────────
    auto_timbrar        = Column(Boolean, nullable=False, default=False)
    auto_enviar         = Column(Boolean, nullable=False, default=False)
    # Lista de strings: ["cliente@ejemplo.com", "pagos@empresa.com"]
    emails_destino      = Column(JSONB, nullable=True, default=list)

    # ── Control / estadísticas ───────────────────────────────────────────────
    nombre              = Column(String(120), nullable=True)   # etiqueta descriptiva
    activo              = Column(Boolean, nullable=False, default=True)
    ultima_ejecucion    = Column(DateTime, nullable=True)
    facturas_generadas  = Column(Integer, nullable=False, default=0)

    creado_en           = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en      = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # ── ORM ──────────────────────────────────────────────────────────────────
    empresa = relationship("Empresa", lazy="selectin")
    cliente = relationship("Cliente", lazy="selectin")
