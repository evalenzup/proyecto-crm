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

import logging
from dataclasses import dataclass
from typing import Optional

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
    body = SOAP_TEMPLATE.format(expresion=expresion)

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
