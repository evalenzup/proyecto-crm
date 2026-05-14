"""add direccion to tecnicos

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tecnicos",
        sa.Column("direccion", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tecnicos", "direccion")
