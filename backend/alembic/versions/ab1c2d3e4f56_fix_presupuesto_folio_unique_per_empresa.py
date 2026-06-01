"""fix presupuesto folio unique per empresa

Revision ID: ab1c2d3e4f56
Revises: fa6e3d21b809
Create Date: 2026-06-01 00:00:00.000000

El folio de presupuesto tenía unique=True global, lo que impedía que dos
empresas distintas tuvieran el mismo folio (ej. ambas con PRE-2026-0001).
Se reemplaza por un unique constraint compuesto (folio, empresa_id).
"""

from alembic import op

# revision identifiers
revision = 'ab1c2d3e4f56'
down_revision = '89bdaad02d77'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Eliminar el constraint único global en folio
    op.drop_constraint('presupuestos_folio_key', 'presupuestos', type_='unique')
    # Crear constraint único compuesto (folio, empresa_id)
    op.create_unique_constraint(
        'uq_presupuesto_folio_empresa',
        'presupuestos',
        ['folio', 'empresa_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_presupuesto_folio_empresa', 'presupuestos', type_='unique')
    op.create_unique_constraint('presupuestos_folio_key', 'presupuestos', ['folio'])
