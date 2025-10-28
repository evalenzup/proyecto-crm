# app/models/empresa.py
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.associations import cliente_empresa
from app.models.base import Base


class Empresa(Base):
    """
    Modelo de empresa.

    Importante:
      - 'contrasena' guarda la contraseña **real** (texto plano) de la llave .key del CSD.
      - 'archivo_cer' y 'archivo_key' guardan solo el nombre del archivo dentro de CERT_DIR.
    """

    __tablename__ = "empresas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    nombre_comercial = Column(String(255), nullable=False)
    ruc = Column(String(20), unique=True, nullable=False)
    direccion = Column(Text, nullable=True)
    telefono = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    rfc = Column(String(13), nullable=False)
    regimen_fiscal = Column(String(100), nullable=False)
    codigo_postal = Column(String(10), nullable=False)

    # ← TEXTO PLANO (no hash)
    contrasena = Column(String(255), nullable=False)

    archivo_cer = Column(String(255), nullable=True)
    archivo_key = Column(String(255), nullable=True)
    logo = Column(String(255), nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    clientes = relationship(
        "Cliente", secondary=cliente_empresa, back_populates="empresas"
    )
    productos_servicios = relationship(
        "ProductoServicio", back_populates="empresa", cascade="all, delete-orphan"
    )
    email_config = relationship(
        "EmailConfig",
        back_populates="empresa",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Empresa(nombre={self.nombre}, nombre_comercial={self.nombre_comercial}, ruc={self.ruc})>"
