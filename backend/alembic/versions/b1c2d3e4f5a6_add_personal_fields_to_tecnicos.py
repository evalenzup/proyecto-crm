"""add personal fields to tecnicos table

Revision ID: b1c2d3e4f5a6
Revises: 9a8b7c6d5e4f
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "9a8b7c6d5e4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Campos de nombre separados
    op.add_column("tecnicos", sa.Column("nombre", sa.String(100), nullable=True))
    op.add_column("tecnicos", sa.Column("primer_apellido", sa.String(100), nullable=True))
    op.add_column("tecnicos", sa.Column("segundo_apellido", sa.String(100), nullable=True))

    # Identificación
    op.add_column("tecnicos", sa.Column("curp", sa.String(18), nullable=True))
    op.add_column("tecnicos", sa.Column("rfc", sa.String(13), nullable=True))
    op.add_column("tecnicos", sa.Column("nss", sa.String(11), nullable=True))
    op.add_column("tecnicos", sa.Column("sexo", sa.String(10), nullable=True))
    op.add_column("tecnicos", sa.Column("tipo_sangre", sa.String(5), nullable=True))

    # Datos laborales
    op.add_column("tecnicos", sa.Column("numero_trabajador", sa.String(30), nullable=True))
    op.add_column("tecnicos", sa.Column("tipo_personal", sa.String(30), nullable=False, server_default="TECNICO"))
    op.add_column("tecnicos", sa.Column("area", sa.String(100), nullable=True))
    op.add_column("tecnicos", sa.Column("puesto", sa.String(100), nullable=True))
    op.add_column("tecnicos", sa.Column("nivel_estudios", sa.String(50), nullable=True))

    # Contacto
    op.add_column("tecnicos", sa.Column("celular", sa.String(50), nullable=True))

    # Licencia
    op.add_column("tecnicos", sa.Column("licencia_numero", sa.String(50), nullable=True))
    op.add_column("tecnicos", sa.Column("licencia_tipo", sa.String(20), nullable=True))
    op.add_column("tecnicos", sa.Column("licencia_vencimiento", sa.Date(), nullable=True))

    # Foto
    op.add_column("tecnicos", sa.Column("foto", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("tecnicos", "foto")
    op.drop_column("tecnicos", "licencia_vencimiento")
    op.drop_column("tecnicos", "licencia_tipo")
    op.drop_column("tecnicos", "licencia_numero")
    op.drop_column("tecnicos", "celular")
    op.drop_column("tecnicos", "nivel_estudios")
    op.drop_column("tecnicos", "puesto")
    op.drop_column("tecnicos", "area")
    op.drop_column("tecnicos", "tipo_personal")
    op.drop_column("tecnicos", "numero_trabajador")
    op.drop_column("tecnicos", "tipo_sangre")
    op.drop_column("tecnicos", "sexo")
    op.drop_column("tecnicos", "nss")
    op.drop_column("tecnicos", "rfc")
    op.drop_column("tecnicos", "curp")
    op.drop_column("tecnicos", "segundo_apellido")
    op.drop_column("tecnicos", "primer_apellido")
    op.drop_column("tecnicos", "nombre")
