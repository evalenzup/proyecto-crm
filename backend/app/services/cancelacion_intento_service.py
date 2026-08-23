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

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.cancelacion_intento import (
    CANCELADO,
    ENVIANDO,
    FACTURA,
    PAGO,
    RECONCILIADO,
    RESPONDIDO,
    REVERTIDO,
    SIN_RESPUESTA,
    SISTEMA,
    CancelacionIntento,
)
from app.models.factura import Factura


# Cuánto se considera que un envío sigue realmente en vuelo. Pasado esto, un
# renglón en ENVIANDO ya no es una llamada viva sino un huérfano: la petición
# murió sin volver. El timeout del cliente HTTP contra el PAC es de segundos, no
# de minutos, así que 5 es holgado.
MINUTOS_ENVIO_EN_VUELO = 5


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


def _sesion_propia() -> Optional[Session]:
    """
    Una sesión independiente de la del request, o None si no se puede abrir.

    La usan las escrituras que tienen que sobrevivir al rollback de quien las
    llama (``abrir`` y ``cerrar_fallido``): el renglón que dice "se le habló al
    PAC" no puede desaparecer justo cuando la llamada falla, que es cuando más
    falta hace.

    El SELECT 1 no sobra: ``SessionLocal()`` no conecta, sólo prepara, así que
    sin él un motor inalcanzable se descubriría hasta el commit —con el renglón
    ya perdido y sin margen para escribirlo en la sesión del request.
    """
    try:
        from sqlalchemy import text as _text

        from app.database import SessionLocal

        propia = SessionLocal()
        propia.execute(_text("SELECT 1"))
        return propia
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "No se pudo abrir una sesión propia para la bitácora (%s); se "
            "escribirá en la del request, que es mejor que no escribir nada.",
            exc,
        )
        return None


def _aplicar_respuesta(
    intento: CancelacionIntento,
    *,
    pac_code: Optional[str],
    pac_message: Optional[str],
    pac_codigo_conocido: Optional[bool],
    acuse_sat: Any,
    sat_registro_solicitud: Optional[bool],
    pac_consulta: Optional[dict],
) -> None:
    """Vuelca en el renglón lo que contestaron el PAC y el SAT."""
    intento.pac_code = pac_code or None
    intento.pac_message = pac_message or None
    intento.pac_codigo_conocido = pac_codigo_conocido
    intento.sat_estado = getattr(acuse_sat, "estado", None)
    intento.sat_es_cancelable = getattr(acuse_sat, "es_cancelable", None)
    intento.sat_estatus_cancelacion = getattr(acuse_sat, "estatus_cancelacion", None)
    intento.sat_registro_solicitud = sat_registro_solicitud
    intento.pac_consulta_estado = (pac_consulta or {}).get("estado")
    intento.pac_consulta_estatus_cancelacion = (pac_consulta or {}).get(
        "estatus_cancelacion"
    )


def abrir(
    db: Session,
    doc: Any,
    *,
    motivo: Optional[str],
    folio_sustitucion: Optional[str],
    origen: str = SISTEMA,
) -> Optional[UUID]:
    """
    Escribe el renglón ANTES de hablarle al PAC y lo deja commiteado.

    Es el write-ahead del trámite. Si el POST se va en timeout, si el PAC tarda
    y el proxy corta, o si el contenedor se reinicia a media llamada, la
    solicitud pudo haber llegado igual: el PAC la registra al recibirla, no al
    contestar. Sin este renglón no quedaría constancia de que se intentó, y el
    siguiente reintento se topa con un "ya existe una solicitud previa" que
    nadie puede explicar (es lo que le pasó a A-22069, con siete intentos).

    Usa una **sesión propia** a propósito: si escribiera en la del request, el
    rollback que sigue a un error de red se llevaría por delante justo la
    evidencia de que hubo llamada. Por lo mismo devuelve el id y no el objeto,
    que pertenece a una sesión ya cerrada.

    Devuelve None si no se pudo abrir; el trámite sigue su curso igual, porque
    la bitácora es evidencia y no parte del trámite.
    """
    tipo, uuid_cfdi, etiqueta = _datos_documento(doc)
    # Se lee antes del try a propósito: si hay que hacer rollback, el objeto
    # queda expirado y volver a tocarlo dispararía otra consulta —sobre la
    # sesión que acabamos de tumbar— en pleno manejo del error.
    doc_id = doc.id
    propia = _sesion_propia()
    sesion = propia or db
    try:
        intento = CancelacionIntento(
            empresa_id=doc.empresa_id,
            documento_tipo=tipo,
            documento_id=doc.id,
            cfdi_uuid=uuid_cfdi,
            documento_folio=etiqueta,
            fecha_envio=datetime.utcnow(),
            motivo=(motivo or None),
            folio_sustitucion=(folio_sustitucion or "").strip() or None,
            origen=origen,
            envio=ENVIANDO,
        )
        sesion.add(intento)
        if propia is not None:
            propia.commit()
        else:
            # Sin sesión propia el renglón viaja con la transacción del request:
            # se pierde el blindaje contra el rollback, pero se conserva el
            # candado del índice único, que es lo que impide el envío doble.
            sesion.flush()
        return intento.id
    except IntegrityError:
        # La única restricción de unicidad de la tabla es el índice parcial de
        # "un envío en vuelo": otro proceso está mandando esta misma solicitud
        # ahora mismo. Aquí la bitácora SÍ detiene el trámite —es su papel de
        # candado, no el de evidencia—, porque dos solicitudes simultáneas son
        # justo lo que fabrica una "solicitud previa" fantasma.
        sesion.rollback()
        logger.warning(
            "Envío de cancelación rechazado: ya hay uno en vuelo para %s",
            doc_id,
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya hay una solicitud de cancelación en curso para este "
                "comprobante. Espera a que termine antes de reintentar."
            ),
        )
    except Exception as exc:  # noqa: BLE001 — la bitácora nunca tumba el trámite
        sesion.rollback()
        logger.warning("No se pudo abrir el intento de cancelación: %s", exc)
        return None
    finally:
        if propia is not None:
            propia.close()


