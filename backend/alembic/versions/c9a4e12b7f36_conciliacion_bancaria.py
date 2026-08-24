"""Conciliación bancaria: estados de cuenta y su cotejo con las facturas

Revision ID: c9a4e12b7f36
Revises: b3f8d02e7a41
Create Date: 2026-08-24

Cristal concilia hoy a mano en Excel: baja el estado de cuenta, escribe al lado
de cada depósito los folios que lo componen, marca a qué área corresponde cada
gasto y se lo manda a la contadora. Estas tablas mueven ese trabajo al sistema
sin cambiarle la forma de trabajar.

- conciliaciones_bancarias: un mes, con el PDF original archivado. Se conserva
  porque es el documento que respalda el trabajo ante la contadora.
- movimientos_bancarios: cada línea del estado de cuenta, más las dos columnas
  que ella agrega (comentario y área).
- movimiento_facturas: qué facturas componen un movimiento. Es de muchos a
  muchos a propósito: un depósito en efectivo puede pagar seis facturas, y una
  factura puede llegar en varias exhibiciones — los dos casos existen en junio.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c9a4e12b7f36"
down_revision = "b3f8d02e7a41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conciliaciones_bancarias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fin", sa.Date(), nullable=False),
        sa.Column("banco", sa.String(50), nullable=False, server_default="BANAMEX"),
        sa.Column("cuenta", sa.String(50), nullable=True),
        # El PDF original, archivado
        sa.Column("archivo_nombre", sa.String(255), nullable=True),
        sa.Column("archivo_path", sa.String(500), nullable=True),
        # Totales que declara el propio banco; el importador los usa para validar
        sa.Column("saldo_inicial", sa.Numeric(14, 2), nullable=False),
        sa.Column("saldo_final", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_depositos", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_retiros", sa.Numeric(14, 2), nullable=False),
        sa.Column("n_depositos", sa.Integer(), nullable=False),
        sa.Column("n_retiros", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="EN_PROCESO"),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        # Un mismo periodo y cuenta no se importa dos veces
        sa.UniqueConstraint("empresa_id", "cuenta", "periodo_inicio", "periodo_fin",
                            name="uq_concil_periodo"),
    )

    op.create_table(
        "movimientos_bancarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conciliacion_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("conciliaciones_bancarias.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        # orden respeta la secuencia del estado de cuenta; es como ella lo lee
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False, index=True),
        sa.Column("concepto", sa.Text(), nullable=False),
        sa.Column("deposito", sa.Numeric(14, 2), nullable=True),
        sa.Column("retiro", sa.Numeric(14, 2), nullable=True),
        # Las dos columnas que agrega Cristal
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("area", sa.String(20), nullable=True),   # A, F, J, L o combinaciones
        sa.Column("conciliado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "movimiento_facturas",
        sa.Column("movimiento_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("movimientos_bancarios.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("factura_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("facturas.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("movimiento_facturas")
    op.drop_table("movimientos_bancarios")
    op.drop_table("conciliaciones_bancarias")
