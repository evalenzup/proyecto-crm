# app/models/refresh_token.py
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class RefreshToken(Base):
    """
    Whitelist de refresh tokens activos.
    Cada fila representa un token válido no revocado.
    Al renovar: se borra la fila antigua y se inserta una nueva (rotación).
    Al cerrar sesión: se borra la fila del token usado.
    """
    __tablename__ = "refresh_tokens"

    jti = Column(String(36), primary_key=True)          # UUID como string
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
