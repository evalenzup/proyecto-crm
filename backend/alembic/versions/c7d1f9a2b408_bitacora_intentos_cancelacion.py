"""bitácora de intentos de cancelación ante el SAT

Revision ID: c7d1f9a2b408
Revises: a4e7c2b95d13
Create Date: 2026-08-19

Las columnas cancelacion_code / cancelacion_message / cancelacion_acuse_path de
facturas y pagos guardan sólo el último intento y se sobrescriben en cada
reintento. Con eso no se puede reconstruir qué pasó ni responder la pregunta de
fondo que quedó abierta con el PAC: ¿con qué frecuencia Facturación Moderna
acusa recibo de una solicitud que nunca transmitió al SAT?

Esta tabla guarda un renglón por envío, con lo que contestó el PAC, lo que
decía el SAT en ese mismo instante, si el acuse sellado existió o no, y cómo
terminó el trámite.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "c7d1f9a2b408"
down_revision = "a4e7c2b95d13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cancelacion_intentos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), nullable=False),
        # Sin ForeignKey: apunta indistintamente a facturas o a pagos.
        sa.Column("documento_tipo", sa.String(10), nullable=False),
        sa.Column("documento_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cfdi_uuid", sa.String(36), nullable=False),
        sa.Column("documento_folio", sa.String(30), nullable=True),
        sa.Column("fecha_envio", sa.DateTime(), nullable=False),
        sa.Column("motivo", sa.String(2), nullable=True),
        sa.Column("folio_sustitucion", sa.String(36), nullable=True),
        sa.Column("origen", sa.String(20), nullable=False, server_default="SISTEMA"),
        sa.Column("pac_code", sa.String(10), nullable=True),
        sa.Column("pac_message", sa.Text(), nullable=True),
        sa.Column("pac_codigo_conocido", sa.Boolean(), nullable=True),
        sa.Column("sat_estado", sa.String(20), nullable=True),
        sa.Column("sat_es_cancelable", sa.String(40), nullable=True),
        sa.Column("sat_estatus_cancelacion", sa.String(40), nullable=True),
        sa.Column("sat_registro_solicitud", sa.Boolean(), nullable=True),
        sa.Column("acuse_path", sa.String(255), nullable=True),
        sa.Column("acuse_error", sa.Text(), nullable=True),
        sa.Column("resultado", sa.String(20), nullable=True),
        sa.Column("fecha_resultado", sa.DateTime(), nullable=True),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cancelacion_intentos_empresa_id", "cancelacion_intentos", ["empresa_id"]
    )
    op.create_index(
        "ix_cancelacion_intentos_documento_id", "cancelacion_intentos", ["documento_id"]
    )
    op.create_index(
        "ix_cancelacion_intentos_cfdi_uuid", "cancelacion_intentos", ["cfdi_uuid"]
    )
    op.create_index(
        "ix_cancelacion_intentos_fecha_envio", "cancelacion_intentos", ["fecha_envio"]
    )
    op.create_index(
        "ix_cancel_intentos_doc",
        "cancelacion_intentos",
        ["documento_tipo", "documento_id"],
    )
    op.create_index(
        "ix_cancel_intentos_abiertos",
        "cancelacion_intentos",
        ["documento_id", "resultado"],
    )


def downgrade() -> None:
    op.drop_index("ix_cancel_intentos_abiertos", table_name="cancelacion_intentos")
    op.drop_index("ix_cancel_intentos_doc", table_name="cancelacion_intentos")
    op.drop_index("ix_cancelacion_intentos_fecha_envio", table_name="cancelacion_intentos")
    op.drop_index("ix_cancelacion_intentos_cfdi_uuid", table_name="cancelacion_intentos")
    op.drop_index("ix_cancelacion_intentos_documento_id", table_name="cancelacion_intentos")
    op.drop_index("ix_cancelacion_intentos_empresa_id", table_name="cancelacion_intentos")
    op.drop_table("cancelacion_intentos")
