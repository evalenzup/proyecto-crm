"""cliente: campos de contrato (representante_legal, escritura_publica) y tabla cliente_documentos

Revision ID: d8343f5efb96
Revises: a7b8c9d0e1f2
Create Date: 2026-06-13 00:00:00.000000

Fase 0a: datos de contrato del cliente y adjuntos de documentos.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "d8343f5efb96"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("representante_legal", sa.String(255), nullable=True))
    op.add_column("clientes", sa.Column("escritura_publica", sa.String(255), nullable=True))

    op.create_table(
        "cliente_documentos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tipo", sa.String(40), nullable=False, server_default="OTRO"),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("archivo", sa.String(255), nullable=False),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cliente_documentos")
    op.drop_column("clientes", "escritura_publica")
    op.drop_column("clientes", "representante_legal")
