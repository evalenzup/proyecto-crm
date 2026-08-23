# app/services/historial_documento_service.py
"""
Historial de un comprobante —factura o complemento de pago—: qué se le hizo,
cuándo y quién.

Junta dos rastros que hasta ahora vivían separados y no se podían leer uno
contra otro:

  · ``auditoria_log`` — las acciones de la gente: crear, modificar, timbrar,
    enviar por correo, consultar al SAT.
  · ``cancelacion_intentos`` — el trámite fiscal: cada solicitud enviada al PAC
    con lo que contestó y lo que el SAT decía en ese instante.

La pregunta que responde es la que hoy obliga a entrar a la base: "¿qué le pasó
a esta factura?". Y de paso destapa una carencia: las modificaciones casi no se
auditaban (1 registro contra 478 creaciones), así que ``diff`` existe para que
a partir de ahora sí quede escrito qué campo cambió y de qué a qué.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.auditoria import AuditoriaLog
from app.models.factura import Factura
from app.models.cancelacion_intento import (
    ENVIANDO,
    PORTAL_SAT,
    RECONCILIADO,
    RECONSTRUIDO,
    SIN_RESPUESTA,
    CancelacionIntento,
)

# ── Qué se compara y cómo se agrupa ──────────────────────────────────────────
#
# El grupo no es cosmética: decide qué ve el usuario de entrada. Un cambio de
# receptor o de importes hay que verlo siempre; que alguien corrigiera una nota
# interna, casi nunca.
GRUPO_FISCAL = "fiscal"      # cambia el CFDI o lo que se timbraría
GRUPO_COBRANZA = "cobranza"  # no toca el CFDI pero sí lo que se debe
GRUPO_INTERNO = "interno"    # sólo para nosotros

CAMPOS_FISCALES_FACTURA = {
    "serie", "folio", "cliente_id", "fecha_emision", "tipo_comprobante",
    "forma_pago", "metodo_pago", "uso_cfdi", "moneda", "tipo_cambio",
    "lugar_expedicion", "condiciones_pago", "cfdi_relacionados_tipo",
    "cfdi_relacionados", "subtotal", "descuento", "impuestos_trasladados",
    "impuestos_retenidos", "total", "retencion_local_desc",
    "retencion_local_tasa", "retencion_local_monto", "conceptos",
}

# En un complemento casi todo es fiscal: el monto, la forma y la fecha del pago
# son el contenido del CFDI, y los documentos relacionados son los renglones.
CAMPOS_FISCALES_PAGO = {
    "serie", "folio", "cliente_id", "fecha_pago", "fecha_emision",
    "forma_pago_p", "moneda_p", "monto", "tipo_cambio_p",
    "documentos_relacionados",
}

# Sólo las facturas tienen estado de cobranza; un complemento ES el cobro.
CAMPOS_COBRANZA = {"status_pago", "fecha_pago", "fecha_cobro"}

# Lo que cambia solo o lo escribe el propio timbrado. Registrarlo sería llenar
# el historial de ruido y esconder los cambios que sí hizo una persona; además
# cada uno de estos ya tiene su evento propio en la línea de tiempo.
CAMPOS_IGNORADOS = {
    "id", "empresa_id", "creado_en", "actualizado_en",
    "xml_path", "pdf_path", "cadena_original", "qr_url",
    "estatus", "cfdi_uuid", "uuid", "fecha_timbrado", "no_certificado",
    "no_certificado_sat", "sello_cfdi", "sello_sat", "rfc_proveedor_sat",
    "cfdi_rfc_emisor", "cfdi_rfc_receptor", "cfdi_total",
    "motivo_cancelacion", "folio_fiscal_sustituto", "cancelacion_code",
    "cancelacion_message", "cancelacion_acuse_path",
    "fecha_solicitud_cancelacion",
}


def _es_factura(doc: Any) -> bool:
    return isinstance(doc, Factura)


def _valor_simple(v: Any) -> Any:
    """Convierte a algo comparable y serializable a JSON."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return str(v)


