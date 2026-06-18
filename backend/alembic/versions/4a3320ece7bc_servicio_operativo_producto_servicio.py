"""servicio_operativo: vínculo a producto_servicio (claves SAT para facturar)

Revision ID: 4a3320ece7bc
Revises: 441da753f1ec
Create Date: 2026-06-18 00:00:00.000000

Opción B: cada Tipo de Servicio puede apuntar a un Producto/Servicio fiscal,
de donde salen las claves SAT al crear factura desde una orden.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "4a3320ece7bc"
down_revision = "441da753f1ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "servicios_operativos",
        sa.Column("producto_servicio_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_servicios_operativos_producto_servicio_id",
        "servicios_operativos", ["producto_servicio_id"],
    )
    op.create_foreign_key(
        "fk_servicios_operativos_producto_servicio_id",
        "servicios_operativos", "productos_servicios",
        ["producto_servicio_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_servicios_operativos_producto_servicio_id", "servicios_operativos", type_="foreignkey")
    op.drop_index("ix_servicios_operativos_producto_servicio_id", table_name="servicios_operativos")
    op.drop_column("servicios_operativos", "producto_servicio_id")
