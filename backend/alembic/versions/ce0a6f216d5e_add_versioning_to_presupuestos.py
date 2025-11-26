"""Add versioning to presupuestos

Revision ID: ce0a6f216d5e
Revises: 1b9ad6ebaca0
Create Date: 2025-11-21 21:11:56.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ce0a6f216d5e'
down_revision: Union[str, Sequence[str], None] = '1b9ad6ebaca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the ENUM type and its values
estado_presupuesto_enum = postgresql.ENUM(
    "BORRADOR",
    "ENVIADO",
    "ACEPTADO",
    "RECHAZADO",
    "CADUCADO",
    "FACTURADO",
    "ARCHIVADO",
    name="estado_presupuesto_enum",
    create_type=False
)

def upgrade() -> None:
    """Upgrade schema."""
    # Add the new value to the ENUM type
    op.execute("ALTER TYPE estado_presupuesto_enum ADD VALUE 'ARCHIVADO'")

    # Drop the old unique constraint on folio
    # Note: The constraint name might differ if not using default naming conventions.
    try:
        op.drop_constraint('presupuestos_folio_key', 'presupuestos', type_='unique')
    except Exception:
        # Fallback for slightly different default naming
        op.drop_constraint('uq_presupuestos_folio', 'presupuestos', type_='unique')


    # Create the new composite unique constraint
    op.create_unique_constraint(
        'uq_presupuestos_folio_version_empresa',
        'presupuestos',
        ['folio', 'version', 'empresa_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the composite unique constraint
    op.drop_constraint('uq_presupuestos_folio_version_empresa', 'presupuestos', type_='unique')

    # Recreate the old unique constraint on folio
    op.create_unique_constraint('presupuestos_folio_key', 'presupuestos', ['folio'])

    # NOTE: Removing a value from an ENUM is a complex and potentially destructive operation.
    # It often requires creating a new type, migrating data, dropping the old type, and renaming the new one.
    # For a downgrade, we will leave the 'ARCHIVADO' value in the ENUM type
    # as it is a non-trivial operation to remove it safely.
    pass