def _renglones_de(doc: Any) -> tuple[str, list[dict]]:
    """
    Los renglones del comprobante en su forma mínima comparable.

    Una factura tiene conceptos; un complemento, los documentos que paga. Son la
    misma idea —lo que cambia en bloque cuando se reordena— y por eso se
    comparan igual.
    """
    if _es_factura(doc):
        salida = [
            {
                "descripcion": _valor_simple(getattr(c, "descripcion", None)),
                "cantidad": _valor_simple(getattr(c, "cantidad", None)),
                "valor_unitario": _valor_simple(getattr(c, "valor_unitario", None)),
                "importe": _valor_simple(getattr(c, "importe", None)),
            }
            for c in getattr(doc, "conceptos", None) or []
        ]
        return "conceptos", salida

    salida = [
        {
            "documento": f"{getattr(d, 'serie', '') or ''}-{getattr(d, 'folio', '') or ''}",
            "parcialidad": _valor_simple(getattr(d, "num_parcialidad", None)),
            "pagado": _valor_simple(getattr(d, "imp_pagado", None)),
            "saldo_insoluto": _valor_simple(getattr(d, "imp_saldo_insoluto", None)),
        }
        for d in getattr(doc, "documentos_relacionados", None) or []
    ]
    return "documentos_relacionados", salida


def snapshot(doc: Any) -> dict:
    """
    Foto del comprobante para comparar antes/después de una edición.

    Se toma sobre las columnas del modelo, no sobre el payload: así se detecta
    también lo que cambia de rebote —los totales al recalcularse, por ejemplo—
    y no sólo lo que el usuario tecleó.
    """
    datos: dict = {}
    for col in doc.__table__.columns:
        nombre = col.name
        if nombre in CAMPOS_IGNORADOS:
            continue
        datos[nombre] = _valor_simple(getattr(doc, nombre, None))
    campo_renglones, renglones = _renglones_de(doc)
    datos[campo_renglones] = renglones
    return datos


def _grupo(campo: str, de_factura: bool) -> str:
    """
    A qué grupo pertenece un campo, según de qué comprobante venga.

    No es lo mismo en los dos: `fecha_pago` en una factura es la fecha
    programada de cobro —cobranza— y en un complemento es la fecha real del pago
    que se declara en el CFDI —fiscal—. El mismo nombre, dos cosas distintas.
    """
    fiscales = CAMPOS_FISCALES_FACTURA if de_factura else CAMPOS_FISCALES_PAGO
    if campo in fiscales:
        return GRUPO_FISCAL
    if de_factura and campo in CAMPOS_COBRANZA:
        return GRUPO_COBRANZA
    return GRUPO_INTERNO


def diff(antes: dict, despues: dict) -> list[dict]:
    """
    Qué campos cambiaron, con su valor anterior y el nuevo.

    Los renglones —conceptos o documentos pagados— se reportan como un solo
    cambio con las dos listas: partirlo uno por uno sería adivinar cuál
    corresponde a cuál cuando se reordenan, y para leer el historial basta ver
    qué había y qué quedó.
    """
    # De qué comprobante viene se deduce de la propia foto, que ya trae el campo
    # de renglones que le toca; así no hay que arrastrar el tipo hasta aquí.
    # Se pregunta por el complemento y no por la factura a propósito: una foto
    # parcial —o cualquier futuro documento— cae en la clasificación de factura,
    # que es la más detallada, en vez de mandar todo a "interno" en silencio.
    de_factura = not (
        "documentos_relacionados" in antes or "documentos_relacionados" in despues
    )

    cambios = []
    for campo in sorted(set(antes) | set(despues)):
        anterior = antes.get(campo)
        nuevo = despues.get(campo)
        if anterior == nuevo:
            continue
        cambios.append(
            {
                "campo": campo,
                "antes": anterior,
                "despues": nuevo,
                "grupo": _grupo(campo, de_factura),
            }
        )
    return cambios


# ─────────────────────────────────────────────────────────────────────────────
# Línea de tiempo
# ─────────────────────────────────────────────────────────────────────────────

TITULOS = {
    "CREAR_FACTURA": "Factura creada",
    "ACTUALIZAR_FACTURA": "Factura modificada",
    "TIMBRAR_FACTURA": "Timbrada ante el SAT",
    "ENVIAR_FACTURA_EMAIL": "Enviada por correo",
    "CANCELAR_FACTURA": "Cancelación solicitada",
    "VERIFICAR_SAT": "Consulta al SAT",
    "REVERTIR_CANCELACION": "Cancelación revertida a mano",
    "REGISTRAR_CANCELACION_PORTAL": "Cancelación del portal registrada",
    "LIMPIAR_RASTRO_CANCELACION": "Rastro de cancelación limpiado",
    "CREAR_FACTURA_DESDE_ORDEN": "Creada desde una orden de servicio",
    "EXPORTAR_EXCEL": "Exportada a Excel",
    # Complementos de pago
    "CREAR_PAGO": "Complemento creado",
    "ACTUALIZAR_PAGO": "Complemento modificado",
    "TIMBRAR_PAGO": "Timbrado ante el SAT",
    "ENVIAR_PAGO_EMAIL": "Enviado por correo",
    "CANCELAR_PAGO": "Cancelación solicitada",
    "ELIMINAR_PAGO": "Complemento eliminado",
}


