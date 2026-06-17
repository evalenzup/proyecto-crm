"""contrato: cimientos — campos de empresa/tecnico y tabla contratos

Revision ID: ad79fd2a8417
Revises: d8343f5efb96
Create Date: 2026-06-13 00:00:00.000000

Fase 0b (cimientos de datos): campos de prestador en Empresa, salario en
Tecnico y la tabla `contratos`. La generación del documento llega después.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "ad79fd2a8417"
down_revision = "d8343f5efb96"
branch_labels = None
depends_on = None

_JSON_TYPE = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    # ── Empresa: datos del prestador para el contrato ─────────────────────────
    op.add_column("empresas", sa.Column("representante_legal", sa.String(255), nullable=True))
    op.add_column("empresas", sa.Column("licencia_sanitaria", sa.String(100), nullable=True))
    op.add_column("empresas", sa.Column("registro_patronal", sa.String(50), nullable=True))
    op.add_column("empresas", sa.Column("repse_registro", sa.String(50), nullable=True))
    op.add_column("empresas", sa.Column("repse_aviso", sa.String(50), nullable=True))
    op.add_column("empresas", sa.Column("instrumento_notarial", sa.Text(), nullable=True))

    # ── Tecnico: salario base cotizable ───────────────────────────────────────
    op.add_column("tecnicos", sa.Column("salario_base_cotizable", sa.Numeric(12, 2), nullable=True))

    # ── Tabla contratos ───────────────────────────────────────────────────────
    op.create_table(
        "contratos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=False, index=True),
        sa.Column("presupuesto_id", UUID(as_uuid=True), sa.ForeignKey("presupuestos.id"), nullable=True, index=True),
        sa.Column("numero_contrato", sa.String(40), nullable=True),
        sa.Column("fecha_contrato", sa.Date(), nullable=True),
        sa.Column("vigencia_desde", sa.Date(), nullable=True),
        sa.Column("vigencia_hasta", sa.Date(), nullable=True),
        sa.Column("certificado_folio", sa.String(40), nullable=True),
        sa.Column("servicios", _JSON_TYPE, nullable=True),
        sa.Column("personal_asignado", _JSON_TYPE, nullable=True),
        sa.Column("exclusiones", sa.Text(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
        sa.Column("archivo_docx", sa.String(255), nullable=True),
        sa.Column("archivo_pdf", sa.String(255), nullable=True),
        sa.Column("creado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("contratos")
    op.drop_column("tecnicos", "salario_base_cotizable")
    op.drop_column("empresas", "instrumento_notarial")
    op.drop_column("empresas", "repse_aviso")
    op.drop_column("empresas", "repse_registro")
    op.drop_column("empresas", "registro_patronal")
    op.drop_column("empresas", "licencia_sanitaria")
    op.drop_column("empresas", "representante_legal")
