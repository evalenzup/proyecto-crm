"""Memoria de quién paga por quién

Revision ID: e7f2a04c8b19
Revises: d1b7c93e5a48
Create Date: 2026-08-24

Muchos depósitos los envía alguien distinto al cliente facturado —el dueño a
título personal, la matriz, un socio— y el nombre del ordenante no se parece
al del cliente. Caso real de junio: "260 GRADOS S DE RL DE CV" paga las
facturas de "RESTAURANTE 260"; ningún algoritmo une esos dos nombres solo.

Aquí se guarda esa equivalencia la primera vez que alguien la resuelve a mano,
para no volver a preguntarla. Es lo que hace que la conciliación mejore mes
con mes en lugar de empezar de cero cada vez.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e7f2a04c8b19"
down_revision = "d1b7c93e5a48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conciliacion_alias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("empresas.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        # Nombre del ordenante ya normalizado: sin acentos, sin razón social,
        # sin palabras vacías. Es la llave de búsqueda.
        sa.Column("ordenante", sa.String(200), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
        # Cuántas veces se ha confirmado; a más veces, más confianza
        sa.Column("veces", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "ordenante", "cliente_id",
                            name="uq_alias_ordenante_cliente"),
    )
    op.create_index("ix_alias_busqueda", "conciliacion_alias",
                    ["empresa_id", "ordenante"])


def downgrade() -> None:
    op.drop_index("ix_alias_busqueda", table_name="conciliacion_alias")
    op.drop_table("conciliacion_alias")
