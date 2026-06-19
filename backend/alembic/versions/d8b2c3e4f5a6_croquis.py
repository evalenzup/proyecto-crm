"""croquis por cliente (configurable por empresa)

Revision ID: d8b2c3e4f5a6
Revises: c7f1a2b3d4e5
Create Date: 2026-06-18 00:00:00.000000

Tabla de croquis (planos) por cliente: general o por área, con archivo PDF.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "d8b2c3e4f5a6"
down_revision = "c7f1a2b3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "croquis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("area", sa.String(length=150), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("archivo", sa.String(length=255), nullable=False),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_croquis_empresa_id", "croquis", ["empresa_id"])
    op.create_index("ix_croquis_cliente_id", "croquis", ["cliente_id"])


def downgrade() -> None:
    op.drop_table("croquis")
