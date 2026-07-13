"""certificados de servicio (aplicación de plaguicidas / sanitización)

Revision ID: a2d5e8f1c3b6
Revises: f1c4a8e6b3d7
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "a2d5e8f1c3b6"
down_revision = "f1c4a8e6b3d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificados_servicio",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="PLAGUICIDAS"),
        sa.Column("folio", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("nombre_razon_social", sa.String(255), nullable=False),
        sa.Column("domicilio", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("actividad", sa.String(255), nullable=True),
        sa.Column("areas", JSONB(), nullable=True),
        sa.Column("plagas", JSONB(), nullable=True),
        sa.Column("aplicaciones", JSONB(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("gerente_nombre", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "tipo", "folio", name="uq_certserv_folio_por_empresa_tipo"),
    )
    op.create_index("ix_certserv_empresa", "certificados_servicio", ["empresa_id"])
    op.create_index("ix_certserv_cliente", "certificados_servicio", ["cliente_id"])


def downgrade() -> None:
    op.drop_index("ix_certserv_cliente", table_name="certificados_servicio")
    op.drop_index("ix_certserv_empresa", table_name="certificados_servicio")
    op.drop_table("certificados_servicio")
