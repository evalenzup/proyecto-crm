"""presupuestos: el folio es único por empresa Y versión

Revision ID: a4e7c2b95d13
Revises: f7a3b81d6e42
Create Date: 2026-08-18

El módulo versiona un presupuesto creando una fila nueva con el MISMO folio y
la versión incrementada (presupuesto_service.update). La restricción anterior,
UNIQUE (folio, empresa_id), hacía imposible esa segunda fila: el usuario recibía
"Ya existe un registro con esos datos" al guardar cualquier cambio.

La restricción se declaró en junio pero en producción no llegó a existir hasta
que la migración c1f4e07b2d95 la creó explícitamente, y ahí empezó a doler.

La llave correcta incluye la versión. Sigue impidiendo que dos presupuestos
distintos de una misma empresa compartan folio, porque ambos nacen en versión 1.
"""
from alembic import op

revision = "a4e7c2b95d13"
down_revision = "f7a3b81d6e42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE presupuestos DROP CONSTRAINT IF EXISTS uq_presupuesto_folio_empresa"
    )
    # Restos de esquemas anteriores, por si quedaran en algún entorno.
    op.execute("ALTER TABLE presupuestos DROP CONSTRAINT IF EXISTS presupuestos_folio_key")
    op.execute("ALTER TABLE presupuestos DROP CONSTRAINT IF EXISTS presupuestos_folio_key1")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_presupuesto_folio_empresa_version'
            ) THEN
                ALTER TABLE presupuestos
                    ADD CONSTRAINT uq_presupuesto_folio_empresa_version
                    UNIQUE (folio, empresa_id, version);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE presupuestos "
        "DROP CONSTRAINT IF EXISTS uq_presupuesto_folio_empresa_version"
    )
    op.execute(
        "ALTER TABLE presupuestos "
        "ADD CONSTRAINT uq_presupuesto_folio_empresa UNIQUE (folio, empresa_id)"
    )
