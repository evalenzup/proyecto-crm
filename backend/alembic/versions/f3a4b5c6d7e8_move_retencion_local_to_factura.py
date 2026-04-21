"""move retencion_local fields from empresas to facturas

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-04-09 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a4b5c6d7e8'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Quitar de empresas
    op.drop_column('empresas', 'retencion_local_desc')
    op.drop_column('empresas', 'retencion_local_tasa')

    # Agregar a facturas (configuración por factura)
    op.add_column('facturas', sa.Column(
        'retencion_local_desc',
        sa.String(100),
        nullable=True,
        comment='Etiqueta SAT del impuesto local, ej. "5 AL MILLAR"'
    ))
    op.add_column('facturas', sa.Column(
        'retencion_local_tasa',
        sa.Numeric(10, 6),
        nullable=True,
        comment='Tasa como valor directo para TasadeRetencion en XML, ej. 0.050000'
    ))


def downgrade() -> None:
    op.drop_column('facturas', 'retencion_local_tasa')
    op.drop_column('facturas', 'retencion_local_desc')
    op.add_column('empresas', sa.Column('retencion_local_tasa', sa.Numeric(10, 6), nullable=True))
    op.add_column('empresas', sa.Column('retencion_local_desc', sa.String(100), nullable=True))
