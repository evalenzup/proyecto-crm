# app/models/conciliacion.py
"""Conciliación bancaria mensual.

Reemplaza el Excel que se llenaba a mano: el estado de cuenta se importa, se
conserva el PDF original, y sobre cada movimiento quedan las dos anotaciones
que la contadora espera — el comentario (qué facturas lo componen, o qué fue
el gasto) y el área a la que corresponde.
"""
import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String,
    Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

# Áreas a las que se reparte un gasto. Se pueden combinar ("A,F") cuando el
# gasto es compartido, que es como ya lo venían anotando.
AREAS = {
    "A": "Administración",
    "F": "Fumigaciones",
    "J": "Jardinería",
    "L": "Limpieza",
}


class ConciliacionBancaria(Base):
    __tablename__ = "conciliaciones_bancarias"
    __table_args__ = (
        UniqueConstraint("empresa_id", "cuenta", "periodo_inicio", "periodo_fin",
                         name="uq_concil_periodo"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"),
                        nullable=False, index=True)

    periodo_inicio = Column(Date, nullable=False)
    periodo_fin = Column(Date, nullable=False)
    banco = Column(String(50), nullable=False, default="BANAMEX")
    cuenta = Column(String(50), nullable=True)

    # El PDF original. Se archiva porque es el respaldo del trabajo.
    archivo_nombre = Column(String(255), nullable=True)
    archivo_path = Column(String(500), nullable=True)

    # Lo que declara el banco. El importador exige que cuadre antes de guardar.
    saldo_inicial = Column(Numeric(14, 2), nullable=False)
    saldo_final = Column(Numeric(14, 2), nullable=False)
    total_depositos = Column(Numeric(14, 2), nullable=False)
    total_retiros = Column(Numeric(14, 2), nullable=False)
    n_depositos = Column(Integer, nullable=False)
    n_retiros = Column(Integer, nullable=False)

    estado = Column(String(20), nullable=False, default="EN_PROCESO")  # EN_PROCESO | CERRADA
    creado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(),
                            onupdate=func.now(), nullable=False)

    empresa = relationship("Empresa", lazy="selectin")
    movimientos = relationship(
        "MovimientoBancario", back_populates="conciliacion",
        cascade="all, delete-orphan", order_by="MovimientoBancario.orden",
    )

    @property
    def conciliados(self) -> int:
        return sum(1 for m in self.movimientos if m.conciliado)

    @property
    def total_movimientos(self) -> int:
        return len(self.movimientos)


class MovimientoBancario(Base):
    __tablename__ = "movimientos_bancarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conciliacion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conciliaciones_bancarias.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Conserva el orden del estado de cuenta: así lo lee ella
    orden = Column(Integer, nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    concepto = Column(Text, nullable=False)
    deposito = Column(Numeric(14, 2), nullable=True)
    retiro = Column(Numeric(14, 2), nullable=True)

    comentario = Column(Text, nullable=True)
    area = Column(String(20), nullable=True)
    conciliado = Column(Boolean, nullable=False, default=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(),
                            onupdate=func.now(), nullable=False)

    conciliacion = relationship("ConciliacionBancaria", back_populates="movimientos")
    facturas = relationship(
        "Factura", secondary="movimiento_facturas", lazy="selectin", viewonly=False,
    )

    @property
    def importe(self):
        """Monto del movimiento, con signo: positivo entra, negativo sale."""
        return self.deposito if self.deposito is not None else -(self.retiro or 0)

    @property
    def es_deposito(self) -> bool:
        return self.deposito is not None


class MovimientoFactura(Base):
    """Qué facturas componen un movimiento.

    Muchos a muchos a propósito: un depósito en efectivo puede cubrir varias
    facturas, y una factura puede cobrarse en varias exhibiciones.
    """
    __tablename__ = "movimiento_facturas"

    movimiento_id = Column(
        UUID(as_uuid=True),
        ForeignKey("movimientos_bancarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    factura_id = Column(
        UUID(as_uuid=True), ForeignKey("facturas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
