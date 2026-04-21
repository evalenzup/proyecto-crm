"""add check constraint: supervisor must have empresa_id

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-04-10 13:00:00.000000

"""
from alembic import op

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOT VALID: el constraint se aplica solo a filas nuevas/actualizadas,
    # sin bloquear la tabla para validar las filas existentes.
    # Ejecutar VALIDATE CONSTRAINT manualmente cuando se quiera verificar datos históricos.
    op.execute("""
        ALTER TABLE usuarios
        ADD CONSTRAINT chk_supervisor_requiere_empresa
        CHECK (rol != 'SUPERVISOR' OR empresa_id IS NOT NULL)
        NOT VALID
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE usuarios
        DROP CONSTRAINT IF EXISTS chk_supervisor_requiere_empresa
    """)
