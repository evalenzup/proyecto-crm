"""Restricción de exportar a Excel por usuario

Revision ID: f7a3b81d6e42
Revises: e2c9d4a71f35
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a3b81d6e42"
down_revision = "e2c9d4a71f35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("puede_exportar", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "puede_exportar")