def tomar_candado(db: Session, doc: Any) -> None:
    """
    Impide que dos solicitudes de cancelación del mismo comprobante convivan.

    Son dos candados de distinto alcance y hacen falta los dos:

      · ``SELECT ... FOR UPDATE NOWAIT`` sobre el comprobante — cubre el doble
        clic y el "usuario y cron a la vez" mientras la petición está viva. Se
        mantiene hasta el commit, o sea durante toda la llamada al PAC. Con
        NOWAIT la segunda petición contesta 409 al instante en vez de quedarse
        colgada esperando a un PAC que tarda segundos.
      · El renglón ENVIANDO — cubre lo que el anterior no puede: la petición que
        murió sin liberar nada. Sobrevive al proceso porque está commiteado.

    Un envío en vuelo reciente rebota. Uno viejo ya no es una llamada viva sino
    un huérfano, y se resuelve aquí mismo contra el SAT: dejarlo puesto
    bloquearía el reintento de un trámite legal por una falla nuestra, que es
    exactamente el error que ya se cometió dos veces con los "No cancelable".
    """
    from datetime import timedelta

    modelo = type(doc)
    try:
        (
            db.query(modelo)
            .filter(modelo.id == doc.id)
            .with_for_update(nowait=True)
            .first()
        )
    except DBAPIError as exc:
        # lock_not_available: otra petición tiene tomado el comprobante.
        db.rollback()
        logger.warning("Cancelación concurrente rechazada para %s: %s", doc.id, exc)
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya se está procesando una cancelación de este comprobante. "
                "Espera unos segundos antes de reintentar."
            ),
        )

    intento = en_vuelo(db, doc)
    if intento is None:
        return

    edad = datetime.utcnow() - intento.fecha_envio
    if edad < timedelta(minutes=MINUTOS_ENVIO_EN_VUELO):
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya hay una solicitud de cancelación en curso para este "
                "comprobante, enviada hace unos segundos. Espera a que el PAC "
                "conteste antes de reintentar."
            ),
        )

    logger.warning(
        "[Bitácora] %s %s tenía un envío huérfano de hace %s; se resuelve antes "
        "de aceptar el reintento.",
        intento.documento_tipo, intento.documento_folio, edad,
    )
    reconciliar_uno(db, intento)
    db.commit()


def completar(
    db: Session,
    intento_id: Optional[UUID],
    *,
    pac_code: Optional[str],
    pac_message: Optional[str],
    pac_codigo_conocido: Optional[bool] = None,
    acuse_sat: Any = None,
    sat_registro_solicitud: Optional[bool] = None,
    pac_consulta: Optional[dict] = None,
) -> Optional[CancelacionIntento]:
    """
    Cierra el renglón abierto por ``abrir`` con lo que contestaron PAC y SAT.

    Escribe en la sesión del request —a diferencia de ``abrir``— porque a estas
    alturas la respuesta ya es parte del mismo desenlace que el estatus del
    comprobante: si ese commit se cae, tampoco queremos la respuesta.
    """
    if intento_id is None:
        return None
    try:
        intento = (
            db.query(CancelacionIntento)
            .filter(CancelacionIntento.id == intento_id)
            .first()
        )
        if intento is None:
            logger.warning(
                "El intento %s no existe al completarlo; la respuesta del PAC "
                "se queda sin renglón.", intento_id,
            )
            return None
        _aplicar_respuesta(
            intento,
            pac_code=pac_code,
            pac_message=pac_message,
            pac_codigo_conocido=pac_codigo_conocido,
            acuse_sat=acuse_sat,
            sat_registro_solicitud=sat_registro_solicitud,
            pac_consulta=pac_consulta,
        )
        intento.envio = RESPONDIDO
        db.add(intento)
        db.flush()
        return intento
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo completar el intento de cancelación: %s", exc)
        return None


