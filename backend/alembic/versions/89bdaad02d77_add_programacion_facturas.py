"""add_programacion_facturas

Revision ID: 89bdaad02d77
Revises: fa6e3d21b809
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "89bdaad02d77"
down_revision = "fa6e3d21b809"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "programacion_facturas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=False, index=True),
        # Datos fiscales
        sa.Column("serie", sa.String(10), nullable=True, server_default="A"),
        sa.Column("tipo_comprobante", sa.String(1), nullable=False, server_default="I"),
        sa.Column("forma_pago", sa.String(3), nullable=True),
        sa.Column("metodo_pago", sa.String(3), nullable=True),
        sa.Column("uso_cfdi", sa.String(3), nullable=True),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="MXN"),
        sa.Column("lugar_expedicion", sa.String(5), nullable=True),
        sa.Column("condiciones_pago", sa.Text, nullable=True),
        sa.Column("observaciones", sa.Text, nullable=True),
        sa.Column("retencion_local_desc", sa.String(100), nullable=True),
        sa.Column("retencion_local_tasa", sa.String(20), nullable=True),
        # Conceptos JSONB
        sa.Column("conceptos", postgresql.JSONB, nullable=False, server_default="[]"),
        # Programación
        sa.Column("periodicidad", sa.String(20), nullable=False, server_default="mensual"),
        sa.Column("proxima_ejecucion", sa.Date, nullable=False, index=True),
        sa.Column("fecha_fin", sa.Date, nullable=True),
        # Automatización
        sa.Column("auto_timbrar", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("auto_enviar", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("emails_destino", postgresql.JSONB, nullable=True, server_default="[]"),
        # Control
        sa.Column("nombre", sa.String(120), nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ultima_ejecucion", sa.DateTime, nullable=True),
        sa.Column("facturas_generadas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("programacion_facturas")
