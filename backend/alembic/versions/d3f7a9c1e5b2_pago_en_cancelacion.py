"""pagos: estado EN_CANCELACION y fecha de solicitud de cancelación

Da a los complementos de pago la misma capacidad que ya tienen las facturas
para representar una cancelación solicitada pero aún no confirmada por el SAT
(p. ej. motivo 01, pendiente de aceptación del receptor). Sin este estado, el
sistema marcaba CANCELADO de inmediato y quedaba desfasado del SAT.

Revision ID: d3f7a9c1e5b2
Revises: c7a1b4d9e2f5
Create Date: 2026-07-22

"""
from alembic import op
import sqlalchemy as sa


revision = "d3f7a9c1e5b2"
down_revision = "c7a1b4d9e2f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE no puede ejecutarse dentro del bloque
    # transaccional de Alembic: requiere autocommit.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE estatuspago ADD VALUE IF NOT EXISTS 'EN_CANCELACION'")

    op.add_column(
        "pagos",
        sa.Column("fecha_solicitud_cancelacion", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pagos", "fecha_solicitud_cancelacion")
    # Postgres no permite eliminar un valor de un ENUM; se deja el valor
    # EN_CANCELACION en el tipo (inofensivo si ya no se usa).
