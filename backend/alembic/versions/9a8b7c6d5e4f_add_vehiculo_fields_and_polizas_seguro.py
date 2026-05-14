"""add vehiculo fields to unidades and create polizas_seguro table

Revision ID: 9a8b7c6d5e4f
Revises: f8a9b0c1d2e3
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "9a8b7c6d5e4f"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Nuevos campos en tabla unidades ──────────────────────────────────────
    op.add_column("unidades", sa.Column("numero_serie", sa.String(50), nullable=True))
    op.add_column("unidades", sa.Column("marca", sa.String(60), nullable=True))
    op.add_column("unidades", sa.Column("version", sa.String(60), nullable=True))
    op.add_column("unidades", sa.Column("modelo_anio", sa.Integer(), nullable=True))
    op.add_column("unidades", sa.Column("capacidad_personas", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("unidades", sa.Column("color", sa.String(30), nullable=True))
    op.add_column("unidades", sa.Column("numero_motor", sa.String(50), nullable=True))
    op.add_column("unidades", sa.Column("numero_economico", sa.String(30), nullable=True))
    op.add_column("unidades", sa.Column("propietario", sa.String(120), nullable=True))

    # Fotos
    op.add_column("unidades", sa.Column("foto_frontal", sa.String(255), nullable=True))
    op.add_column("unidades", sa.Column("foto_lateral", sa.String(255), nullable=True))
    op.add_column("unidades", sa.Column("foto_placa", sa.String(255), nullable=True))

    # Tarjeta de circulación
    op.add_column("unidades", sa.Column("tarjeta_circulacion", sa.String(50), nullable=True))
    op.add_column("unidades", sa.Column("fecha_expedicion_tc", sa.Date(), nullable=True))
    op.add_column("unidades", sa.Column("doc_tarjeta_circulacion", sa.String(255), nullable=True))

    # ── Nueva tabla polizas_seguro ────────────────────────────────────────────
    op.create_table(
        "polizas_seguro",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("unidad_id", UUID(as_uuid=True), sa.ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("num_poliza", sa.String(60), nullable=False),
        sa.Column("compania", sa.String(100), nullable=False),
        sa.Column("fecha_expedicion", sa.Date(), nullable=True),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("documento", sa.String(255), nullable=True),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_polizas_seguro_unidad_id", "polizas_seguro", ["unidad_id"])


def downgrade() -> None:
    # Eliminar tabla polizas_seguro
    op.drop_index("ix_polizas_seguro_unidad_id", table_name="polizas_seguro")
    op.drop_table("polizas_seguro")

    # Eliminar columnas de unidades
    op.drop_column("unidades", "doc_tarjeta_circulacion")
    op.drop_column("unidades", "fecha_expedicion_tc")
    op.drop_column("unidades", "tarjeta_circulacion")
    op.drop_column("unidades", "foto_placa")
    op.drop_column("unidades", "foto_lateral")
    op.drop_column("unidades", "foto_frontal")
    op.drop_column("unidades", "propietario")
    op.drop_column("unidades", "numero_economico")
    op.drop_column("unidades", "numero_motor")
    op.drop_column("unidades", "color")
    op.drop_column("unidades", "capacidad_personas")
    op.drop_column("unidades", "modelo_anio")
    op.drop_column("unidades", "version")
    op.drop_column("unidades", "marca")
    op.drop_column("unidades", "numero_serie")
