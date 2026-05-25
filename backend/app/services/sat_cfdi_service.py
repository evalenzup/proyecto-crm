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
from datetime import datetime
from typing import Any, Optional, Tuple

import httpx
from lxml import etree

logger = logging.getLogger("app")

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

VENTANA_72H = 72.0  # horas antes de considerar que el receptor rechazó


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
      · SAT dice Cancelado          → estatus = "CANCELADA"
      · SAT dice En proceso         → estatus = "EN_CANCELACION"
                                      registra fecha_solicitud_cancelacion si no existe
      · SAT dice Vigente (no en proceso):
          - Si la factura estaba EN_CANCELACION:
              · Sin fecha de solicitud registrada → revertir a TIMBRADA
              · Con fecha y han pasado ≥72 h      → revertir a TIMBRADA (receptor rechazó)
              · Con fecha y dentro de las 72 h    → NO tocar (SAT puede tardar en actualizarse)
          - Si estaba TIMBRADA/CANCELADA → sin cambio

    No llama a db.add() ni db.commit() — responsabilidad del llamador.

    Returns:
        (nuevo_estatus: str, hubo_cambio: bool)
    """
    if ahora is None:
        ahora = datetime.utcnow()

    estatus_anterior: str = factura.estatus
    nuevo_estatus: str = estatus_anterior  # por defecto no cambia

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
        if estatus_anterior == "EN_CANCELACION":
            fecha_sol = factura.fecha_solicitud_cancelacion
            if fecha_sol is None:
                # Sin fecha → no hay forma de calcular las 72 h → revertir
                nuevo_estatus = "TIMBRADA"
                factura.fecha_solicitud_cancelacion = None
            else:
                horas = (ahora - fecha_sol).total_seconds() / 3600
                if horas >= VENTANA_72H:
                    # Pasó la ventana y SAT sigue Vigente → receptor rechazó
                    nuevo_estatus = "TIMBRADA"
                    factura.fecha_solicitud_cancelacion = None
                # else: dentro de 72 h → esperamos, no tocar el estatus

    factura.estatus = nuevo_estatus
    return nuevo_estatus, estatus_anterior != nuevo_estatus
