"""add fecha_vencimiento_tc to unidades

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("unidades", sa.Column("fecha_vencimiento_tc", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("unidades", "fecha_vencimiento_tc")
