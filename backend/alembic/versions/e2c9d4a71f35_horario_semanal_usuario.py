"""Horario distinto por día de la semana

Revision ID: e2c9d4a71f35
Revises: d8b2a5f31c60
Create Date: 2026-08-10

El horario único (horario_inicio/horario_fin + dias_laborales) no alcanza para
jornadas como "lunes a viernes completo y sábado medio día". Se agrega un mapa
opcional por día que, cuando está presente, manda sobre los campos simples.

Formato: {"1": ["08:00", "18:00"], ..., "6": ["08:00", "14:00"]}
donde la llave es el día ISO (1=lunes … 7=domingo). Un día ausente del mapa
significa que ese día no tiene acceso.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e2c9d4a71f35"
down_revision = "d8b2a5f31c60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("horario_semanal", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "horario_semanal")
