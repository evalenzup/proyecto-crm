"""role hierarchy: usuario_empresas, usuario_permisos, data migration

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-10 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Tabla junction: admin ↔ empresas ─────────────────────────────────────
    op.create_table(
        'usuario_empresas',
        sa.Column('usuario_id', UUID(as_uuid=True),
                  sa.ForeignKey('usuarios.id', ondelete='CASCADE'),
                  primary_key=True, nullable=False),
        sa.Column('empresa_id', UUID(as_uuid=True),
                  sa.ForeignKey('empresas.id', ondelete='CASCADE'),
                  primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_usuario_empresas_usuario', 'usuario_empresas', ['usuario_id'])
    op.create_index('ix_usuario_empresas_empresa', 'usuario_empresas', ['empresa_id'])

    # ── 2. Tabla de permisos por módulo para ESTANDAR ────────────────────────────
    op.create_table(
        'usuario_permisos',
        sa.Column('usuario_id', UUID(as_uuid=True),
                  sa.ForeignKey('usuarios.id', ondelete='CASCADE'),
                  primary_key=True, nullable=False),
        sa.Column('modulo', sa.String(50), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_usuario_permisos_usuario', 'usuario_permisos', ['usuario_id'])

    connection = op.get_bind()

    # ── 3. Data migration: admin@example.com → SUPERADMIN ───────────────────────
    #       El enum en BD usa mayúsculas (ADMIN, SUPERVISOR → mismo patrón SUPERADMIN)
    connection.execute(sa.text("""
        UPDATE usuarios
        SET rol = 'SUPERADMIN'
        WHERE email = 'admin@example.com'
    """))

    # ── 4. Data migration: todos los ADMIN existentes ───────────────────────────
    #       obtienen acceso a TODAS las empresas en usuario_empresas
    connection.execute(sa.text("""
        INSERT INTO usuario_empresas (usuario_id, empresa_id)
        SELECT u.id, e.id
        FROM usuarios u
        CROSS JOIN empresas e
        WHERE u.rol = 'ADMIN'
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    connection = op.get_bind()

    # Revertir superadmin → admin
    connection.execute(sa.text("""
        UPDATE usuarios SET rol = 'ADMIN' WHERE rol = 'SUPERADMIN'
    """))

    op.drop_index('ix_usuario_permisos_usuario', table_name='usuario_permisos')
    op.drop_table('usuario_permisos')

    op.drop_index('ix_usuario_empresas_empresa', table_name='usuario_empresas')
    op.drop_index('ix_usuario_empresas_usuario', table_name='usuario_empresas')
    op.drop_table('usuario_empresas')