def cerrar_fallido(
    db: Session,
    intento_id: Optional[UUID],
    *,
    mensaje: str,
    envio: str = SIN_RESPUESTA,
) -> None:
    """
    El envío no llegó a completarse: se cierra el renglón con lo que se sabe.

    Dos casos, y la diferencia importa para leer la bitácora después:

      · ``SIN_RESPUESTA`` — timeout o corte de red. Nadie vio la respuesta, lo
        que NO significa que la solicitud no llegara: el PAC la registra al
        recibirla. Lo resuelve el reconciliador preguntándole al SAT.
      · ``RESPONDIDO`` — el PAC sí contestó, con un error que aborta el trámite.
        Ahí no hay nada que reconciliar: se sabe que no hubo solicitud.

    Sesión propia por la misma razón que ``abrir``: quien llama está a punto de
    lanzar la excepción que hará rollback del request.
    """
    if intento_id is None:
        return

    propia = _sesion_propia()
    sesion = propia or db
    try:
        intento = (
            sesion.query(CancelacionIntento)
            .filter(CancelacionIntento.id == intento_id)
            .first()
        )
        if intento is None:
            return
        intento.envio = envio
        intento.pac_message = (mensaje or "")[:2000] or None
        sesion.add(intento)
        if propia is not None:
            propia.commit()
        else:
            sesion.flush()
    except Exception as exc:  # noqa: BLE001
        sesion.rollback()
        logger.warning("No se pudo cerrar el intento fallido: %s", exc)
    finally:
        if propia is not None:
            propia.close()


