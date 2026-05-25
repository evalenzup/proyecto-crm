"""add_ordenes_servicio

Revision ID: fa6e3d21b809
Revises: e4f5a6b7c8d9
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fa6e3d21b809"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ordenes_servicio ──────────────────────────────────────────────────────
    op.create_table(
        "ordenes_servicio",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=False, index=True),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tecnicos.id"), nullable=True, index=True),
        sa.Column("unidad_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("unidades.id"), nullable=True, index=True),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("servicios_operativos.id"), nullable=True),
        sa.Column("presupuesto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("presupuestos.id"), nullable=True),
        # Folio
        sa.Column("folio_os", sa.String(20), nullable=False, index=True),
        # Programación
        sa.Column("fecha_programada", sa.Date, nullable=False, index=True),
        sa.Column("hora_inicio", sa.Time, nullable=True),
        sa.Column("hora_fin", sa.Time, nullable=True),
        sa.Column("duracion_minutos", sa.Integer, nullable=True),
        # Estado y prioridad
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("prioridad", sa.String(10), nullable=False, server_default="MEDIA"),
        # Ubicación
        sa.Column("direccion_servicio", sa.Text, nullable=True),
        sa.Column("latitud", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitud", sa.Numeric(10, 7), nullable=True),
        # Financiero
        sa.Column("precio_acordado", sa.Numeric(12, 2), nullable=True),
        # Notas
        sa.Column("notas_tecnico", sa.Text, nullable=True),
        sa.Column("notas_internas", sa.Text, nullable=True),
        sa.Column("notas_cierre", sa.Text, nullable=True),
        # Control
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── historial_estados_os ──────────────────────────────────────────────────
    op.create_table(
        "historial_estados_os",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "orden_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ordenes_servicio.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("estado_anterior", sa.String(20), nullable=True),
        sa.Column("estado_nuevo", sa.String(20), nullable=False),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("historial_estados_os")
    op.drop_table("ordenes_servicio")
