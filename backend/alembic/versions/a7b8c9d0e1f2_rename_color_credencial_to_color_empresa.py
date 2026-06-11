"""rename_color_credencial_to_color_empresa

Revision ID: a7b8c9d0e1f2
Revises: f1e2d3c4b5a6
Create Date: 2026-06-09 00:00:00.000000

El campo deja de ser exclusivo de la credencial PDF: ahora es el color
de marca de la empresa (credenciales, agenda pública y tema del ERP).
"""
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("empresas", "color_credencial", new_column_name="color_empresa")


def downgrade() -> None:
    op.alter_column("empresas", "color_empresa", new_column_name="color_credencial")
