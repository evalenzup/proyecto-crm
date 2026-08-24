"""Enlazar egresos a los retiros del estado de cuenta

Revision ID: d1b7c93e5a48
Revises: c9a4e12b7f36
Create Date: 2026-08-24

Los depósitos se cotejan contra facturas y los retiros contra egresos, pero
sólo existía la tabla de facturas. Sin ésta, un cargo sólo se podía anotar a
mano aunque el gasto ya estuviera capturado en el sistema.

Muchos a muchos por lo mismo que las facturas: un cargo puede cubrir varios
gastos y un gasto puede pagarse en partes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d1b7c93e5a48"
down_revision = "c9a4e12b7f36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movimiento_egresos",
        sa.Column("movimiento_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("movimientos_bancarios.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("egreso_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("egresos.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("movimiento_egresos")
