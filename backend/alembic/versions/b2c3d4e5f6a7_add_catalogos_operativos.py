"""add catalogos operativos sprint6

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f7
Create Date: 2026-04-22 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── servicios_operativos ─────────────────────────────────────────────────
    op.create_table(
        "servicios_operativos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "empresa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("empresas.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("duracion_estimada_min", sa.Integer, nullable=True),
        sa.Column("duracion_variable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("personal_requerido", sa.Integer, nullable=False, server_default="1"),
        sa.Column("requiere_vehiculo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "servicio_padre_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("servicios_operativos.id"),
            nullable=True,
        ),
        sa.Column("observaciones", sa.Text, nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("creado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_servicios_operativos_empresa_id", "servicios_operativos", ["empresa_id"])

    # ── tecnicos ─────────────────────────────────────────────────────────────
    op.create_table(
        "tecnicos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "empresa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("empresas.id"),
            nullable=False,
        ),
        sa.Column("nombre_completo", sa.String(200), nullable=False),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("max_servicios_dia", sa.Integer, nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("creado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tecnicos_empresa_id", "tecnicos", ["empresa_id"])

    # ── unidades ─────────────────────────────────────────────────────────────
    op.create_table(
        "unidades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "empresa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("empresas.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("placa", sa.String(20), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="OTRO"),
        sa.Column("max_servicios_dia", sa.Integer, nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("creado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_unidades_empresa_id", "unidades", ["empresa_id"])

    # ── mantenimientos_unidad ─────────────────────────────────────────────────
    op.create_table(
        "mantenimientos_unidad",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "unidad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("unidades.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="PREVENTIVO"),
        sa.Column("fecha_realizado", sa.Date, nullable=False),
        sa.Column("kilometraje_actual", sa.Integer, nullable=True),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("costo", sa.Numeric(12, 2), nullable=True),
        sa.Column("proveedor", sa.String(150), nullable=True),
        sa.Column("proxima_fecha", sa.Date, nullable=True),
        sa.Column("proximo_kilometraje", sa.Integer, nullable=True),
        sa.Column("creado_en", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mantenimientos_unidad_unidad_id", "mantenimientos_unidad", ["unidad_id"])

    # ── pivot: tecnico_especialidades ─────────────────────────────────────────
    op.create_table(
        "tecnico_especialidades",
        sa.Column(
            "tecnico_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tecnicos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "servicio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("servicios_operativos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # ── pivot: unidad_servicios_compatibles ───────────────────────────────────
    op.create_table(
        "unidad_servicios_compatibles",
        sa.Column(
            "unidad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("unidades.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "servicio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("servicios_operativos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("unidad_servicios_compatibles")
    op.drop_table("tecnico_especialidades")
    op.drop_index("ix_mantenimientos_unidad_unidad_id", table_name="mantenimientos_unidad")
    op.drop_table("mantenimientos_unidad")
    op.drop_index("ix_unidades_empresa_id", table_name="unidades")
    op.drop_table("unidades")
    op.drop_index("ix_tecnicos_empresa_id", table_name="tecnicos")
    op.drop_table("tecnicos")
    op.drop_index("ix_servicios_operativos_empresa_id", table_name="servicios_operativos")
    op.drop_table("servicios_operativos")
