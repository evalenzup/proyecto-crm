"""contrato: datos genéricos por placeholder (reemplaza servicios fijos)

Revision ID: e62672ae0db3
Revises: b8e2841491ec
Create Date: 2026-06-13 00:00:00.000000

Los valores manuales del contrato dejan de ser campos fijos (fumigacion,
sanitizacion, combo) y pasan a un dict genérico keyed por placeholder de la
plantilla de cada empresa.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "e62672ae0db3"
down_revision = "b8e2841491ec"
branch_labels = None
depends_on = None

_JSON_TYPE = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("contratos", sa.Column("datos", _JSON_TYPE, nullable=True))
    # 'servicios' queda en desuso (no se elimina para no perder datos existentes)


def downgrade() -> None:
    op.drop_column("contratos", "datos")
