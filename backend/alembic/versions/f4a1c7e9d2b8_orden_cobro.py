"""ordenes_servicio: campos de cobro para ingresos no facturados

Agrega cobrado / fecha_cobro / forma_cobro para registrar el pago de órdenes
que no se facturan (las facturadas rastrean el pago vía la factura).

Revision ID: f4a1c7e9d2b8
Revises: e5c8b1f0a7d3
Create Date: 2026-07-28

"""
from alembic import op
import sqlalchemy as sa


revision = "f4a1c7e9d2b8"
down_revision = "e5c8b1f0a7d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ordenes_servicio",
        sa.Column("cobrado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("ordenes_servicio", sa.Column("fecha_cobro", sa.Date(), nullable=True))
    op.add_column("ordenes_servicio", sa.Column("forma_cobro", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("ordenes_servicio", "forma_cobro")
    op.drop_column("ordenes_servicio", "fecha_cobro")
    op.drop_column("ordenes_servicio", "cobrado")
