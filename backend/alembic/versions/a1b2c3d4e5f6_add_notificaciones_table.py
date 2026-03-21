"""add_notificaciones_table

Revision ID: a1b2c3d4e5f6
Revises: f51db8305cba
Create Date: 2026-03-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f51db8305cba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notificaciones',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('empresa_id', sa.UUID(), nullable=False),
        sa.Column('usuario_id', sa.UUID(), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('leida', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('creada_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notificaciones_empresa_id', 'notificaciones', ['empresa_id'])
    op.create_index('ix_notificaciones_usuario_id', 'notificaciones', ['usuario_id'])
    op.create_index('ix_notificaciones_creada_en', 'notificaciones', ['creada_en'])


def downgrade() -> None:
    op.drop_index('ix_notificaciones_creada_en', table_name='notificaciones')
    op.drop_index('ix_notificaciones_usuario_id', table_name='notificaciones')
    op.drop_index('ix_notificaciones_empresa_id', table_name='notificaciones')
    op.drop_table('notificaciones')
