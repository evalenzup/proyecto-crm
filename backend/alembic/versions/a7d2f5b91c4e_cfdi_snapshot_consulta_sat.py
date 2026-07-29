"""facturas/pagos: snapshot del CFDI para consultar al SAT

Guarda el RFC del emisor, el RFC del receptor y el Total tal como quedaron en
el XML timbrado. La consulta al SAT usaba los valores actuales de la BD, que
cambian (cliente que cambia de RFC, total recalculado) y hacen fallar la
consulta con "601: la expresión impresa no es válida".

Revision ID: a7d2f5b91c4e
Revises: f4a1c7e9d2b8
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa


revision = "a7d2f5b91c4e"
down_revision = "f4a1c7e9d2b8"
branch_labels = None
depends_on = None

_TABLAS = ("facturas", "pagos")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.add_column(tabla, sa.Column("cfdi_rfc_emisor", sa.String(13), nullable=True))
        op.add_column(tabla, sa.Column("cfdi_rfc_receptor", sa.String(13), nullable=True))
        op.add_column(tabla, sa.Column("cfdi_total", sa.Numeric(18, 6), nullable=True))


def downgrade() -> None:
    for tabla in _TABLAS:
        op.drop_column(tabla, "cfdi_total")
        op.drop_column(tabla, "cfdi_rfc_receptor")
        op.drop_column(tabla, "cfdi_rfc_emisor")
