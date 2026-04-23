"""add seccion and costo_unitario_recarga to presupuesto_detalles

Revision ID: d6e7f8a9b0c1
Revises: b2c3d4e5f6a7
Create Date: 2026-04-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "d6e7f8a9b0c1"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "presupuesto_detalles",
        sa.Column("seccion", sa.String(100), nullable=True),
    )
    op.add_column(
        "presupuesto_detalles",
        sa.Column("costo_unitario_recarga", sa.Numeric(18, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("presupuesto_detalles", "costo_unitario_recarga")
    op.drop_column("presupuesto_detalles", "seccion")
