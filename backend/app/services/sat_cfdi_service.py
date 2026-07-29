# app/services/sat_cfdi_service.py
"""
Consulta de estado de CFDI directamente en el SAT.

Endpoint público (sin autenticación):
  https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc

Documentación: DocumentacionWSConsulta_CFDIv1-2.pdf (oct 2018)

La expresionImpresa tiene el formato:
  ?re=<RFC_EMISOR>&rr=<RFC_RECEPTOR>&tt=<TOTAL_17.6>&id=<UUID>
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

import httpx
from lxml import etree

logger = logging.getLogger("app")

# Días de antigüedad de la solicitud tras los cuales, si el SAT sigue reportando
# el CFDI Vigente y SIN cancelación en proceso, damos la cancelación por vencida
# (el receptor no la aceptó en el plazo) y revertimos a TIMBRADA/TIMBRADO.
# Cubre las 72 horas hábiles del SAT más un fin de semana.
DIAS_CANCELACION_VENCIDA = 5

SAT_CONSULTA_URL = (
    "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
)
SAT_SOAP_ACTION = "http://tempuri.org/IConsultaCFDIService/Consulta"

SOAP_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope
    xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:tns="http://tempuri.org/">
  <soap:Body>
    <tns:Consulta>
      <tns:expresionImpresa>{expresion}</tns:expresionImpresa>
    </tns:Consulta>
  </soap:Body>
</soap:Envelope>"""


@dataclass
class AcuseSAT:
    """Respuesta del SAT para la consulta de un CFDI."""
    codigo_estatus: str          # "S" = encontrado | "N 601" | "N 602"
    estado: str                  # "Vigente" | "Cancelado"
    es_cancelable: str           # "Cancelable sin aceptación" | "Cancelable con aceptación" | "No cancelable"
    estatus_cancelacion: str     # "En proceso de cancelación" | "Cancelado sin aceptación" | "Cancelado con aceptación" | ""

    @property
    def encontrado(self) -> bool:
        return self.codigo_estatus.startswith("S")

    @property
    def cancelado(self) -> bool:
        return self.estado.lower() == "cancelado"

    @property
    def en_proceso(self) -> bool:
        return "proceso" in (self.estatus_cancelacion or "").lower()

    @property
    def cancelado_por_sat(self) -> bool:
        """Ya cancelado definitivamente en SAT."""
        return self.cancelado and not self.en_proceso

    @property
    def rechazado_por_receptor(self) -> bool:
        """El receptor rechazó explícitamente la cancelación."""
        return "rechazada" in (self.estatus_cancelacion or "").lower()


def extraer_datos_cfdi(xml_bytes: bytes) -> dict:
    """
    Extrae del XML timbrado los tres datos con los que el SAT identifica un CFDI:
    RFC del emisor, RFC del receptor y Total.

    Son inmutables una vez timbrado, a diferencia de los valores en la BD (el
    cliente puede cambiar de RFC, el total puede recalcularse), que es lo que
    rompe la consulta al SAT ("601: la expresión impresa no es válida").

    Devuelve {} si no se pueden extraer.
    """
    datos: dict = {}
    try:
        root = etree.fromstring(xml_bytes)
        for el in root.iter():
            local = etree.QName(el.tag).localname if el.tag else ""
            if local == "Comprobante":
                total = el.get("Total") or el.get("total")
                if total:
                    datos["total"] = total
            elif local == "Emisor":
                rfc = el.get("Rfc") or el.get("rfc")
                if rfc:
                    datos["rfc_emisor"] = rfc.strip().upper()
            elif local == "Receptor":
                rfc = el.get("Rfc") or el.get("rfc")
                if rfc:
                    datos["rfc_receptor"] = rfc.strip().upper()
    except Exception:  # noqa: BLE001 — caemos al regex de abajo
        pass

    if not datos:
        import re

        txt = xml_bytes.decode("utf-8", "ignore")
        m = re.search(r"<[\w:]*Emisor[^>]*\sRfc=\"([^\"]+)\"", txt)
        if m:
            datos["rfc_emisor"] = m.group(1).strip().upper()
        m = re.search(r"<[\w:]*Receptor[^>]*\sRfc=\"([^\"]+)\"", txt)
        if m:
            datos["rfc_receptor"] = m.group(1).strip().upper()
        m = re.search(r"<[\w:]*Comprobante[^>]*\sTotal=\"([^\"]+)\"", txt)
        if m:
            datos["total"] = m.group(1)

    return datos


