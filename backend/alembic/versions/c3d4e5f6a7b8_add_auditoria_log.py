"""add_auditoria_log

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auditoria_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('empresa_id', sa.UUID(), nullable=True),
        sa.Column('usuario_id', sa.UUID(), nullable=True),
        sa.Column('usuario_email', sa.String(length=255), nullable=True),
        sa.Column('accion', sa.String(length=60), nullable=False),
        sa.Column('entidad', sa.String(length=50), nullable=False),
        sa.Column('entidad_id', sa.String(length=36), nullable=True),
        sa.Column('detalle', sa.Text(), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auditoria_empresa_id', 'auditoria_log', ['empresa_id'])
    op.create_index('ix_auditoria_usuario_id', 'auditoria_log', ['usuario_id'])
    op.create_index('ix_auditoria_accion', 'auditoria_log', ['accion'])
    op.create_index('ix_auditoria_entidad', 'auditoria_log', ['entidad'])
    op.create_index('ix_auditoria_creado_en', 'auditoria_log', ['creado_en'])


def downgrade() -> None:
    op.drop_index('ix_auditoria_creado_en', table_name='auditoria_log')
    op.drop_index('ix_auditoria_entidad', table_name='auditoria_log')
    op.drop_index('ix_auditoria_accion', table_name='auditoria_log')
    op.drop_index('ix_auditoria_usuario_id', table_name='auditoria_log')
    op.drop_index('ix_auditoria_empresa_id', table_name='auditoria_log')
    op.drop_table('auditoria_log')
