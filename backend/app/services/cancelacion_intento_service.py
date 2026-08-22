# app/services/cancelacion_intento_service.py
"""
Escritura y consulta de la bitácora de intentos de cancelación.

Ver la nota del modelo (`app/models/cancelacion_intento.py`) para el porqué.
Todas las funciones son best-effort: la bitácora es evidencia, no parte del
trámite, así que un fallo al escribirla nunca debe tumbar una cancelación.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.cancelacion_intento import (
    CANCELADO,
    FACTURA,
    PAGO,
    REVERTIDO,
    SISTEMA,
    CancelacionIntento,
)
from app.models.factura import Factura


def _datos_documento(doc: Any) -> tuple[str, str, str]:
    """(documento_tipo, cfdi_uuid, folio legible) para Factura o Pago."""
    if isinstance(doc, Factura):
        tipo = FACTURA
        uuid_cfdi = getattr(doc, "cfdi_uuid", None) or ""
    else:
        tipo = PAGO
        uuid_cfdi = getattr(doc, "uuid", None) or ""
    serie = getattr(doc, "serie", None) or ""
    folio = getattr(doc, "folio", None)
    etiqueta = f"{serie}-{folio}" if folio is not None else serie
    return tipo, str(uuid_cfdi).strip(), etiqueta


def registrar(
    db: Session,
    doc: Any,
    *,
    motivo: Optional[str],
    folio_sustitucion: Optional[str],
    pac_code: Optional[str],
    pac_message: Optional[str],
    pac_codigo_conocido: Optional[bool] = None,
    acuse_sat: Any = None,
    sat_registro_solicitud: Optional[bool] = None,
    pac_consulta: Optional[dict] = None,
    origen: str = SISTEMA,
    fecha_envio: Optional[datetime] = None,
) -> Optional[CancelacionIntento]:
    """
    Deja constancia de un envío de solicitud de cancelación.

    ``acuse_sat`` es el AcuseSAT consultado justo después de enviar (o None si
    no se pudo consultar); de él se copia lo que el SAT decía en ese instante.
    """
    try:
        tipo, uuid_cfdi, etiqueta = _datos_documento(doc)
        intento = CancelacionIntento(
            empresa_id=doc.empresa_id,
            documento_tipo=tipo,
            documento_id=doc.id,
            cfdi_uuid=uuid_cfdi,
            documento_folio=etiqueta,
            fecha_envio=fecha_envio or datetime.utcnow(),
            motivo=(motivo or None),
            folio_sustitucion=(folio_sustitucion or "").strip() or None,
            origen=origen,
            pac_code=(pac_code or None),
            pac_message=(pac_message or None),
            pac_codigo_conocido=pac_codigo_conocido,
            sat_estado=getattr(acuse_sat, "estado", None),
            sat_es_cancelable=getattr(acuse_sat, "es_cancelable", None),
            sat_estatus_cancelacion=getattr(acuse_sat, "estatus_cancelacion", None),
            sat_registro_solicitud=sat_registro_solicitud,
            pac_consulta_estado=(pac_consulta or {}).get("estado"),
            pac_consulta_estatus_cancelacion=(
                (pac_consulta or {}).get("estatus_cancelacion")
            ),
        )
        db.add(intento)
        db.flush()
        return intento
    except Exception as exc:  # noqa: BLE001 — la bitácora nunca tumba el trámite
        logger.warning("No se pudo registrar el intento de cancelación: %s", exc)
        return None


def ultimo_abierto(db: Session, doc: Any) -> Optional[CancelacionIntento]:
    """El intento más reciente que todavía no tiene desenlace."""
    tipo, _uuid, _etq = _datos_documento(doc)
    return (
        db.query(CancelacionIntento)
        .filter(
            CancelacionIntento.documento_tipo == tipo,
            CancelacionIntento.documento_id == doc.id,
            CancelacionIntento.resultado.is_(None),
        )
        .order_by(CancelacionIntento.fecha_envio.desc())
        .first()
    )


def anotar_acuse(
    db: Session, doc: Any, *, path: Optional[str] = None, error: Optional[str] = None
) -> None:
    """
    Anota si el acuse sellado se pudo obtener o no.

    La ausencia se guarda igual que la presencia: es justo lo que desmiente al
    PAC cuando afirma tener un acuse que nunca emitió.
    """
    try:
        intento = ultimo_abierto(db, doc)
        if intento is None:
            return
        intento.acuse_path = path
        intento.acuse_error = error
        db.add(intento)
        # flush explícito: las sesiones de la app usan autoflush=False, así que
        # sin esto una consulta posterior dentro de la misma transacción seguiría
        # viendo la fila sin actualizar.
        db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo anotar el acuse en la bitácora: %s", exc)


def cerrar_si_resuelto(
    db: Session, doc: Any, estatus_anterior: str, nuevo_estatus: str
) -> None:
    """
    Cierra el intento abierto cuando el comprobante sale de EN_CANCELACION.

    Se llama desde los tres lugares que aplican el veredicto del SAT: el cron,
    el botón «Verificar con SAT» y la reversión manual.
    """
    if estatus_anterior == nuevo_estatus or estatus_anterior != "EN_CANCELACION":
        return
    if nuevo_estatus in ("CANCELADA", "CANCELADO"):
        resultado = CANCELADO
    elif nuevo_estatus in ("TIMBRADA", "TIMBRADO"):
        resultado = REVERTIDO
    else:
        return

    try:
        intento = ultimo_abierto(db, doc)
        if intento is None:
            return
        intento.resultado = resultado
        intento.fecha_resultado = datetime.utcnow()
        db.add(intento)
        db.flush()  # ver la nota en anotar_acuse
        logger.info(
            "[Bitácora] %s %s → %s (PAC dijo %s, SAT registró la solicitud: %s)",
            intento.documento_tipo, intento.documento_folio, resultado,
            intento.pac_code, intento.sat_registro_solicitud,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo cerrar el intento en la bitácora: %s", exc)


def listar(
    db: Session,
    *,
    empresa_id: Optional[UUID] = None,
    empresa_ids: Optional[list] = None,
    documento_id: Optional[UUID] = None,
    desde: Optional[datetime] = None,
    solo_no_registrados: bool = False,
    limit: int = 200,
) -> list[CancelacionIntento]:
    """Bitácora, del envío más reciente al más antiguo."""
    q = db.query(CancelacionIntento)
    if empresa_id:
        q = q.filter(CancelacionIntento.empresa_id == empresa_id)
    if empresa_ids:
        q = q.filter(CancelacionIntento.empresa_id.in_(empresa_ids))
    if documento_id:
        q = q.filter(CancelacionIntento.documento_id == documento_id)
    if desde:
        q = q.filter(CancelacionIntento.fecha_envio >= desde)
    if solo_no_registrados:
        # Las que el PAC acusó pero el SAT nunca registró.
        q = q.filter(CancelacionIntento.sat_registro_solicitud.is_(False))
    return q.order_by(CancelacionIntento.fecha_envio.desc()).limit(limit).all()


def resumen(
    db: Session,
    *,
    empresa_ids: Optional[list] = None,
    desde: Optional[datetime] = None,
) -> dict:
    """
    Cuántas solicitudes salieron y cuántas el SAT nunca registró.

    Es la respuesta a la pregunta que quedó abierta con Facturación Moderna:
    ¿acusan recibo de solicitudes que no transmiten, y con qué frecuencia?
    Sólo cuenta los envíos observados (origen SISTEMA): los RECONSTRUIDOS no
    tienen dato de lo que el SAT decía en ese momento.
    """
    q = db.query(CancelacionIntento).filter(
        CancelacionIntento.origen == SISTEMA
    )
    if empresa_ids:
        q = q.filter(CancelacionIntento.empresa_id.in_(empresa_ids))
    if desde:
        q = q.filter(CancelacionIntento.fecha_envio >= desde)

    intentos = q.all()
    total = len(intentos)
    sin_registro = sum(1 for i in intentos if i.sat_registro_solicitud is False)
    registradas = sum(1 for i in intentos if i.sat_registro_solicitud is True)
    sin_verificar = total - sin_registro - registradas
    sin_acuse = sum(1 for i in intentos if not i.acuse_path)
    codigos: dict = {}
    for i in intentos:
        codigos[i.pac_code or "(sin código)"] = codigos.get(i.pac_code or "(sin código)", 0) + 1

    return {
        "total_envios": total,
        "sat_registro_la_solicitud": registradas,
        "sat_nunca_la_registro": sin_registro,
        "no_se_pudo_verificar": sin_verificar,
        "porcentaje_no_registradas": (
            round(100 * sin_registro / total, 1) if total else 0.0
        ),
        "sin_acuse_del_pac": sin_acuse,
        "codigos_del_pac": dict(sorted(codigos.items(), key=lambda kv: -kv[1])),
        "canceladas": sum(1 for i in intentos if i.resultado == CANCELADO),
        "revertidas": sum(1 for i in intentos if i.resultado == REVERTIDO),
        "abiertas": sum(1 for i in intentos if i.resultado is None),
    }
