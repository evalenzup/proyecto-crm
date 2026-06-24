"""unidad: comprobante de pago de la tarjeta de circulación

Revision ID: e3a7c1b9d2f4
Revises: d8b2c3e4f5a6
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e3a7c1b9d2f4"
down_revision = "d8b2c3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unidades",
        sa.Column("doc_comprobante_pago_tc", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("unidades", "doc_comprobante_pago_tc")