def datos_consulta(doc) -> Tuple[str, str, float]:
    """
    (rfc_emisor, rfc_receptor, total) para consultar un CFDI en el SAT.

    Prefiere el snapshot tomado del XML al timbrar (``cfdi_rfc_emisor`` /
    ``cfdi_rfc_receptor`` / ``cfdi_total``) porque es inmutable; sólo si no
    existe cae a los valores actuales de la BD (empresa/cliente/total), que
    pueden haber cambiado después de timbrar y hacen fallar la consulta.

    Sirve para Factura y para Pago.
    """
    emisor = (getattr(doc, "cfdi_rfc_emisor", None) or "").strip().upper()
    receptor = (getattr(doc, "cfdi_rfc_receptor", None) or "").strip().upper()
    total_snap = getattr(doc, "cfdi_total", None)

    if not emisor:
        emisor = (getattr(getattr(doc, "empresa", None), "rfc", None) or "").strip().upper()
    if not receptor:
        receptor = (getattr(getattr(doc, "cliente", None), "rfc", None) or "").strip().upper()

    if total_snap is not None:
        total = float(total_snap)
    else:
        # Los complementos de pago timbran con Total=0; las facturas con su total.
        total = float(getattr(doc, "total", 0) or 0)

    return emisor, receptor, total


def _build_expresion(rfc_emisor: str, rfc_receptor: str, total: float, uuid: str) -> str:
    """
    Construye la expresionImpresa para el CFDI 4.0.
    El total va con 6 decimales, 17 caracteres totales, relleno con ceros a la izquierda.
    """
    total_str = f"{total:017.6f}"
    return f"?re={rfc_emisor}&rr={rfc_receptor}&tt={total_str}&id={uuid}"


def consultar_cfdi(
    rfc_emisor: str,
    rfc_receptor: str,
    total: float,
    uuid: str,
    timeout: int = 15,
) -> AcuseSAT:
    """
    Llama al web service del SAT y devuelve un AcuseSAT con el estado actual del CFDI.
    Lanza RuntimeError si hay problemas de red o respuesta inválida.
    """
    expresion = _build_expresion(rfc_emisor, rfc_receptor, total, uuid)
    # Los & de la query string deben escaparse como &amp; dentro de XML;
    # de lo contrario el parser SOAP del SAT falla con DeserializationFailed.
    body = SOAP_TEMPLATE.format(expresion=html.escape(expresion))

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": SAT_SOAP_ACTION,
    }

    try:
        with httpx.Client(timeout=timeout, verify=True) as client:
            resp = client.post(SAT_CONSULTA_URL, content=body.encode("utf-8"), headers=headers)
    except httpx.TimeoutException as e:
        raise RuntimeError(f"Timeout al consultar el SAT ({timeout}s): {e}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Error de red al consultar el SAT: {e}") from e

    if resp.status_code >= 400:
        raise RuntimeError(
            f"HTTP {resp.status_code} del SAT (ConsultaCFDI): {resp.text[:500]}"
        )

    return _parse_response(resp.content)


