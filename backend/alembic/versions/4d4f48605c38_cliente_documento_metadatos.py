"""cliente_documentos: metadatos (numero, vigencia, notas)

Revision ID: 4d4f48605c38
Revises: e62672ae0db3
Create Date: 2026-06-13 00:00:00.000000

Al subir un contrato escaneado se captura número y vigencia.
"""
from alembic import op
import sqlalchemy as sa

revision = "4d4f48605c38"
down_revision = "e62672ae0db3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cliente_documentos", sa.Column("numero", sa.String(60), nullable=True))
    op.add_column("cliente_documentos", sa.Column("vigencia_desde", sa.Date(), nullable=True))
    op.add_column("cliente_documentos", sa.Column("vigencia_hasta", sa.Date(), nullable=True))
    op.add_column("cliente_documentos", sa.Column("notas", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cliente_documentos", "notas")
    op.drop_column("cliente_documentos", "vigencia_hasta")
    op.drop_column("cliente_documentos", "vigencia_desde")
    op.drop_column("cliente_documentos", "numero")
