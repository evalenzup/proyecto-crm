"""equipos de control configurables por empresa

Revision ID: c7f1a2b3d4e5
Revises: 4a3320ece7bc
Create Date: 2026-06-18 00:00:00.000000

Crea las tablas para equipos de control por cliente, configurables por empresa:
  - tipos_equipo        : catálogo de tipos por empresa
  - tipos_equipo_campo  : campos personalizados por tipo (form dinámico)
  - estados_equipo      : catálogo de estados por empresa
  - equipos_control     : equipo instalado en un cliente (valores en JSONB)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "c7f1a2b3d4e5"
down_revision = "4a3320ece7bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tipos_equipo",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tipos_equipo_empresa_id", "tipos_equipo", ["empresa_id"])

    op.create_table(
        "tipos_equipo_campo",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tipo_equipo_id", UUID(as_uuid=True), nullable=False),
        sa.Column("etiqueta", sa.String(length=100), nullable=False),
        sa.Column("clave", sa.String(length=60), nullable=False),
        sa.Column("tipo_dato", sa.String(length=20), nullable=False, server_default="TEXTO"),
        sa.Column("opciones", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=True),
        sa.Column("requerido", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tipo_equipo_id"], ["tipos_equipo.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tipos_equipo_campo_tipo_equipo_id", "tipos_equipo_campo", ["tipo_equipo_id"])

    op.create_table(
        "estados_equipo",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_estados_equipo_empresa_id", "estados_equipo", ["empresa_id"])

    op.create_table(
        "equipos_control",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_equipo_id", UUID(as_uuid=True), nullable=False),
        sa.Column("estado_id", UUID(as_uuid=True), nullable=True),
        sa.Column("identificador", sa.String(length=60), nullable=True),
        sa.Column("area", sa.String(length=150), nullable=True),
        sa.Column("fecha_instalacion", sa.Date(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valores", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=True),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tipo_equipo_id"], ["tipos_equipo.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["estado_id"], ["estados_equipo.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_equipos_control_empresa_id", "equipos_control", ["empresa_id"])
    op.create_index("ix_equipos_control_cliente_id", "equipos_control", ["cliente_id"])
    op.create_index("ix_equipos_control_tipo_equipo_id", "equipos_control", ["tipo_equipo_id"])
    op.create_index("ix_equipos_control_estado_id", "equipos_control", ["estado_id"])


def downgrade() -> None:
    op.drop_table("equipos_control")
    op.drop_table("estados_equipo")
    op.drop_table("tipos_equipo_campo")
    op.drop_table("tipos_equipo")