def _parse_response(content: bytes) -> AcuseSAT:
    """Parsea el XML SOAP de respuesta del SAT y extrae el Acuse."""
    try:
        root = etree.fromstring(content)
    except etree.XMLSyntaxError as e:
        raise RuntimeError(f"Respuesta SAT inválida (XML): {e}") from e

    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "tns": "http://tempuri.org/",
        "s": "http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.ConsultaCfdi.Servicio",
    }

    def _text(tag: str, default: str = "") -> str:
        el = root.find(f".//{{{ns['s']}}}{tag}")
        if el is None:
            # Intento sin namespace (algunos entornos lo omiten)
            el = root.find(f".//{tag}")
        return (el.text or "").strip() if el is not None else default

    codigo_estatus = _text("CodigoEstatus")
    estado = _text("Estado")
    es_cancelable = _text("EsCancelable")
    estatus_cancelacion = _text("EstatusCancelacion")

    # Fallback: buscar con xpath más amplio si los namespace fallaron
    if not codigo_estatus:
        for el in root.iter():
            local = etree.QName(el.tag).localname if el.tag else ""
            if local == "CodigoEstatus":
                codigo_estatus = (el.text or "").strip()
            elif local == "Estado":
                estado = (el.text or "").strip()
            elif local == "EsCancelable":
                es_cancelable = (el.text or "").strip()
            elif local == "EstatusCancelacion":
                estatus_cancelacion = (el.text or "").strip()

    if not codigo_estatus:
        raise RuntimeError("El SAT no devolvió CodigoEstatus en la respuesta")

    return AcuseSAT(
        codigo_estatus=codigo_estatus,
        estado=estado,
        es_cancelable=es_cancelable,
        estatus_cancelacion=estatus_cancelacion,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lógica canónica de aplicación del acuse SAT a una factura
# ─────────────────────────────────────────────────────────────────────────────



def aplicar_acuse_sat(
    factura: Any,
    acuse: AcuseSAT,
    ahora: Optional[datetime] = None,
) -> Tuple[str, bool]:
    """
    Aplica el resultado del acuse SAT al objeto ``factura`` (lo muta en sus campos
    de estatus y fecha_solicitud_cancelacion).

    Lógica canónica — única fuente de verdad para los 3 consumidores:
      - endpoint  POST /facturas/{id}/verificar-sat
      - cron      _sync_cancelaciones_job  (main.py)
      - script    scripts/verificar_timbradas_en_sat.py

    Reglas:
      · SAT no reconoce el CFDI (encontrado=False) → NO se toca nada (no verificable)
      · SAT dice Cancelado                        → estatus = "CANCELADA"
      · SAT dice En proceso                       → estatus = "EN_CANCELACION"
                                                    registra fecha_solicitud_cancelacion si no existe
      · SAT dice Vigente + "Solicitud rechazada"  → revertir a TIMBRADA (receptor rechazó explícitamente)
      · SAT dice Vigente sin fecha registrada     → anclar fecha actual, mantener EN_CANCELACION
      · SAT dice Vigente, solicitud reciente       → mantener EN_CANCELACION (el SAT puede tardar en
                                                    reflejar la solicitud recién enviada)
      · SAT dice Vigente, solicitud vencida        → revertir a TIMBRADA (cancelación "con aceptación"
        (> DIAS_CANCELACION_VENCIDA)                que expiró sin que el receptor la aceptara)

    No llama a db.add() ni db.commit() — responsabilidad del llamador.

    Returns:
        (nuevo_estatus: str, hubo_cambio: bool)
    """
    if ahora is None:
        ahora = datetime.utcnow()

    estatus_anterior: str = factura.estatus
    nuevo_estatus: str = estatus_anterior  # por defecto no cambia

    if not acuse.encontrado:
        # El SAT no reconoció el CFDI (típicamente "601: la expresión impresa no
        # es válida", porque el RFC del receptor o el total ya no coinciden con
        # los del XML timbrado). No sabemos nada de su estado real: cualquier
        # decisión aquí sería a ciegas. Antes esto caía en la rama "Vigente sin
        # proceso" y podía revertir a TIMBRADA una factura realmente cancelada.
        logger.warning(
            "[SAT] CFDI no verificable (%s) — no se modifica el estatus (%s)",
            acuse.codigo_estatus, estatus_anterior,
        )
        return estatus_anterior, False

    if acuse.cancelado_por_sat:
        nuevo_estatus = "CANCELADA"
        factura.fecha_solicitud_cancelacion = None

    elif acuse.en_proceso:
        nuevo_estatus = "EN_CANCELACION"
        # Registrar la fecha de solicitud si aún no existe
        if not factura.fecha_solicitud_cancelacion:
            factura.fecha_solicitud_cancelacion = ahora

    else:
        # SAT reporta Vigente y no en proceso
        if estatus_anterior == "CANCELADA":
            # El sistema la tenía como CANCELADA, pero el SAT la reporta Vigente
            # (sin cancelación en proceso): la cancelación fue rechazada o nunca se
            # aplicó (ej. "Relación no válida o inexistente" en motivo 01).
            # El SAT es la fuente de verdad → reconciliar a TIMBRADA.
            nuevo_estatus = "TIMBRADA"
            factura.fecha_solicitud_cancelacion = None
        elif estatus_anterior == "EN_CANCELACION":
            if acuse.rechazado_por_receptor:
                # El receptor rechazó explícitamente → revertir a TIMBRADA
                nuevo_estatus = "TIMBRADA"
                factura.fecha_solicitud_cancelacion = None
            elif factura.fecha_solicitud_cancelacion is None:
                # Sin fecha registrada: anclar ahora para tener referencia,
                # pero NO revertir — el SAT puede tardar en reflejar la solicitud
                factura.fecha_solicitud_cancelacion = ahora
            elif (ahora - factura.fecha_solicitud_cancelacion) >= timedelta(days=DIAS_CANCELACION_VENCIDA):
                # Solicitud vencida y el CFDI sigue Vigente sin cancelación en
                # proceso: la cancelación "con aceptación" expiró sin que el
                # receptor la aceptara → no procedió, revertir a TIMBRADA.
                nuevo_estatus = "TIMBRADA"
                factura.fecha_solicitud_cancelacion = None
            # else: solicitud reciente → mantener EN_CANCELACION (el SAT puede
            # tardar en reflejar la solicitud recién enviada)

    factura.estatus = nuevo_estatus
    return nuevo_estatus, estatus_anterior != nuevo_estatus


def aplicar_acuse_sat_pago(
    pago: Any,
    acuse: AcuseSAT,
    ahora: Optional[datetime] = None,
) -> Tuple[str, bool]:
    """
    Equivalente de ``aplicar_acuse_sat`` para complementos de pago.

    Misma lógica canónica, con los nombres de estatus propios de Pago
    (TIMBRADO / EN_CANCELACION / CANCELADO en vez de TIMBRADA / …).

    No llama a db.add() ni db.commit() — responsabilidad del llamador.

    Returns:
        (nuevo_estatus: str, hubo_cambio: bool)
    """
    from app.models.pago import EstatusPago

    if ahora is None:
        ahora = datetime.utcnow()

    estatus_anterior: str = getattr(pago.estatus, "value", pago.estatus)
    nuevo: str = estatus_anterior

    if not acuse.encontrado:
        # Ver la nota en aplicar_acuse_sat: sin reconocimiento del SAT no hay
        # información sobre el estado real, así que no se toca nada.
        logger.warning(
            "[SAT] Complemento no verificable (%s) — no se modifica el estatus (%s)",
            acuse.codigo_estatus, estatus_anterior,
        )
        return estatus_anterior, False

    if acuse.cancelado_por_sat:
        nuevo = "CANCELADO"
        pago.fecha_solicitud_cancelacion = None

    elif acuse.en_proceso:
        nuevo = "EN_CANCELACION"
        if not pago.fecha_solicitud_cancelacion:
            pago.fecha_solicitud_cancelacion = ahora

    else:
        # El SAT reporta Vigente y sin cancelación en proceso
        if estatus_anterior == "CANCELADO":
            # Marcado como cancelado localmente pero vigente ante el SAT
            # (p. ej. el receptor rechazó la solicitud) → reconciliar.
            nuevo = "TIMBRADO"
            pago.fecha_solicitud_cancelacion = None
        elif estatus_anterior == "EN_CANCELACION":
            if acuse.rechazado_por_receptor:
                nuevo = "TIMBRADO"
                pago.fecha_solicitud_cancelacion = None
            elif pago.fecha_solicitud_cancelacion is None:
                pago.fecha_solicitud_cancelacion = ahora
            elif (ahora - pago.fecha_solicitud_cancelacion) >= timedelta(days=DIAS_CANCELACION_VENCIDA):
                # Solicitud vencida y el complemento sigue Vigente sin proceso:
                # la cancelación con aceptación expiró sin respuesta → revertir.
                nuevo = "TIMBRADO"
                pago.fecha_solicitud_cancelacion = None

    pago.estatus = EstatusPago(nuevo)
    return nuevo, estatus_anterior != nuevo
