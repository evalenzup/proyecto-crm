"""bitácora: segunda opinión del PAC (consultarEstatusCFDI)

Revision ID: d3a8c15e7b92
Revises: c7d1f9a2b408
Create Date: 2026-08-19

Cuando nuestra consulta directa al SAT dice que no hay ninguna solicitud de
cancelación registrada, ahora se le pregunta lo mismo al PAC con su propio
método consultarEstatusCFDI —el que su soporte señala como la vía oficial para
confirmar el estatus— y se guarda lo que contesta.

Sirve para que la evidencia no dependa de una sola fuente: si su herramienta
contesta lo mismo que el SAT, el argumento de "consultaron mal" deja de existir.
"""
import sqlalchemy as sa
from alembic import op

revision = "d3a8c15e7b92"
down_revision = "c7d1f9a2b408"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cancelacion_intentos",
        sa.Column("pac_consulta_estado", sa.String(20), nullable=True),
    )
    op.add_column(
        "cancelacion_intentos",
        sa.Column("pac_consulta_estatus_cancelacion", sa.String(40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cancelacion_intentos", "pac_consulta_estatus_cancelacion")
    op.drop_column("cancelacion_intentos", "pac_consulta_estado")
