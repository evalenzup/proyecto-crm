# app/models/cancelacion_intento.py
"""
Bitácora de intentos de cancelación ante el SAT.

Existe porque el acuse del PAC no prueba que la solicitud haya llegado al SAT
(caso A-2202, 6-ago-2026: Facturación Moderna contestó GT12 y el SAT nunca la
registró). Las columnas ``cancelacion_code`` / ``cancelacion_message`` /
``cancelacion_acuse_path`` de Factura y Pago guardan sólo el último intento y se
sobrescriben en cada reintento, así que no sirven para reconstruir qué pasó ni
para responder la pregunta de fondo: ¿con qué frecuencia el PAC acusa recibo de
algo que no transmitió?

Cada renglón es un envío. Es inmutable salvo por la evidencia que llega después
(el acuse) y el desenlace (``resultado``), que se anotan sobre el mismo renglón.
"""
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    String,
    TIMESTAMP,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from app.models.base import Base

# Valores de documento_tipo
FACTURA = "FACTURA"
PAGO = "PAGO"

# Valores de origen — de dónde salió este renglón
SISTEMA = "SISTEMA"          # enviado por el CRM a través del PAC (caso normal)
PORTAL_SAT = "PORTAL_SAT"    # capturado a mano tras hacer el trámite en el portal
RECONSTRUIDO = "RECONSTRUIDO"  # deducido de las columnas del documento: el envío
                               # ocurrió antes de que existiera esta bitácora, así
                               # que nadie observó lo que el SAT decía en ese momento
                               # y los campos sat_* quedan en nulo.

# Valores de resultado
CANCELADO = "CANCELADO"    # el SAT terminó cancelando el comprobante
REVERTIDO = "REVERTIDO"    # volvió a vigente: rechazo del receptor o nunca se registró

# Valores de envio — en qué punto de la llamada al PAC quedó este renglón.
#
# El renglón se escribe ANTES de hablarle al PAC, no después. La diferencia
# importa: si el POST se va en timeout o el proceso muere a media llamada, el
# PAC pudo haber recibido la solicitud y sin write-ahead no quedaría ni rastro
# de que se intentó. Ese es justo el estado que produce la trampa del
# "solicitud previa" —el PAC cree tener un trámite que nosotros no sabemos que
# mandamos— y el que dejó a A-22069 rebotando siete veces.
ENVIANDO = "ENVIANDO"          # escrito antes del POST; no sabemos si llegó
RESPONDIDO = "RESPONDIDO"      # el PAC contestó y su respuesta está en pac_code
SIN_RESPUESTA = "SIN_RESPUESTA"  # la llamada falló; el PAC pudo haberla recibido igual
RECONCILIADO = "RECONCILIADO"  # quedó huérfano y se resolvió preguntándole al SAT,
                               # que es lo único observable cuando nadie vio la
                               # respuesta del PAC


class CancelacionIntento(Base):
    __tablename__ = "cancelacion_intentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Sin ForeignKey: apunta indistintamente a facturas o a pagos.
    documento_tipo = Column(String(10), nullable=False)  # FACTURA | PAGO
    documento_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    cfdi_uuid = Column(String(36), nullable=False, index=True)
    # Serie-folio al momento del envío, para leer la bitácora sin joins.
    documento_folio = Column(String(30), nullable=True)

    # ── Qué se pidió ────────────────────────────────────────────────────────
    fecha_envio = Column(DateTime, nullable=False, index=True)
    motivo = Column(String(2), nullable=True)
    folio_sustitucion = Column(String(36), nullable=True)
    origen = Column(String(20), nullable=False, default=SISTEMA)

    # ── Qué contestó el PAC ─────────────────────────────────────────────────
    pac_code = Column(String(10), nullable=True)
    pac_message = Column(Text, nullable=True)
    # False = el código no está en CODIGOS_SOLICITUD_ACEPTADA y se interpretó
    # por el texto del mensaje (ver timbrado_factmoderna).
    pac_codigo_conocido = Column(Boolean, nullable=True)

    # ── Qué decía el SAT inmediatamente después del envío ────────────────────
    sat_estado = Column(String(20), nullable=True)
    sat_es_cancelable = Column(String(40), nullable=True)
    sat_estatus_cancelacion = Column(String(40), nullable=True)
    # True  = el SAT ya reportaba la solicitud (EstatusCancelacion no vacío)
    # False = el PAC acusó recibo pero el SAT no tenía registro  ← el caso grave
    # None  = no se pudo consultar al SAT en ese momento
    sat_registro_solicitud = Column(Boolean, nullable=True)

    # ── Segunda opinión: el estatus según el propio PAC ─────────────────────
    # Se pide con consultarEstatusCFDI sólo cuando nuestra consulta directa al
    # SAT dice que no hay solicitud registrada. Si su propia herramienta
    # contesta lo mismo, queda documentado con la fuente que ellos señalan como
    # la oficial.
    pac_consulta_estado = Column(String(20), nullable=True)
    pac_consulta_estatus_cancelacion = Column(String(40), nullable=True)

    # ── Evidencia ───────────────────────────────────────────────────────────
    acuse_path = Column(String(255), nullable=True)
    # La AUSENCIA del acuse también es un hecho, y fechado: es lo que desmiente
    # al PAC cuando afirma tenerlo.
    acuse_error = Column(Text, nullable=True)

    # ── En qué quedó la llamada al PAC ──────────────────────────────────────
    # Ver la nota de los valores arriba. Nunca es nulo: el renglón nace en
    # ENVIANDO justo antes del POST.
    envio = Column(
        String(15), nullable=False, default=ENVIANDO, server_default=RESPONDIDO,
    )

    # ── Cómo terminó ────────────────────────────────────────────────────────
    resultado = Column(String(20), nullable=True)  # CANCELADO | REVERTIDO | NULL=abierto
    fecha_resultado = Column(DateTime, nullable=True)

    creado_en = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cancel_intentos_doc", "documento_tipo", "documento_id"),
        Index("ix_cancel_intentos_abiertos", "documento_id", "resultado"),
        # Un solo envío en vuelo por comprobante, garantizado por la base y no
        # por la buena voluntad del código: es el candado de último recurso
        # contra dos solicitudes simultáneas al PAC (doble clic, un usuario y el
        # cron, dos instancias del proceso web). El índice es parcial, así que
        # no estorba a los reintentos legítimos: sólo colisiona con otro renglón
        # que siga en ENVIANDO.
        Index(
            "uq_cancel_intentos_en_vuelo",
            "documento_id",
            unique=True,
            postgresql_where=text("envio = 'ENVIANDO'"),
            sqlite_where=text("envio = 'ENVIANDO'"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CancelacionIntento({self.documento_tipo} {self.documento_folio} "
            f"{self.fecha_envio:%Y-%m-%d %H:%M} pac={self.pac_code} "
            f"sat_registro={self.sat_registro_solicitud})>"
        )
