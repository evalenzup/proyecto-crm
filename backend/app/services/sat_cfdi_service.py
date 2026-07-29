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

# Margen tras enviar la solicitud durante el cual confiamos en nuestro estado
# local aunque el SAT todavía no muestre el trámite (el registro puede tardar
# unos minutos). Pasado ese margen, si el SAT sigue sin reportar solicitud
# alguna, es que nunca se registró.
HORAS_GRACIA_SOLICITUD = 24

# Respaldo para el caso ambiguo: el SAT reporta un EstatusCancelacion que no
# sabemos interpretar (ni vacío, ni en proceso, ni rechazada). Tras estos días
# se revierte igual para no dejar el CFDI atorado indefinidamente.
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
    """
    Respuesta del SAT para la consulta de un CFDI.

    Campos y códigos según la "Documentación del Servicio de Consulta de CFDI"
    v1.3 (SAT, nov 2020). El Acuse trae cinco campos: CodigoEstatus, EsCancelable,
    Estado, EstatusCancelacion y ValidacionEFOS.
    """
    codigo_estatus: str          # "S - Comprobante obtenido satisfactoriamente" | "N - 601" | "N - 602"
    estado: str                  # "Vigente" | "Cancelado"
    es_cancelable: str           # "Cancelable sin aceptación" | "Cancelable con aceptación" | "No cancelable"
    estatus_cancelacion: str     # "En proceso" | "Solicitud rechazada" | "Cancelado con/sin aceptación" | "Plazo vencido" | ""
    validacion_efos: str = ""    # "100" = emisor en lista EFOS (69-B CFF) | "200" = no está en la lista

    @property
    def encontrado(self) -> bool:
        return self.codigo_estatus.startswith("S")

    @property
    def expresion_invalida(self) -> bool:
        """
        601: la expresión impresa no respeta el formato definido. En la práctica,
        que el RFC del emisor/receptor o el Total no coinciden con los del CFDI
        timbrado. El comprobante puede existir perfectamente en el SAT.
        """
        return "601" in (self.codigo_estatus or "")

    @property
    def no_existe_en_sat(self) -> bool:
        """602: el UUID no se encuentra en la base de datos del SAT."""
        return "602" in (self.codigo_estatus or "")

    @property
    def emisor_en_lista_efos(self) -> bool:
        """
        El RFC emisor está publicado en la lista de Empresas que Facturan
        Operaciones Simuladas (art. 69-B del CFF). Código 100 del servicio.
        """
        return (self.validacion_efos or "").strip() == "100"

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

    @property
    def sin_solicitud_registrada(self) -> bool:
        """
        El CFDI está Vigente y el SAT no reporta ningún trámite de cancelación.

        EstatusCancelacion vacío sobre un CFDI vigente significa que el SAT no
        tiene registrada ninguna solicitud: ni en proceso, ni rechazada, ni
        aplicada. O nunca llegó, o ya se resolvió sin cancelar.
        """
        return not self.cancelado and not (self.estatus_cancelacion or "").strip()

    @property
    def no_cancelable(self) -> bool:
        """
        El SAT no permite cancelar este CFDI (normalmente porque tiene otros
        CFDI relacionados). Una solicitud sobre él nunca va a prosperar.
        """
        return "no cancelable" in (self.es_cancelable or "").lower()


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
    validacion_efos = _text("ValidacionEFOS")

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
            elif local == "ValidacionEFOS":
                validacion_efos = (el.text or "").strip()

    if not codigo_estatus:
        raise RuntimeError("El SAT no devolvió CodigoEstatus en la respuesta")

    acuse = AcuseSAT(
        codigo_estatus=codigo_estatus,
        estado=estado,
        es_cancelable=es_cancelable,
        estatus_cancelacion=estatus_cancelacion,
        validacion_efos=validacion_efos,
    )
    if acuse.emisor_en_lista_efos:
        # Alerta fiscal seria: el RFC emisor aparece en la lista del 69-B del CFF.
        logger.error(
            "[SAT] ⚠️ El RFC emisor está publicado en la lista EFOS (art. 69-B CFF). "
            "Acuse: %s", codigo_estatus,
        )
    return acuse


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
        (< HORAS_GRACIA_SOLICITUD)                  reflejar la solicitud recién enviada)
      · SAT dice Vigente SIN trámite registrado    → revertir a TIMBRADA (la solicitud nunca se
        (EstatusCancelacion vacío)                  registró en el SAT, o se resolvió sin cancelar)
      · SAT dice Vigente con estatus desconocido   → revertir a TIMBRADA tras DIAS_CANCELACION_VENCIDA
                                                    (respaldo, para no dejarlo atorado)

    No llama a db.add() ni db.commit() — responsabilidad del llamador.

    Returns:
        (nuevo_estatus: str, hubo_cambio: bool)
    """
    if ahora is None:
        ahora = datetime.utcnow()

    estatus_anterior: str = factura.estatus
    nuevo_estatus: str = estatus_anterior  # por defecto no cambia

    if not acuse.encontrado:
        # El SAT no reconoció el CFDI. No sabemos nada de su estado real, así que
        # cualquier decisión aquí sería a ciegas (antes esto caía en la rama
        # "Vigente sin proceso" y podía revertir a TIMBRADA una factura cancelada).
        #   601 → la expresión impresa no coincide: el RFC o el Total que enviamos
        #         no son los del CFDI timbrado. El comprobante sí existe.
        #   602 → el UUID no está en la base de datos del SAT.
        if acuse.expresion_invalida:
            detalle = "los datos enviados no coinciden con el CFDI timbrado (601)"
        elif acuse.no_existe_en_sat:
            detalle = "el UUID no existe en la base del SAT (602)"
        else:
            detalle = acuse.codigo_estatus
        logger.warning(
            "[SAT] CFDI no verificable: %s — no se modifica el estatus (%s)",
            detalle, estatus_anterior,
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
            antiguedad = (
                ahora - factura.fecha_solicitud_cancelacion
                if factura.fecha_solicitud_cancelacion
                else None
            )
            if acuse.rechazado_por_receptor:
                # El receptor rechazó explícitamente → revertir a TIMBRADA
                nuevo_estatus = "TIMBRADA"
                factura.fecha_solicitud_cancelacion = None
            elif antiguedad is None:
                # Sin fecha registrada: anclar ahora para tener referencia,
                # pero NO revertir — el SAT puede tardar en reflejar la solicitud
                factura.fecha_solicitud_cancelacion = ahora
            elif acuse.sin_solicitud_registrada and antiguedad >= timedelta(
                hours=HORAS_GRACIA_SOLICITUD
            ):
                # El SAT no tiene registrada ninguna solicitud sobre este CFDI y
                # ya pasó el margen: la cancelación nunca llegó a registrarse
                # (o se resolvió sin cancelar) → revertir a TIMBRADA.
                logger.info(
                    "[SAT] CFDI %s sin solicitud de cancelación registrada en el SAT "
                    "(%s) → se revierte a TIMBRADA",
                    getattr(factura, "cfdi_uuid", "?"),
                    "no cancelable" if acuse.no_cancelable else "cancelable",
                )
                nuevo_estatus = "TIMBRADA"
                factura.fecha_solicitud_cancelacion = None
            elif antiguedad >= timedelta(days=DIAS_CANCELACION_VENCIDA):
                # Caso ambiguo: el SAT reporta un EstatusCancelacion que no
                # sabemos interpretar. Se revierte para no dejarlo atorado.
                logger.warning(
                    "[SAT] CFDI %s con EstatusCancelacion no reconocido (%r) tras "
                    "%d días → se revierte a TIMBRADA",
                    getattr(factura, "cfdi_uuid", "?"),
                    acuse.estatus_cancelacion,
                    antiguedad.days,
                )
                nuevo_estatus = "TIMBRADA"
                factura.fecha_solicitud_cancelacion = None
            # else: solicitud dentro del margen → mantener EN_CANCELACION

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
            antiguedad = (
                ahora - pago.fecha_solicitud_cancelacion
                if pago.fecha_solicitud_cancelacion
                else None
            )
            if acuse.rechazado_por_receptor:
                nuevo = "TIMBRADO"
                pago.fecha_solicitud_cancelacion = None
            elif antiguedad is None:
                pago.fecha_solicitud_cancelacion = ahora
            elif acuse.sin_solicitud_registrada and antiguedad >= timedelta(
                hours=HORAS_GRACIA_SOLICITUD
            ):
                # El SAT no tiene registrada solicitud alguna → nunca se aplicó.
                nuevo = "TIMBRADO"
                pago.fecha_solicitud_cancelacion = None
            elif antiguedad >= timedelta(days=DIAS_CANCELACION_VENCIDA):
                # Caso ambiguo (EstatusCancelacion no reconocido) → no dejarlo atorado.
                nuevo = "TIMBRADO"
                pago.fecha_solicitud_cancelacion = None

    pago.estatus = EstatusPago(nuevo)
    return nuevo, estatus_anterior != nuevo
