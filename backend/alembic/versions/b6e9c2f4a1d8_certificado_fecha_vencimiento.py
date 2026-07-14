"""certificado: fecha de vencimiento (vigencia)

Revision ID: b6e9c2f4a1d8
Revises: a2d5e8f1c3b6
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa


revision = "b6e9c2f4a1d8"
down_revision = "a2d5e8f1c3b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "certificados_servicio",
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("certificados_servicio", "fecha_vencimiento")
