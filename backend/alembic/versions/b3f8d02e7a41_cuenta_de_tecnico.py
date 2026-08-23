"""Liga una cuenta de usuario con un técnico

Revision ID: b3f8d02e7a41
Revises: e5b2071c9a34
Create Date: 2026-08-23

Los usuarios y los técnicos eran dos tablas sin relación, así que no había forma
de darle acceso a un técnico para que viera su propia agenda. Con esta columna
una cuenta con rol OPERATIVO queda asociada a su ficha de técnico y el sistema
puede filtrarle las órdenes donde él es el asignado.

Único: una ficha de técnico no puede tener dos cuentas.
"""
from alembic import op
import sqlalchemy as sa

revision = "b3f8d02e7a41"
down_revision = "e5b2071c9a34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("tecnico_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_usuarios_tecnico", "usuarios", "tecnicos", ["tecnico_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_usuarios_tecnico", "usuarios", ["tecnico_id"])


def downgrade() -> None:
    op.drop_constraint("uq_usuarios_tecnico", "usuarios", type_="unique")
    op.drop_constraint("fk_usuarios_tecnico", "usuarios", type_="foreignkey")
    op.drop_column("usuarios", "tecnico_id")
