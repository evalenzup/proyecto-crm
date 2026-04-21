"""add fecha_solicitud_cancelacion to facturas (EN_CANCELACION status)

Revision ID: a1b2c3d4e5f7
Revises: f3a4b5c6d7e8
Create Date: 2026-04-16 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ampliar la longitud del campo estatus para acomodar "EN_CANCELACION" (14 chars)
    op.alter_column(
        "facturas",
        "estatus",
        existing_type=sa.String(length=15),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.add_column(
        "facturas",
        sa.Column("fecha_solicitud_cancelacion", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("facturas", "fecha_solicitud_cancelacion")
    op.alter_column(
        "facturas",
        "estatus",
        existing_type=sa.String(length=20),
        type_=sa.String(length=15),
        existing_nullable=False,
    )