def en_vuelo(db: Session, doc: Any) -> Optional[CancelacionIntento]:
    """El envío que quedó en ENVIANDO para este comprobante, si lo hay."""
    tipo, _uuid, _etq = _datos_documento(doc)
    return (
        db.query(CancelacionIntento)
        .filter(
            CancelacionIntento.documento_tipo == tipo,
            CancelacionIntento.documento_id == doc.id,
            CancelacionIntento.envio == ENVIANDO,
        )
        .order_by(CancelacionIntento.fecha_envio.desc())
        .first()
    )


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
    envio: str = RESPONDIDO,
) -> Optional[CancelacionIntento]:
    """
    Deja constancia de un envío del que ya se conoce el desenlace.

    Es el camino de un solo paso, para lo que no pasa por el PAC y por tanto no
    puede quedar a medias: el trámite hecho en el portal del SAT y el backfill
    de lo anterior a esta bitácora. Los envíos por el PAC usan ``abrir`` +
    ``completar``.

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
            envio=envio,
        )
        _aplicar_respuesta(
            intento,
            pac_code=pac_code,
            pac_message=pac_message,
            pac_codigo_conocido=pac_codigo_conocido,
            acuse_sat=acuse_sat,
            sat_registro_solicitud=sat_registro_solicitud,
            pac_consulta=pac_consulta,
        )
        db.add(intento)
        db.flush()
        return intento
    except Exception as exc:  # noqa: BLE001 — la bitácora nunca tumba el trámite
        logger.warning("No se pudo registrar el intento de cancelación: %s", exc)
        return None


def _documento_de(db: Session, intento: CancelacionIntento) -> Any:
    """El comprobante al que apunta un renglón de la bitácora."""
    if intento.documento_tipo == FACTURA:
        return db.query(Factura).filter(Factura.id == intento.documento_id).first()
    from app.models.pago import Pago

    return db.query(Pago).filter(Pago.id == intento.documento_id).first()


def reconciliar_uno(db: Session, intento: CancelacionIntento) -> Optional[str]:
    """
    Resuelve un envío huérfano preguntándole al SAT, que es el único que sabe.

    Nadie vio lo que contestó el PAC, así que no hay nada que reconstruir de ese
    lado: lo observable es si el SAT registró la solicitud, y eso decide si el
    comprobante queda EN_CANCELACION o se queda como estaba.

    El renglón se cierra pase lo que pase, incluso si el SAT no se deja
    consultar. Mantenerlo en ENVIANDO conservaría el candado puesto sobre un
    comprobante cuya llamada murió hace rato, y eso impediría el reintento —o
    sea, bloquearía un trámite legal por una falla nuestra, que es exactamente
    el error que ya se cometió dos veces con los "No cancelable".

    Devuelve el nuevo estatus del comprobante si cambió, o None.
    """
    from app.services import sat_cfdi_service as sat_svc

    doc = _documento_de(db, intento)
    nota_previa = intento.pac_message or ""
    nuevo_estatus = None

    if doc is None:
        intento.envio = RECONCILIADO
        intento.pac_message = (
            f"{nota_previa} Envío huérfano: el comprobante ya no existe."
        ).strip()
        db.add(intento)
        db.flush()
        return None

    es_factura = intento.documento_tipo == FACTURA
    try:
        rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(doc)
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_emisor,
            rfc_receptor=rfc_receptor,
            total=total,
            uuid=intento.cfdi_uuid,
        )
    except Exception as exc:  # noqa: BLE001
        intento.envio = RECONCILIADO
        intento.pac_message = (
            f"{nota_previa} Envío huérfano sin respuesta del PAC; tampoco se "
            f"pudo consultar al SAT para saber si la solicitud llegó ({exc})."
        ).strip()
        db.add(intento)
        db.flush()
        logger.warning(
            "[Bitácora] Huérfano %s %s: el SAT no se dejó consultar (%s)",
            intento.documento_tipo, intento.documento_folio, exc,
        )
        return None

    _aplicar_respuesta(
        intento,
        pac_code=intento.pac_code,
        pac_message=(
            f"{nota_previa} Envío huérfano: nadie vio la respuesta del PAC. "
            f"Según el SAT, {'sí' if (acuse.estatus_cancelacion or acuse.cancelado_por_sat) else 'no'} "
            "quedó registrada la solicitud."
        ).strip(),
        pac_codigo_conocido=intento.pac_codigo_conocido,
        acuse_sat=acuse if acuse.encontrado else None,
        sat_registro_solicitud=(
            bool(acuse.cancelado_por_sat or (acuse.estatus_cancelacion or "").strip())
            if acuse.encontrado
            else None
        ),
        pac_consulta=None,
    )
    intento.envio = RECONCILIADO
    db.add(intento)

    if acuse.encontrado:
        estatus_previo = getattr(doc.estatus, "value", doc.estatus)
        aplicar = (
            sat_svc.aplicar_acuse_sat if es_factura else sat_svc.aplicar_acuse_sat_pago
        )
        estatus_resultante, hubo_cambio = aplicar(doc, acuse)
        if hubo_cambio:
            db.add(doc)
            nuevo_estatus = estatus_resultante
            cerrar_si_resuelto(db, doc, estatus_previo, estatus_resultante)
            logger.warning(
                "[Bitácora] Huérfano %s %s reconciliado: %s → %s",
                intento.documento_tipo, intento.documento_folio,
                estatus_previo, estatus_resultante,
            )
    db.flush()
    return nuevo_estatus


def reconciliar_huerfanos(
    db: Optional[Session] = None,
    *,
    minutos: int = MINUTOS_ENVIO_EN_VUELO,
    limite: int = 50,
) -> int:
    """
    Barre los envíos que quedaron en ENVIANDO y nunca se completaron.

    Corre en la ventana caliente del cron. Son pocos por definición —uno por
    llamada caída—, pero cada uno es un comprobante que puede estar en trámite
    ante el SAT sin que el sistema lo sepa.

    Sesión propia y commit por huérfano: el cron sostiene su advisory lock en la
    transacción del job, y commitear ahí a media pasada lo soltaría y dejaría
    entrar a otra instancia a la misma ventana. Además así un huérfano que
    truena no arrastra a los demás.
    """
    from datetime import timedelta

    propia = None if db is not None else _sesion_propia()
    sesion = propia or db
    if sesion is None:
        return 0
    try:
        corte = datetime.utcnow() - timedelta(minutes=minutos)
        huerfanos = (
            sesion.query(CancelacionIntento)
            .filter(
                CancelacionIntento.envio == ENVIANDO,
                CancelacionIntento.fecha_envio < corte,
            )
            .order_by(CancelacionIntento.fecha_envio)
            .limit(limite)
            .all()
        )
        if not huerfanos:
            return 0

        logger.warning(
            "[Bitácora] %d envío(s) de cancelación quedaron sin respuesta; "
            "resolviéndolos contra el SAT.", len(huerfanos),
        )
        for intento in huerfanos:
            try:
                reconciliar_uno(sesion, intento)
                sesion.commit()
            except Exception as exc:  # noqa: BLE001
                sesion.rollback()
                logger.warning(
                    "[Bitácora] No se pudo reconciliar el huérfano %s: %s",
                    intento.id, exc,
                )
        return len(huerfanos)
    finally:
        if propia is not None:
            propia.close()


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
        if intento.envio == ENVIANDO:
            # El SAT resolvió un envío del que nunca supimos la respuesta del
            # PAC. Dejarlo en ENVIANDO mantendría puesto el candado de "un envío
            # en vuelo" sobre un trámite que ya terminó.
            intento.envio = RECONCILIADO
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
