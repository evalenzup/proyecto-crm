# app/models/tecnico.py
import uuid
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.associations import tecnico_especialidades


class Tecnico(Base):
    __tablename__ = "tecnicos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    # ── Nombre (campos separados) ────────────────────────────────────────────
    nombre = Column(String(100), nullable=True)
    primer_apellido = Column(String(100), nullable=True)
    segundo_apellido = Column(String(100), nullable=True)
    nombre_completo = Column(String(200), nullable=False)   # calculado; se mantiene por compat

    # ── Identificación ───────────────────────────────────────────────────────
    curp = Column(String(18), nullable=True)
    rfc = Column(String(13), nullable=True)
    nss = Column(String(11), nullable=True)
    sexo = Column(String(10), nullable=True)                # HOMBRE | MUJER | OTRO
    tipo_sangre = Column(String(5), nullable=True)          # A+, A-, B+, …

    # ── Datos laborales ──────────────────────────────────────────────────────
    numero_trabajador = Column(String(30), nullable=True)
    tipo_personal = Column(String(30), nullable=False, default="TECNICO")
    area = Column(String(100), nullable=True)
    puesto = Column(String(100), nullable=True)
    nivel_estudios = Column(String(50), nullable=True)

    # ── Contacto y domicilio ─────────────────────────────────────────────────
    telefono = Column(String(50), nullable=True)
    celular = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)
    direccion = Column(Text, nullable=True)

    # ── Licencia de conducir ─────────────────────────────────────────────────
    licencia_numero = Column(String(50), nullable=True)
    licencia_tipo = Column(String(20), nullable=True)       # A, B, C, D, E
    licencia_vencimiento = Column(Date, nullable=True)

    # ── Foto ─────────────────────────────────────────────────────────────────
    foto = Column(String(255), nullable=True)               # filename en data/tecnicos_fotos/

    # ── Operativo ────────────────────────────────────────────────────────────
    max_servicios_dia = Column(Integer, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    notas = Column(Text, nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # ── Relaciones ───────────────────────────────────────────────────────────
    empresa = relationship("Empresa", lazy="selectin")
    especialidades = relationship(
        "ServicioOperativo",
        secondary=tecnico_especialidades,
        back_populates="tecnicos",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Tecnico(nombre={self.nombre_completo})>"
