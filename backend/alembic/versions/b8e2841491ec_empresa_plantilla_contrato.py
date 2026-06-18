"""empresa: plantilla_contrato (formato de contrato por empresa)

Revision ID: b8e2841491ec
Revises: ad79fd2a8417
Create Date: 2026-06-13 00:00:00.000000

Cada empresa tiene su propio formato de contrato (plantilla docxtpl).
"""
from alembic import op
import sqlalchemy as sa

revision = "b8e2841491ec"
down_revision = "ad79fd2a8417"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("empresas", sa.Column("plantilla_contrato", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("empresas", "plantilla_contrato")
