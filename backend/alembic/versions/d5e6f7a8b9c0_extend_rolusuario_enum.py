"""extend rolusuario enum: superadmin, estandar, operativo

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-10 15:00:00.000000

NOTA: ALTER TYPE … ADD VALUE no puede ejecutarse dentro de un bloque de
transacción en PostgreSQL < 12. En PG 12+ sí puede, pero los nuevos valores
no son visibles hasta que la transacción hace COMMIT.  Por eso esta migración
SOLO agrega los valores; la siguiente (e6f7a8b9c0d1) crea las tablas y hace
la migración de datos, garantizando que los nuevos valores ya estén
comprometidos cuando se usan.
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE … ADD VALUE no puede ejecutarse dentro de una transacción abierta
    # en PostgreSQL. Usamos autocommit_block() (Alembic ≥1.4) para que cada
    # ADD VALUE se ejecute en modo autocommit y quede visible de inmediato.
    # El enum fue creado con valores en MAYÚSCULAS (ADMIN, SUPERVISOR);
    # mantenemos esa convención para los nuevos valores.
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'SUPERADMIN' BEFORE 'ADMIN'"
        ))
        op.execute(sa.text(
            "ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'ESTANDAR'"
        ))
        op.execute(sa.text(
            "ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'OPERATIVO'"
        ))


def downgrade() -> None:
    # PostgreSQL no soporta DROP VALUE en un enum.
    # Para revertir habría que recrear el tipo, lo cual es complejo y raro en producción.
    pass
