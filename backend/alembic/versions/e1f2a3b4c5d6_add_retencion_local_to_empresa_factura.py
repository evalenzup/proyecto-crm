"""add retencion_local to empresa and factura

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Campos de retención local en empresa (configuración)
    op.add_column('empresas', sa.Column(
        'retencion_local_desc',
        sa.String(100),
        nullable=True,
        comment='Etiqueta SAT del impuesto local, ej. "5 AL MILLAR"'
    ))
    op.add_column('empresas', sa.Column(
        'retencion_local_tasa',
        sa.Numeric(10, 6),
        nullable=True,
        comment='Tasa como porcentaje para XML, ej. 0.050000 para 0.05%'
    ))

    # Monto calculado en factura (se llena al generar el CFDI)
    op.add_column('facturas', sa.Column(
        'retencion_local_monto',
        sa.Numeric(20, 6),
        nullable=True,
        comment='Importe de retención local calculado al timbrar'
    ))


def downgrade() -> None:
    op.drop_column('facturas', 'retencion_local_monto')
    op.drop_column('empresas', 'retencion_local_tasa')
    op.drop_column('empresas', 'retencion_local_desc')
