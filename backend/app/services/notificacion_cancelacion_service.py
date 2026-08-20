# app/services/notificacion_cancelacion_service.py
"""
Avisos cuando una cancelación se resuelve sin que nadie esté mirando.

Hasta ahora el cron revertía en silencio y el usuario se enteraba al abrir el
comprobante, a veces días después. Eso era tolerable mientras se suponía que el
PAC siempre transmitía la solicitud; desde el caso A-2202 (6-ago-2026) sabemos
que puede acusar recibo de algo que nunca envió, y entonces el trámite legal
simplemente no existe y nadie se entera.

Sólo avisa el cron. Los endpoints de «Verificar con SAT» no notifican a
propósito: ahí el usuario está viendo la pantalla y ya recibe el resultado.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.services import notificacion_service as notif_svc

_CANCELADOS = ("CANCELADA", "CANCELADO")
_VIGENTES = ("TIMBRADA", "TIMBRADO")


def _etiqueta(doc: Any) -> str:
    serie = getattr(doc, "serie", None) or ""
    folio = getattr(doc, "folio", None)
    nombre = "Factura" if hasattr(doc, "cfdi_uuid") else "Complemento de pago"
    return f"{nombre} {serie}-{folio}" if folio is not None else nombre


def avisar_resolucion(
    db: Session,  # noqa: ARG001 — se conserva por simetría; el aviso usa sesión propia
    doc: Any,
    estatus_anterior: str,
    nuevo_estatus: str,
    acuse: Optional[Any] = None,
) -> None:
    """
    Notifica el desenlace de una cancelación detectado por el cron.

    Best-effort: un fallo aquí no debe interrumpir la sincronización.
    """
    if estatus_anterior == nuevo_estatus:
        return

    etiqueta = _etiqueta(doc)
    meta = {
        "documento_id": str(getattr(doc, "id", "")),
        "cfdi_uuid": getattr(doc, "cfdi_uuid", None) or getattr(doc, "uuid", None),
        "estatus_anterior": estatus_anterior,
        "estatus_nuevo": nuevo_estatus,
    }

    if nuevo_estatus in _CANCELADOS and estatus_anterior == "EN_CANCELACION":
        tipo = notif_svc.EXITO
        titulo = "Cancelación aplicada por el SAT"
        mensaje = (
            f"{etiqueta}: el SAT aplicó la cancelación"
            + (
                f" ({acuse.estatus_cancelacion})."
                if getattr(acuse, "estatus_cancelacion", None)
                else "."
            )
        )

    elif nuevo_estatus in _VIGENTES and estatus_anterior == "EN_CANCELACION":
        if getattr(acuse, "rechazado_por_receptor", False):
            tipo = notif_svc.ADVERTENCIA
            titulo = "Cancelación rechazada por el receptor"
            mensaje = (
                f"{etiqueta}: el receptor rechazó la cancelación y el comprobante "
                "sigue vigente ante el SAT. Si aun así debe cancelarse, hay que "
                "acordarlo con el cliente o usar otro motivo."
            )
        elif getattr(acuse, "sin_solicitud_registrada", False):
            # El caso grave: el PAC acusó recibo y el SAT nunca supo nada.
            tipo = notif_svc.ERROR
            titulo = "La cancelación nunca llegó al SAT"
            mensaje = (
                f"{etiqueta}: el SAT no registró ninguna solicitud de cancelación, "
                "aunque el PAC acusó recibo. El comprobante sigue vigente y el "
                "trámite NO está en curso. Reintenta la cancelación o hazla desde "
                "el portal del SAT."
            )
        else:
            tipo = notif_svc.ADVERTENCIA
            titulo = "Cancelación no aplicada"
            mensaje = (
                f"{etiqueta}: el SAT no aplicó la cancelación y el comprobante "
                "volvió a vigente. Revisa el detalle en la pantalla del documento."
            )

    elif nuevo_estatus in _VIGENTES and estatus_anterior in _CANCELADOS:
        # El sistema lo daba por cancelado y el SAT lo reporta vigente.
        tipo = notif_svc.ERROR
        titulo = "Comprobante vigente ante el SAT"
        mensaje = (
            f"{etiqueta}: el sistema lo tenía como cancelado, pero el SAT lo "
            "reporta VIGENTE. Se corrigió el estatus; revisa si hay que rehacer "
            "el trámite."
        )

    else:
        return

    # Sesión propia a propósito: crear_notificacion hace commit, y el cron
    # sostiene un pg_try_advisory_xact_lock que se libera justamente al hacer
    # commit. Escribir el aviso en la sesión del cron soltaría el lock a media
    # pasada y permitiría que otra instancia arrancara en paralelo.
    from app.database import SessionLocal

    db_aviso = SessionLocal()
    try:
        notif_svc.crear_notificacion(
            db=db_aviso,
            empresa_id=doc.empresa_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            metadata=meta,
        )
        logger.info("[Aviso cancelación] %s — %s", titulo, etiqueta)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo crear el aviso de cancelación: %s", exc)
    finally:
        db_aviso.close()
