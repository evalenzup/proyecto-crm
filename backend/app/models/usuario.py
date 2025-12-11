# app/models/usuario.py
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base

class RolUsuario(str, enum.Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre_completo = Column(String, nullable=True)
    rol = Column(Enum(RolUsuario), default=RolUsuario.SUPERVISOR, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relación con Empresa (opcional para Admin, obligatorio para Supervisor logicamente)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True)
    
    empresa = relationship("Empresa", back_populates="usuarios")

# Nota: Agregar back_populates="usuarios" al modelo Empresa si no existe
