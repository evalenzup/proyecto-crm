"""add color_credencial to empresas

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column("color_credencial", sa.String(7), nullable=True, server_default="#1a6b3a"),
    )


def downgrade() -> None:
    op.drop_column("empresas", "color_credencial")
