"""merge heads: d6e7f8a9b0c1 + e6f7a8b9c0d1

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1, e6f7a8b9c0d1
Create Date: 2026-04-22 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "e7f8a9b0c1d2"
down_revision = ("d6e7f8a9b0c1", "e6f7a8b9c0d1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