def _titulo_accion(accion: str) -> str:
    if accion in TITULOS:
        return TITULOS[accion]
    return accion.replace("_", " ").capitalize()


def _detalle_json(texto: Optional[str]) -> Any:
    if not texto:
        return None
    try:
        return json.loads(texto)
    except (ValueError, TypeError):
        return texto


def _titulo_intento(intento: CancelacionIntento) -> str:
    """
    Lo que cuenta este renglón de la bitácora, en una línea.

    Se lee del estado del envío antes que del resultado: un envío que nunca
    volvió es una historia distinta a uno que el SAT resolvió, aunque los dos
    terminen sin cancelar.
    """
    if intento.origen == PORTAL_SAT:
        return "Cancelación tramitada en el portal del SAT"
    if intento.origen == RECONSTRUIDO:
        return "Solicitud anterior a la bitácora (reconstruida)"
    if intento.envio == ENVIANDO:
        return "Solicitud saliendo hacia el PAC"
    if intento.envio == SIN_RESPUESTA:
        return "El PAC no contestó — pudo haberla recibido igual"
    if intento.envio == RECONCILIADO:
        return "Envío sin respuesta, resuelto preguntando al SAT"
    if intento.sat_registro_solicitud is False:
        return f"El PAC acusó {intento.pac_code or 'recibo'} y el SAT no la registró"
    return f"Solicitud enviada al PAC ({intento.pac_code or 'sin código'})"


def linea_de_tiempo(db: Session, doc: Any) -> list[dict]:
    """
    Todo lo que le pasó al comprobante, del evento más reciente al más viejo.

    Los dos rastros conviven a propósito aunque a veces hablen del mismo
    momento: la auditoría dice quién apretó el botón y la bitácora qué contestó
    el PAC. Cuando una cancelación sale mal, la diferencia entre esas dos cosas
    es justo lo que hay que ver.
    """
    eventos: list[dict] = []
    entidad = "factura" if _es_factura(doc) else "pago"

    try:
        # `entidad` se escribió inconsistente a lo largo del tiempo: 'factura'
        # en casi todo y 'Factura' en VERIFICAR_SAT. Comparar en minúsculas
        # evita perder los cientos de eventos de la variante equivocada.
        registros = (
            db.query(AuditoriaLog)
            .filter(
                func.lower(AuditoriaLog.entidad) == entidad,
                AuditoriaLog.entidad_id == str(doc.id),
            )
            .order_by(AuditoriaLog.creado_en.desc())
            .all()
        )
        for r in registros:
            eventos.append(
                {
                    "fecha": r.creado_en,
                    "fuente": "auditoria",
                    "accion": r.accion,
                    "titulo": _titulo_accion(r.accion),
                    "usuario": r.usuario_email,
                    "ip": r.ip,
                    "detalle": _detalle_json(r.detalle),
                }
            )
    except Exception as exc:  # noqa: BLE001 — el historial nunca tumba la pantalla
        logger.warning("No se pudo leer la auditoría del comprobante: %s", exc)

    try:
        intentos = (
            db.query(CancelacionIntento)
            .filter(CancelacionIntento.documento_id == doc.id)
            .order_by(CancelacionIntento.fecha_envio.desc())
            .all()
        )
        for i in intentos:
            eventos.append(
                {
                    "fecha": i.fecha_envio,
                    "fuente": "cancelacion",
                    "accion": "SOLICITUD_CANCELACION",
                    "titulo": _titulo_intento(i),
                    "usuario": None,  # el envío lo hace el sistema; el quién está en la auditoría
                    "ip": None,
                    "detalle": {
                        "motivo": i.motivo,
                        "folio_sustitucion": i.folio_sustitucion,
                        "origen": i.origen,
                        "envio": i.envio,
                        "pac_code": i.pac_code,
                        "pac_message": i.pac_message,
                        "sat_estado": i.sat_estado,
                        "sat_es_cancelable": i.sat_es_cancelable,
                        "sat_estatus_cancelacion": i.sat_estatus_cancelacion,
                        "sat_registro_solicitud": i.sat_registro_solicitud,
                        "tiene_acuse": bool(i.acuse_path),
                        "acuse_error": i.acuse_error,
                        "resultado": i.resultado,
                        "fecha_resultado": i.fecha_resultado,
                    },
                }
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer la bitácora de cancelaciones: %s", exc)

    eventos.sort(key=lambda e: (e["fecha"] is not None, e["fecha"]), reverse=True)
    return eventos
