"""póliza de seguro: documentos de factura y complemento de pago

Revision ID: c7a1b4d9e2f5
Revises: b6e9c2f4a1d8
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa


revision = "c7a1b4d9e2f5"
down_revision = "b6e9c2f4a1d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("polizas_seguro", sa.Column("documento_factura", sa.String(255), nullable=True))
    op.add_column("polizas_seguro", sa.Column("documento_complemento", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("polizas_seguro", "documento_complemento")
    op.drop_column("polizas_seguro", "documento_factura")
