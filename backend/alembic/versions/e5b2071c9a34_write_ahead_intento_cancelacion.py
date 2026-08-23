"""bitácora: write-ahead del envío (columna envio) y candado de un envío en vuelo

Revision ID: e5b2071c9a34
Revises: d3a8c15e7b92
Create Date: 2026-08-23

El renglón de la bitácora se escribía DESPUÉS de que el PAC contestaba, así que
un timeout o un reinicio a media llamada no dejaba rastro alguno de que se había
intentado cancelar —aunque el PAC sí la hubiera recibido—. Ese es el estado que
produce la trampa del "solicitud previa": el PAC se niega a reenviar alegando un
trámite que nosotros no sabemos que mandamos.

Ahora el renglón nace en ENVIANDO antes del POST y se completa después. Los
huérfanos (ENVIANDO viejos, de una llamada que nunca volvió) los resuelve el
cron preguntándole al SAT.

El índice parcial único es el candado de último recurso contra dos solicitudes
simultáneas: sólo puede haber un envío en vuelo por comprobante. Es parcial, así
que no estorba a los reintentos legítimos, que ya están RESPONDIDOS.

Los renglones que ya existían se marcan RESPONDIDO: todos tienen la respuesta
del PAC, porque antes no había forma de escribirlos sin ella.
"""
import sqlalchemy as sa
from alembic import op

revision = "e5b2071c9a34"
down_revision = "d3a8c15e7b92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cancelacion_intentos",
        sa.Column(
            "envio", sa.String(15), nullable=False, server_default="RESPONDIDO"
        ),
    )
    # El server_default se queda puesto a propósito, aunque la aplicación
    # siempre escriba el valor: desacopla el orden del deploy. Producción monta
    # el código en vivo pero el proceso sigue con el anterior en memoria, y ese
    # inserta sin la columna. Con NOT NULL y sin default, aplicar la migración
    # antes de reiniciar rompería toda cancelación en ese hueco; con default,
    # los renglones del código viejo caen en RESPONDIDO, que es justo lo que
    # son —los escribe después de que el PAC contestó—.
    op.create_index(
        "uq_cancel_intentos_en_vuelo",
        "cancelacion_intentos",
        ["documento_id"],
        unique=True,
        postgresql_where=sa.text("envio = 'ENVIANDO'"),
    )


def downgrade() -> None:
    op.drop_index("uq_cancel_intentos_en_vuelo", table_name="cancelacion_intentos")
    op.drop_column("cancelacion_intentos", "envio")
