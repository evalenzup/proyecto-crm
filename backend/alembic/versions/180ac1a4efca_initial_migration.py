"""Initial migration

Revision ID: 180ac1a4efca
Revises: 
Create Date: 2025-07-22 02:03:10.308593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '180ac1a4efca'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('clientes', 'uso_cfdi')
    op.drop_column('clientes', 'regimen_fiscal_receptor')
    op.drop_column('clientes', 'num_reg_id_trib')
    op.drop_column('clientes', 'residencia_fiscal')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clientes', sa.Column('residencia_fiscal', sa.VARCHAR(length=5), autoincrement=False, nullable=True))
    op.add_column('clientes', sa.Column('num_reg_id_trib', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.add_column('clientes', sa.Column('regimen_fiscal_receptor', sa.VARCHAR(length=100), autoincrement=False, nullable=False))
    op.add_column('clientes', sa.Column('uso_cfdi', sa.VARCHAR(length=50), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
