"""Restricciones de acceso por usuario: horario, IP y borrado

Revision ID: d8b2a5f31c60
Revises: c1f4e07b2d95
Create Date: 2026-08-07

Permite acotar a un usuario sin cambiarle el rol: limitarlo al horario laboral,
a las IP de las instalaciones y quitarle la facultad de eliminar registros.
Todas las columnas son opcionales y el comportamiento por defecto no cambia
para los usuarios existentes.
"""
from alembic import op
import sqlalchemy as sa

revision = "d8b2a5f31c60"
down_revision = "c1f4e07b2d95"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("puede_eliminar", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
    )
    # Horario permitido (hora local de México). NULL = sin restricción.
    op.add_column("usuarios", sa.Column("horario_inicio", sa.Time(), nullable=True))
    op.add_column("usuarios", sa.Column("horario_fin", sa.Time(), nullable=True))
    # Días laborales en formato ISO: 1=lunes … 7=domingo, separados por coma.
    op.add_column("usuarios", sa.Column("dias_laborales", sa.String(20), nullable=True))
    # IPs o rangos CIDR permitidos, separados por coma. NULL = desde cualquier lado.
    op.add_column("usuarios", sa.Column("ips_permitidas", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "ips_permitidas")
    op.drop_column("usuarios", "dias_laborales")
    op.drop_column("usuarios", "horario_fin")
    op.drop_column("usuarios", "horario_inicio")
    op.drop_column("usuarios", "puede_eliminar")
