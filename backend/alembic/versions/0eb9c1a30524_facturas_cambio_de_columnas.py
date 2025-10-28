from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0eb9c1a30524"
down_revision = "1f3c51757056"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Agregar como NULLABLE para no romper filas existentes
    op.add_column("facturas", sa.Column("fecha_emision", sa.DateTime(), nullable=True))

    # 2) Backfill: usar creado_en si existe; si no, NOW()
    op.execute(
        """
        UPDATE facturas
           SET fecha_emision = COALESCE(creado_en, NOW())
         WHERE fecha_emision IS NULL
        """
    )

    # 3) Ahora sí, volverla NOT NULL
    op.alter_column(
        "facturas", "fecha_emision", existing_type=sa.DateTime(), nullable=False
    )


def downgrade():
    op.drop_column("facturas", "fecha_emision")
