"""Add values to accion_presupuesto_enum

Revision ID: 16ba07feec40
Revises: ce0a6f216d5e
Create Date: 2025-11-21 21:50:12.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16ba07feec40'
down_revision: Union[str, Sequence[str], None] = 'ce0a6f216d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE accion_presupuesto_enum ADD VALUE IF NOT EXISTS 'ARCHIVADO'")
    op.execute("ALTER TYPE accion_presupuesto_enum ADD VALUE IF NOT EXISTS 'BORRADOR'")
    op.execute("ALTER TYPE accion_presupuesto_enum ADD VALUE IF NOT EXISTS 'CADUCADO'")


def downgrade() -> None:
    """Downgrade schema."""
    # Downgrading ENUM values is complex and not safely reversible.
    pass