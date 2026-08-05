"""presupuestos: el folio es único por empresa, no global

La tabla arrastraba de una versión anterior la restricción única
`presupuestos_folio_key1` sobre `folio` solo, además de la correcta
`uq_presupuesto_folio_empresa` sobre (folio, empresa_id) que declara el modelo.

Como el folio se genera por empresa (PRE-AAAA-NNNN reiniciando en cada una), la
segunda empresa que intenta crear su primer presupuesto choca con el
PRE-2026-0001 de otra empresa y falla con "Ya existe un registro con esos datos".

Revision ID: c1f4e07b2d95
Revises: b9e3c6a4d708
Create Date: 2026-08-04

"""
from alembic import op


revision = "c1f4e07b2d95"
down_revision = "b9e3c6a4d708"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS: en algunos entornos (dev) la restricción nunca se creó.
    op.execute("ALTER TABLE presupuestos DROP CONSTRAINT IF EXISTS presupuestos_folio_key1")
    # Variantes por si el nombre autogenerado difiere entre entornos.
    op.execute("ALTER TABLE presupuestos DROP CONSTRAINT IF EXISTS presupuestos_folio_key")
    # Asegurar que exista la restricción correcta (por empresa).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_presupuesto_folio_empresa'
            ) THEN
                ALTER TABLE presupuestos
                    ADD CONSTRAINT uq_presupuesto_folio_empresa UNIQUE (folio, empresa_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # No se restaura la restricción global: impedía que cada empresa llevara su
    # propia numeración de folios.
    pass
