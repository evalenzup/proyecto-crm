# app/models/auditoria.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID

from app.models.cliente import Base


class AuditoriaLog(Base):
    __tablename__ = "auditoria_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), nullable=True)
    usuario_id = Column(UUID(as_uuid=True), nullable=True)
    usuario_email = Column(String(255), nullable=True)

    # Qué se hizo (ej. CREAR_FACTURA, TIMBRAR_FACTURA, CANCELAR_FACTURA)
    accion = Column(String(60), nullable=False)
    # Sobre qué entidad (ej. factura, cliente, empresa, egreso)
    entidad = Column(String(50), nullable=False)
    # UUID o clave del registro afectado
    entidad_id = Column(String(36), nullable=True)
    # Información extra en JSON (folio, RFC, monto, etc.)
    detalle = Column(Text, nullable=True)

    ip = Column(String(45), nullable=True)
    creado_en = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    __table_args__ = (
        Index("ix_auditoria_empresa_id", "empresa_id"),
        Index("ix_auditoria_usuario_id", "usuario_id"),
        Index("ix_auditoria_accion", "accion"),
        Index("ix_auditoria_entidad", "entidad"),
        Index("ix_auditoria_creado_en", "creado_en"),
    )
