import uuid
import sqlalchemy as sa
from sqlalchemy import Column, String, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base

# Use JSONB on PostgreSQL, plain JSON on other dialects (e.g. SQLite for tests)
_JSON_TYPE = sa.JSON().with_variant(JSONB(), "postgresql")


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # None = notificación para toda la empresa; UUID = solo para ese usuario
    usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    tipo = Column(String(20), nullable=False)   # EXITO | INFO | ADVERTENCIA | ERROR
    titulo = Column(String(255), nullable=False)
    mensaje = Column(Text, nullable=False)
    leida = Column(Boolean, default=False, nullable=False)
    # Datos extra: factura_id, pago_id, etc.
    metadata_ = Column("metadata", _JSON_TYPE, nullable=True)

    creada_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
