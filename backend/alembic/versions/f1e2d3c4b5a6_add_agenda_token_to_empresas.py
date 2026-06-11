"""add_agenda_token_to_empresas

Revision ID: f1e2d3c4b5a6
Revises: bc2d3e4f5a67
Create Date: 2026-06-01 00:00:00.000000

Seguridad: reemplaza empresa_id como único gate de la agenda pública
por un token rotable independiente.
"""
from alembic import op
import sqlalchemy as sa

revision = "f1e2d3c4b5a6"
down_revision = "bc2d3e4f5a67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agrega columna nullable primero para poder poblar filas existentes
    op.add_column(
        "empresas",
        sa.Column("agenda_token", sa.String(64), nullable=True),
    )

    # Genera un token único para cada empresa ya existente.
    # Usamos md5(random()::text || id::text) x2 para 64 chars hex sin depender de pgcrypto.
    op.execute(
        """
        UPDATE empresas
        SET agenda_token = md5(random()::text || id::text || clock_timestamp()::text)
                        || md5(random()::text || id::text || clock_timestamp()::text)
        WHERE agenda_token IS NULL
        """
    )

    # Aplica NOT NULL y UNIQUE ahora que todas las filas tienen valor
    op.alter_column("empresas", "agenda_token", nullable=False)
    op.create_unique_constraint(
        "uq_empresas_agenda_token", "empresas", ["agenda_token"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_empresas_agenda_token", "empresas", type_="unique")
    op.drop_column("empresas", "agenda_token")
