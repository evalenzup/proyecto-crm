"""facturas_detalle: corregir precisión de tasas a numeric(18,6)

Las columnas iva_tasa, ret_iva_tasa y ret_isr_tasa estaban como numeric(6,4)
(solo 4 decimales), lo que truncaba tasas como 0.053333 (5.3333%) a 0.0533,
provocando inconsistencias de redondeo al timbrar (CFDI40119 / impuestos).

Revision ID: f1c4a8e6b3d7
Revises: e3a7c1b9d2f4
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa


revision = "f1c4a8e6b3d7"
down_revision = "e3a7c1b9d2f4"
branch_labels = None
depends_on = None

_COLS = ["iva_tasa", "ret_iva_tasa", "ret_isr_tasa"]


def upgrade() -> None:
    for col in _COLS:
        op.alter_column(
            "facturas_detalle", col,
            type_=sa.Numeric(18, 6),
            existing_nullable=True,
        )


def downgrade() -> None:
    for col in _COLS:
        op.alter_column(
            "facturas_detalle", col,
            type_=sa.Numeric(6, 4),
            existing_nullable=True,
        )
