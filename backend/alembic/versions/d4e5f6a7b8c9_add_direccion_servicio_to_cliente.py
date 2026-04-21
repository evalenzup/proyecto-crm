"""add_direccion_servicio_to_cliente

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clientes', sa.Column('serv_calle', sa.String(100), nullable=True))
    op.add_column('clientes', sa.Column('serv_numero_exterior', sa.String(50), nullable=True))
    op.add_column('clientes', sa.Column('serv_numero_interior', sa.String(50), nullable=True))
    op.add_column('clientes', sa.Column('serv_colonia', sa.String(100), nullable=True))
    op.add_column('clientes', sa.Column('serv_codigo_postal', sa.String(10), nullable=True))
    op.add_column('clientes', sa.Column('serv_referencia', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('clientes', 'serv_referencia')
    op.drop_column('clientes', 'serv_codigo_postal')
    op.drop_column('clientes', 'serv_colonia')
    op.drop_column('clientes', 'serv_numero_interior')
    op.drop_column('clientes', 'serv_numero_exterior')
    op.drop_column('clientes', 'serv_calle')
