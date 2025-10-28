"""merge heads

Revision ID: 0cc037e247c8
Revises: 0eb9c1a30524, 5f829bd46ac1
Create Date: 2025-08-23 01:17:13.473948

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "0cc037e247c8"
down_revision: Union[str, Sequence[str], None] = ("0eb9c1a30524", "5f829bd46ac1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
