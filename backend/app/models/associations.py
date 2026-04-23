from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base  # Asegúrate de tener Base centralizado

cliente_empresa = Table(
    "cliente_empresa",
    Base.metadata,
    Column(
        "cliente_id", UUID(as_uuid=True), ForeignKey("clientes.id"), primary_key=True
    ),
    Column(
        "empresa_id", UUID(as_uuid=True), ForeignKey("empresas.id"), primary_key=True
    ),
)

# ── Sprint 6: Catálogos Operativos ────────────────────────────────────────────

tecnico_especialidades = Table(
    "tecnico_especialidades",
    Base.metadata,
    Column(
        "tecnico_id",
        UUID(as_uuid=True),
        ForeignKey("tecnicos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "servicio_id",
        UUID(as_uuid=True),
        ForeignKey("servicios_operativos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

unidad_servicios_compatibles = Table(
    "unidad_servicios_compatibles",
    Base.metadata,
    Column(
        "unidad_id",
        UUID(as_uuid=True),
        ForeignKey("unidades.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "servicio_id",
        UUID(as_uuid=True),
        ForeignKey("servicios_operativos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
