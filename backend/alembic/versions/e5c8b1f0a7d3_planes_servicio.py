"""planes de servicio (contratos) + orden.plan_id

Crea la tabla planes_servicio y agrega ordenes_servicio.plan_id para vincular
una orden al contrato que cumple.

Revision ID: e5c8b1f0a7d3
Revises: d3f7a9c1e5b2
Create Date: 2026-07-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "e5c8b1f0a7d3"
down_revision = "d3f7a9c1e5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planes_servicio",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=False, index=True),
        sa.Column("servicio_id", UUID(as_uuid=True), sa.ForeignKey("servicios_operativos.id"), nullable=True),
        sa.Column("tecnico_id", UUID(as_uuid=True), sa.ForeignKey("tecnicos.id"), nullable=True),
        sa.Column("vigencia_desde", sa.Date(), nullable=False),
        sa.Column("vigencia_hasta", sa.Date(), nullable=True),
        sa.Column("periodicidad", sa.String(20), nullable=False, server_default="MENSUAL"),
        sa.Column("dia_preferido", sa.Integer(), nullable=True),
        sa.Column("precio_pactado", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "certificado_id",
            UUID(as_uuid=True),
            sa.ForeignKey("certificados_servicio.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "ordenes_servicio",
        sa.Column(
            "plan_id",
            UUID(as_uuid=True),
            sa.ForeignKey("planes_servicio.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_ordenes_servicio_plan_id", "ordenes_servicio", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_ordenes_servicio_plan_id", table_name="ordenes_servicio")
    op.drop_column("ordenes_servicio", "plan_id")
    op.drop_table("planes_servicio")
