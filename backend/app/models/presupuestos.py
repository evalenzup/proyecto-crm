# app/models/presupuestos.py

import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    TIMESTAMP,
    Numeric,
    ForeignKey,
    Date,
    Integer,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.models.base import Base


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio = Column(String, nullable=False, unique=True)
    version = Column(Integer, nullable=False, default=1)

    empresa_id = Column(
        pgUUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True
    )
    cliente_id = Column(
        pgUUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, index=True
    )
    responsable_id = Column(pgUUID(as_uuid=True), nullable=True, index=True)

    fecha_emision = Column(Date, nullable=False, default=func.current_date())
    fecha_vencimiento = Column(Date, nullable=True)
    estado = Column(
        Enum(
            "BORRADOR",
            "ENVIADO",
            "ACEPTADO",
            "RECHAZADO",
            "CADUCADO",
            "FACTURADO",
            "ARCHIVADO",
            name="estado_presupuesto_enum",
        ),
        nullable=False,
        default="BORRADOR",
    )

    moneda = Column(String(3), nullable=False, default="MXN")
    tipo_cambio = Column(Numeric(10, 2), nullable=True, default=1.00)

    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    descuento_total = Column(Numeric(18, 2), nullable=False, default=0)
    impuestos = Column(Numeric(18, 2), nullable=False, default=0)
    total = Column(Numeric(18, 2), nullable=False, default=0)

    condiciones_comerciales = Column(Text, nullable=True)
    notas_internas = Column(Text, nullable=True)
    firma_cliente = Column(String, nullable=True)  # URL o token

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones ORM
    empresa = relationship("Empresa", backref=backref("presupuestos", lazy="selectin"))
    cliente = relationship("Cliente", backref=backref("presupuestos", lazy="selectin"))
    detalles = relationship(
        "PresupuestoDetalle",
        back_populates="presupuesto",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    adjuntos = relationship(
        "PresupuestoAdjunto",
        back_populates="presupuesto",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    eventos = relationship(
        "PresupuestoEvento",
        back_populates="presupuesto",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PresupuestoDetalle(Base):
    __tablename__ = "presupuesto_detalles"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presupuesto_id = Column(
        pgUUID(as_uuid=True), ForeignKey("presupuestos.id"), nullable=False, index=True
    )
    producto_servicio_id = Column(
        pgUUID(as_uuid=True),
        ForeignKey("productos_servicios.id"),
        nullable=True,
        index=True,
    )

    descripcion = Column(Text, nullable=False)
    cantidad = Column(Numeric(18, 2), nullable=False, default=1)
    unidad = Column(String(50), nullable=True)
    precio_unitario = Column(Numeric(18, 2), nullable=False, default=0)
    costo_estimado = Column(Numeric(18, 2), nullable=True)
    tasa_impuesto = Column(Numeric(10, 4), nullable=False, default=0.08)
    impuesto_estimado = Column(Numeric(18, 2), nullable=True)
    importe = Column(Numeric(18, 2), nullable=False, default=0)
    margen_estimado = Column(Numeric(18, 2), nullable=True)

    # Relaciones ORM
    presupuesto = relationship("Presupuesto", back_populates="detalles")
    producto_servicio = relationship("ProductoServicio")


class PresupuestoAdjunto(Base):
    __tablename__ = "presupuesto_adjuntos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presupuesto_id = Column(
        pgUUID(as_uuid=True), ForeignKey("presupuestos.id"), nullable=False, index=True
    )
    archivo = Column(String, nullable=False)  # Ruta/URL
    nombre = Column(String, nullable=False)
    tipo = Column(String(50), nullable=True)  # MIME type
    fecha_subida = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relaciones ORM
    presupuesto = relationship("Presupuesto", back_populates="adjuntos")


class PresupuestoEvento(Base):
    __tablename__ = "presupuesto_eventos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presupuesto_id = Column(
        pgUUID(as_uuid=True), ForeignKey("presupuestos.id"), nullable=False, index=True
    )
    usuario_id = Column(pgUUID(as_uuid=True), nullable=True, index=True)
    accion = Column(
        Enum(
            "CREADO",
            "EDITADO",
            "ENVIADO",
            "VISTO",
            "ACEPTADO",
            "RECHAZADO",
            "FACTURADO",
            "ARCHIVADO",
            "BORRADOR",
            "CADUCADO",
            name="accion_presupuesto_enum",
        ),
        nullable=False,
    )
    comentario = Column(Text, nullable=True)
    fecha_evento = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relaciones ORM
    presupuesto = relationship("Presupuesto", back_populates="eventos")
