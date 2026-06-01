"""fix folio unique per empresa en ordenes_servicio y pagos

Revision ID: bc2d3e4f5a67
Revises: ab1c2d3e4f56
Create Date: 2026-06-01 00:00:00.000000

El folio de órdenes de servicio y pagos no tenía ningún constraint único,
lo que permitía duplicados. Se agrega UniqueConstraint(folio, empresa_id)
en ambas tablas para que cada empresa tenga su propia secuencia independiente.
"""

from alembic import op

revision = 'bc2d3e4f5a67'
down_revision = 'ab1c2d3e4f56'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Órdenes de servicio
    op.create_unique_constraint(
        'uq_os_folio_empresa',
        'ordenes_servicio',
        ['folio_os', 'empresa_id'],
    )
    # Pagos
    op.create_unique_constraint(
        'uq_pago_folio_empresa',
        'pagos',
        ['folio', 'empresa_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_os_folio_empresa', 'ordenes_servicio', type_='unique')
    op.drop_constraint('uq_pago_folio_empresa', 'pagos', type_='unique')
