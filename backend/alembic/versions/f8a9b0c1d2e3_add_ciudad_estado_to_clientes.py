"""add ciudad y estado a direccion fiscal y de servicio en clientes

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-05-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dirección fiscal
    op.add_column("clientes", sa.Column("ciudad", sa.String(100), nullable=True))
    op.add_column("clientes", sa.Column("estado", sa.String(100), nullable=True))
    # Dirección de servicio
    op.add_column("clientes", sa.Column("serv_ciudad", sa.String(100), nullable=True))
    op.add_column("clientes", sa.Column("serv_estado", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "serv_estado")
    op.drop_column("clientes", "serv_ciudad")
    op.drop_column("clientes", "estado")
    op.drop_column("clientes", "ciudad")
