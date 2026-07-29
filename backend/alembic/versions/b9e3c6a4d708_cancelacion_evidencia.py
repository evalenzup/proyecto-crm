"""facturas/pagos: evidencia de la solicitud de cancelación

Guarda lo que respondió el PAC (código y mensaje) y la ruta del acuse sellado
por el SAT que se descarga tras solicitar la cancelación. Sin esto no quedaba
ningún rastro de qué contestó el PAC ni prueba del trámite ante el SAT.

Revision ID: b9e3c6a4d708
Revises: a7d2f5b91c4e
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa


revision = "b9e3c6a4d708"
down_revision = "a7d2f5b91c4e"
branch_labels = None
depends_on = None

_TABLAS = ("facturas", "pagos")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.add_column(tabla, sa.Column("cancelacion_code", sa.String(10), nullable=True))
        op.add_column(tabla, sa.Column("cancelacion_message", sa.Text(), nullable=True))
        op.add_column(tabla, sa.Column("cancelacion_acuse_path", sa.String(255), nullable=True))


def downgrade() -> None:
    for tabla in _TABLAS:
        op.drop_column(tabla, "cancelacion_acuse_path")
        op.drop_column(tabla, "cancelacion_message")
        op.drop_column(tabla, "cancelacion_code")
