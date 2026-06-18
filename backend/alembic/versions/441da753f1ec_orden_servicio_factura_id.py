"""orden_servicio: factura_id (vínculo orden ↔ factura)

Revision ID: 441da753f1ec
Revises: 4d4f48605c38
Create Date: 2026-06-13 00:00:00.000000

Una orden puede vincularse a una factura (1:1). ON DELETE SET NULL para no
perder la orden si se borra la factura.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "441da753f1ec"
down_revision = "4d4f48605c38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ordenes_servicio",
        sa.Column("factura_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ordenes_servicio_factura_id", "ordenes_servicio", ["factura_id"])
    op.create_foreign_key(
        "fk_ordenes_servicio_factura_id",
        "ordenes_servicio", "facturas",
        ["factura_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ordenes_servicio_factura_id", "ordenes_servicio", type_="foreignkey")
    op.drop_index("ix_ordenes_servicio_factura_id", table_name="ordenes_servicio")
    op.drop_column("ordenes_servicio", "factura_id")
