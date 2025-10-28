# app/services/timbrado_factmoderna.py
from __future__ import annotations

import os
import re
import base64
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

import httpx
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring

from sqlalchemy.orm import Session

from app.config import settings
from app.models.factura import Factura
from app.models.pago import Pago
from app.services.cfdi40_xml import build_cfdi40_xml_sin_timbrar
from app.services.pago20_xml import build_pago20_xml_sin_timbrar

try:
    from app.core.logger import logger
except Exception:
    logger = None


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────
def _fm_user_id() -> str:
    return getattr(settings, "FM_USER_ID", "") or os.getenv("FM_USER_ID", "")


def _fm_user_pass() -> str:
    return getattr(settings, "FM_USER_PASS", "") or os.getenv("FM_USER_PASS", "")


def _fm_url() -> str:
    # Usa el endpoint que corresponda a tu cuenta (t1/t2/prod)
    return getattr(
        settings, "FM_TIMBRADO_URL", "http://t1.facturacionmoderna.com/timbrado/soap"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SOAP request builder
# ─────────────────────────────────────────────────────────────────────────────
def _soap_timbrar_envelope(
    *,
    user_id: str,
    user_pass: str,
    emisor_rfc: str,
    xml_b64: str,
    generar_cbb: bool = False,
    generar_txt: bool = False,
    generar_pdf: bool = False,
) -> bytes:
    ENV = "http://schemas.xmlsoap.org/soap/envelope/"
    NS1 = "http://t1.facturacionmoderna.com/timbrado/soap"
    XSD = "http://www.w3.org/2001/XMLSchema"
    XSI = "http://www.w3.org/2001/XMLSchema-instance"
    ENC = "http://schemas.xmlsoap.org/soap/encoding/"

    envelope = Element(
        "SOAP-ENV:Envelope",
        {
            "xmlns:SOAP-ENV": ENV,
            "xmlns:ns1": NS1,
            "xmlns:xsd": XSD,
            "xmlns:xsi": XSI,
            "xmlns:SOAP-ENC": ENC,
            "SOAP-ENV:encodingStyle": ENC,
        },
    )
    body = SubElement(envelope, "SOAP-ENV:Body")
    op = SubElement(body, "ns1:requestTimbrarCFDI")
    req = SubElement(op, "request", {"xsi:type": "SOAP-ENC:Struct"})

    def add_str(name: str, value: str):
        SubElement(req, name, {"xsi:type": "xsd:string"}).text = value

    add_str("UserID", user_id)
    add_str("UserPass", user_pass)
    add_str("emisorRFC", emisor_rfc)
    add_str("text2CFDI", xml_b64)
    add_str("generarCBB", "true" if generar_cbb else "false")
    add_str("generarTXT", "true" if generar_txt else "false")
    add_str("generarPDF", "true" if generar_pdf else "false")

    return tostring(envelope, encoding="utf-8", xml_declaration=True)


def _soap_timbrar_pago_envelope(
    *,
    user_id: str,
    user_pass: str,
    emisor_rfc: str,
    xml_b64: str,
    generar_cbb: bool = False,
    generar_txt: bool = False,
    generar_pdf: bool = False,
) -> bytes:
    ENV = "http://schemas.xmlsoap.org/soap/envelope/"
    NS1 = "http://t1.facturacionmoderna.com/timbrado/soap"
    XSD = "http://www.w3.org/2001/XMLSchema"
    XSI = "http://www.w3.org/2001/XMLSchema-instance"
    ENC = "http://schemas.xmlsoap.org/soap/encoding/"

    envelope = Element(
        "SOAP-ENV:Envelope",
        {
            "xmlns:SOAP-ENV": ENV,
            "xmlns:ns1": NS1,
            "xmlns:xsd": XSD,
            "xmlns:xsi": XSI,
            "xmlns:SOAP-ENC": ENC,
            "SOAP-ENV:encodingStyle": ENC,
        },
    )
    body = SubElement(envelope, "SOAP-ENV:Body")
    op = SubElement(
        body, "ns1:requestTimbrarCFDI"
    )  # The same endpoint is used for CFDI and Pago
    req = SubElement(op, "request", {"xsi:type": "SOAP-ENC:Struct"})

    def add_str(name: str, value: str):
        SubElement(req, name, {"xsi:type": "xsd:string"}).text = value

    add_str("UserID", user_id)
    add_str("UserPass", user_pass)
    add_str("emisorRFC", emisor_rfc)
    add_str("text2CFDI", xml_b64)
    add_str("generarCBB", "true" if generar_cbb else "false")
    add_str("generarTXT", "true" if generar_txt else "false")
    add_str("generarPDF", "true" if generar_pdf else "false")

    return tostring(envelope, encoding="utf-8", xml_declaration=True)


# ─────────────────────────────────────────────────────────────────────────────
# SOAP response helpers
# ─────────────────────────────────────────────────────────────────────────────
def _etree_strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _find_first_text(root, local_names) -> Optional[str]:
    wanted = {n.lower() for n in local_names}
    for el in root.iter():
        if _etree_strip_ns(el.tag).lower() in wanted:
            txt = (el.text or "").strip()
            if txt:
                return txt
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SOAP request builder: CANCELACIÓN
# ─────────────────────────────────────────────────────────────────────────────
def _soap_cancelar_envelope(
    *,
    user_id: str,
    user_pass: str,
    emisor_rfc: str,
    uuid: str,
    motivo: str,
    folio_sustitucion: str | None = None,
) -> bytes:
    """
    Crea el envelope SOAP 1.2 para requestCancelarCFDI (Facturación Moderna).
    """
    ENV = "http://schemas.xmlsoap.org/soap/envelope/"
    NS1 = (
        "https://t1demo.facturacionmoderna.com/timbrado/soap"  # usan este ns en la doc
    )
    XSD = "http://www.w3.org/2001/XMLSchema"
    XSI = "http://www.w3.org/2001/XMLSchema-instance"
    ENC = "http://schemas.xmlsoap.org/soap/encoding/"

    envelope = Element(
        "SOAP-ENV:Envelope",
        {
            "xmlns:SOAP-ENV": ENV,
            "xmlns:ns1": NS1,
            "xmlns:xsd": XSD,
            "xmlns:xsi": XSI,
            "xmlns:SOAP-ENC": ENC,
            "SOAP-ENV:encodingStyle": ENC,
        },
    )
    body = SubElement(envelope, "SOAP-ENV:Body")
    op = SubElement(body, "ns1:requestCancelarCFDI")
    req = SubElement(op, "request", {"xsi:type": "SOAP-ENC:Struct"})

    def add_str(name: str, value: str):
        SubElement(req, name, {"xsi:type": "xsd:string"}).text = value

    add_str("UserPass", user_pass)
    add_str("UserID", user_id)
    add_str("emisorRFC", emisor_rfc)
    add_str("uuid", uuid)
    add_str("Motivo", motivo)
    if motivo == "01" and folio_sustitucion:
        add_str("FolioSustitucion", folio_sustitucion)

    return tostring(envelope, encoding="utf-8", xml_declaration=True)


def _parse_cancel_response(root) -> dict:
    """
    Extrae Code/Message de la respuesta SOAP de cancelación.
    Devuelve {"code": "...", "message": "..."} si los encuentra.
    Lanza RuntimeError en Fault o si no se encuentra información.
    """
    # Fault?
    for el in root.iter():
        if _etree_strip_ns(el.tag) == "Fault":
            code = None
            msg = None
            for ch in el:
                ln = _etree_strip_ns(ch.tag)
                if ln == "faultcode":
                    code = (ch.text or "").strip()
                if ln == "faultstring":
                    msg = (ch.text or "").strip()
            raise RuntimeError(
                f"PAC cancelación Fault: {code or ''} {msg or ''}".strip()
            )

    code = None
    message = None
    for el in root.iter():
        ln = _etree_strip_ns(el.tag).lower()
        if ln == "code":
            code = (el.text or "").strip()
        elif ln == "message":
            message = (el.text or "").strip()

    if not (code or message):
        # fallback: busca cualquier <return> con pares
        ret_node = None
        for el in root.iter():
            if _etree_strip_ns(el.tag).lower() == "return":
                ret_node = el
                break
        if ret_node is not None:
            for ch in ret_node:
                ln = _etree_strip_ns(ch.tag).lower()
                if ln == "code":
                    code = (ch.text or "").strip()
                elif ln == "message":
                    message = (ch.text or "").strip()

    if not (code or message):
        raise RuntimeError(
            "No se hallaron Code/Message en la respuesta SOAP de cancelación."
        )

    return {"code": code, "message": message}


# ─────────────────────────────────────────────────────────────────────────────
# TFD extractors (XML + regex fallback)
# ─────────────────────────────────────────────────────────────────────────────
def _parse_tfd_fields_xml(cfdi_bytes: bytes) -> Dict[str, Any]:
    """
    Intenta encontrar el nodo TimbreFiscalDigital por 'local-name()' independientemente del namespace.
    """
    try:
        root = fromstring(cfdi_bytes)
    except Exception:
        return {}

    for el in root.iter():
        if _etree_strip_ns(el.tag) == "TimbreFiscalDigital":
            g = el.attrib.get
            return {
                "uuid": g("UUID"),
                "fecha_timbrado": g("FechaTimbrado"),
                "rfc_prov_certif": g("RfcProvCertif"),
                "sello_cfdi": g("SelloCFD"),
                "no_certificado_sat": g("NoCertificadoSAT"),
                "sello_sat": g("SelloSAT"),
            }
    return {}


# regex robustos (toleran espacios, orden y comillas simples/dobles)
_RE_UUID = re.compile(rb'UUID\s*=\s*["\']([0-9A-Fa-f-]{36})["\']')
_RE_FECHA = re.compile(rb'FechaTimbrado\s*=\s*["\']([^"\']+)["\']')
_RE_RFC_PROV = re.compile(rb'RfcProvCertif\s*=\s*["\']([^"\']+)["\']')
_RE_SELLO_CFD = re.compile(rb'SelloCFD\s*=\s*["\']([^"\']+)["\']')
_RE_CERT_SAT = re.compile(rb'NoCertificadoSAT\s*=\s*["\']([^"\']+)["\']')
_RE_SELLO_SAT = re.compile(rb'SelloSAT\s*=\s*["\']([^"\']+)["\']')


def _parse_tfd_fields_regex(cfdi_bytes: bytes) -> Dict[str, Any]:
    """
    Fallback por si el parser no encuentra el nodo (namespaces raros, minificado, etc.).
    """

    def m(rx):
        mm = rx.search(cfdi_bytes)
        return mm.group(1).decode("utf-8", "ignore") if mm else None

    return {
        "uuid": m(_RE_UUID),
        "fecha_timbrado": m(_RE_FECHA),
        "rfc_prov_certif": m(_RE_RFC_PROV),
        "sello_cfdi": m(_RE_SELLO_CFD),
        "no_certificado_sat": m(_RE_CERT_SAT),
        "sello_sat": m(_RE_SELLO_SAT),
    }


def _parse_tfd_fields(cfdi_bytes: bytes) -> Dict[str, Any]:
    """
    Orquesta: primero XML, luego regex; regresa dict sólo con keys encontradas.
    """
    tfd = _parse_tfd_fields_xml(cfdi_bytes)
    if tfd.get("uuid"):
        return tfd
    # fallback
    tfd2 = _parse_tfd_fields_regex(cfdi_bytes)
    # merge conservando lo hallado en XML si existiera
    out = {**tfd2, **{k: v for k, v in tfd.items() if v}}
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Guardado de archivos
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_cfdi_dir() -> str:
    if not hasattr(settings, "DATA_DIR") or not settings.DATA_DIR:
        raise ValueError("La configuración DATA_DIR no está definida.")
    base = settings.DATA_DIR
    out_dir = os.path.join(base, "cfdis")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _build_base_filename(f: Factura, uuid: Optional[str]) -> str:
    rfc = (getattr(getattr(f, "empresa", None), "rfc", "") or "").upper()
    serie = (getattr(f, "serie", None) or "").strip() or "SN"
    folio = str(getattr(f, "folio", None) or "").strip() or "SN"
    return f"{rfc}-{serie}-{folio}-{uuid or f.id}"


def _save_bytes(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _save_b64(path: str, b64: Optional[str]) -> Optional[str]:
    if not b64:
        return None
    try:
        _save_bytes(path, base64.b64decode(b64))
        return path
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Servicio principal
# ─────────────────────────────────────────────────────────────────────────────
class FacturacionModernaPAC:
    """
    Timbrado CFDI 4.0 vía SOAP con Facturación Moderna.
    - Loguea el SOAP (truncado) y previews de XML timbrado (inicio/fin).
    - Extrae TFD por XML y regex.
    - Guarda XML/PDF/CBB/TXT en disco y persiste campos TFD en DB.
    """

    def __init__(self, *, timeout: float = 60.0):
        self.timeout = timeout

    def timbrar_factura(
        self,
        *,
        db: Session,
        factura_id: UUID,
        generar_cbb: bool = False,
        generar_txt: bool = False,
        generar_pdf: bool = False,
    ) -> Dict[str, Any]:
        # 1) Cargar factura
        f: Optional[Factura] = (
            db.query(Factura).filter(Factura.id == factura_id).first()
        )
        if not f:
            raise ValueError("Factura no encontrada")
        if f.estatus != "BORRADOR":
            raise ValueError("Solo se puede timbrar una factura en BORRADOR")
        if not f.empresa or not f.empresa.rfc:
            raise ValueError(
                "La factura no tiene empresa válida (RFC emisor requerido)."
            )

        # 2) XML sin timbrar (sellado internamente en cfdi40_xml)
        xml_sin_timbre: bytes = build_cfdi40_xml_sin_timbrar(
            db=db, factura_id=factura_id
        )
        xml_b64 = base64.b64encode(xml_sin_timbre).decode("utf-8")

        # 3) SOAP y POST
        env = _soap_timbrar_envelope(
            user_id=_fm_user_id(),
            user_pass=_fm_user_pass(),
            emisor_rfc=f.empresa.rfc,
            xml_b64=xml_b64,
            generar_cbb=generar_cbb,
            generar_txt=generar_txt,
            generar_pdf=generar_pdf,
        )
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "requestTimbrarCFDI",
        }
        url = _fm_url()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, content=env, headers=headers)
        except Exception as e:
            raise RuntimeError(f"Error de red al timbrar: {e}") from e

        # Log SOAP (truncado)
        soap_txt = resp.text
        soap_log = (
            soap_txt
            if len(soap_txt) <= 20000
            else soap_txt[:20000] + "\n... [truncated]"
        )
        (logger.info if logger else print)(
            f"[PAC SOAP] HTTP {resp.status_code}\n{soap_log}"
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code} del PAC: {soap_txt}")

        # 4) Parse SOAP → obtener <xml> (Base64)
        try:
            root = fromstring(resp.content)
        except Exception as e:
            raise RuntimeError(f"Respuesta SOAP inválida: {e}")

        # Detecta Fault si existe
        for el in root.iter():
            if _etree_strip_ns(el.tag) == "Fault":
                code = None
                msg = None
                for ch in el:
                    ln = _etree_strip_ns(ch.tag)
                    if ln == "faultcode":
                        code = (ch.text or "").strip()
                    if ln == "faultstring":
                        msg = (ch.text or "").strip()
                raise RuntimeError(
                    f"PAC devolvió Fault: {code or ''} {msg or ''}".strip()
                )

        cfdi_b64 = _find_first_text(
            root,
            ["xml", "cfdi", "xmlTimbrado", "cfdiTimbrado", "response", "returnXml"],
        )
        if not cfdi_b64:
            raise RuntimeError(
                "No se encontró el nodo <xml> (CFDI timbrado en Base64) en la respuesta del PAC."
            )

        # Adjuntos opcionales
        pdf_b64 = _find_first_text(root, ["pdf", "PDF"]) if generar_pdf else None
        cbb_b64 = _find_first_text(root, ["cbb", "CBB"]) if generar_cbb else None
        txt_b64 = _find_first_text(root, ["txt", "TXT"]) if generar_txt else None

        # 5) Decodificar el CFDI timbrado
        try:
            cfdi_bytes = base64.b64decode(cfdi_b64)
        except Exception as e:
            raise RuntimeError(f"No se pudo decodificar el XML timbrado (base64): {e}")

        # Debug: previews de inicio/fin
        head = cfdi_bytes[:400].decode("utf-8", "ignore")
        tail = cfdi_bytes[-400:].decode("utf-8", "ignore")
        (logger.info if logger else print)(f"[CFDI preview:head]\n{head}")
        (logger.info if logger else print)(f"[CFDI preview:tail]\n{tail}")

        # 6) Extraer TFD (XML → regex fallback)
        tfd = _parse_tfd_fields(cfdi_bytes)
        if not tfd.get("uuid"):
            (logger.warning if logger else print)(
                "⚠️ TFD no detectado por parser/regex. Verifica respuesta del PAC."
            )
            # Aún así guardamos el XML y respondemos con detalle para inspección.
            out_dir = _ensure_cfdi_dir()
            xml_only = os.path.join(
                out_dir, _build_base_filename(f, None) + "-SINUUID.xml"
            )
            _save_bytes(xml_only, cfdi_bytes)
            raise RuntimeError("El PAC no devolvió UUID en el TFD.")

        # 7) Guardar archivos en disco
        out_dir = _ensure_cfdi_dir()
        base_name = _build_base_filename(f, tfd["uuid"])
        xml_path = os.path.join(out_dir, base_name + ".xml")
        _save_bytes(xml_path, cfdi_bytes)

        pdf_path = os.path.join(out_dir, base_name + ".pdf") if pdf_b64 else None
        cbb_path = os.path.join(out_dir, base_name + ".png") if cbb_b64 else None
        txt_path = os.path.join(out_dir, base_name + ".txt") if txt_b64 else None
        if pdf_b64:
            _save_b64(pdf_path, pdf_b64)
        if cbb_b64:
            _save_b64(cbb_path, cbb_b64)
        if txt_b64:
            _save_b64(txt_path, txt_b64)

        # 8) Persistir en DB
        f.cfdi_uuid = tfd.get("uuid")

        # FechaTimbrado → datetime
        fecha_timbrado_iso = tfd.get("fecha_timbrado")
        fecha_timbrado_dt: Optional[datetime] = None
        if fecha_timbrado_iso:
            try:
                fecha_timbrado_dt = datetime.fromisoformat(
                    fecha_timbrado_iso.replace("Z", "+00:00")
                )
            except Exception:
                try:
                    fecha_timbrado_dt = datetime.fromisoformat(
                        fecha_timbrado_iso.split(".")[0]
                    )
                except Exception:
                    fecha_timbrado_dt = None
        f.fecha_timbrado = fecha_timbrado_dt

        # Campos TFD
        f.no_certificado_sat = tfd.get("no_certificado_sat")
        f.sello_sat = tfd.get("sello_sat")
        f.sello_cfdi = tfd.get("sello_cfdi")
        f.rfc_proveedor_sat = tfd.get("rfc_prov_certif")

        # Paths
        if hasattr(f, "xml_path"):
            f.xml_path = xml_path
        if hasattr(f, "pdf_path"):
            f.pdf_path = pdf_path if pdf_b64 else None
        if hasattr(f, "cbb_path"):
            setattr(f, "cbb_path", cbb_path if cbb_b64 else None)
        if hasattr(f, "txt_path"):
            setattr(f, "txt_path", txt_path if txt_b64 else None)

        f.estatus = "TIMBRADA"
        db.add(f)
        db.commit()
        db.refresh(f)

        # 9) Respuesta
        out: Dict[str, Any] = {
            "timbrada": True,
            "uuid": f.cfdi_uuid,
            "fecha_timbrado": f.fecha_timbrado.isoformat()
            if f.fecha_timbrado
            else None,
            "rfc_proveedor_sat": tfd.get("rfc_prov_certif"),
            "no_certificado_sat": f.no_certificado_sat,
            "sello_cfdi": f.sello_cfdi,
            "sello_sat": f.sello_sat,
            "xml_path": xml_path,
        }
        if pdf_b64:
            out["pdf_path"] = pdf_path
        if cbb_b64:
            out["cbb_path"] = cbb_path
        if txt_b64:
            out["txt_path"] = txt_path
        # si quieres exponer el XML timbrado en base64:
        out["cfdi_b64"] = cfdi_b64
        return out

    def timbrar_pago(
        self,
        *,
        db: Session,
        pago_id: UUID,
        generar_cbb: bool = False,
        generar_txt: bool = False,
        generar_pdf: bool = False,
    ) -> Dict[str, Any]:
        # 1) Cargar pago
        p: Optional[Pago] = db.query(Pago).filter(Pago.id == pago_id).first()
        if not p:
            raise ValueError("Pago no encontrado")
        if p.estatus != "BORRADOR":
            raise ValueError("Solo se puede timbrar un pago en BORRADOR")
        if not p.empresa or not p.empresa.rfc:
            raise ValueError("El pago no tiene empresa válida (RFC emisor requerido).")

        # 2) XML sin timbrar (sellado internamente en pago20_xml)
        xml_sin_timbre: bytes = build_pago20_xml_sin_timbrar(db=db, pago_id=pago_id)

        print("--- INICIO: XML del Complemento de Pago (sin timbrar) ---")
        print(xml_sin_timbre.decode("utf-8"))
        print("--- FIN: XML del Complemento de Pago (sin timbrar) ---")

        xml_b64 = base64.b64encode(xml_sin_timbre).decode("utf-8")

        # 3) SOAP y POST
        env = _soap_timbrar_pago_envelope(
            user_id=_fm_user_id(),
            user_pass=_fm_user_pass(),
            emisor_rfc=p.empresa.rfc,
            xml_b64=xml_b64,
            generar_cbb=generar_cbb,
            generar_txt=generar_txt,
            generar_pdf=generar_pdf,
        )
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "requestTimbrarCFDI",
        }
        url = _fm_url()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, content=env, headers=headers)
        except Exception as e:
            raise RuntimeError(f"Error de red al timbrar: {e}") from e

        # Log SOAP (truncado)
        soap_txt = resp.text
        soap_log = (
            soap_txt
            if len(soap_txt) <= 20000
            else soap_txt[:20000] + "\n... [truncated]"
        )
        (logger.info if logger else print)(
            f"[PAC SOAP] HTTP {resp.status_code}\n{soap_log}"
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code} del PAC: {soap_txt}")

        # 4) Parse SOAP → obtener <xml> (Base64)
        try:
            root = fromstring(resp.content)
        except Exception as e:
            raise RuntimeError(f"Respuesta SOAP inválida: {e}")

        # Detecta Fault si existe
        for el in root.iter():
            if _etree_strip_ns(el.tag) == "Fault":
                code = None
                msg = None
                for ch in el:
                    ln = _etree_strip_ns(ch.tag)
                    if ln == "faultcode":
                        code = (ch.text or "").strip()
                    if ln == "faultstring":
                        msg = (ch.text or "").strip()
                raise RuntimeError(
                    f"PAC devolvió Fault: {code or ''} {msg or ''}".strip()
                )

        cfdi_b64 = _find_first_text(
            root,
            ["xml", "cfdi", "xmlTimbrado", "cfdiTimbrado", "response", "returnXml"],
        )
        if not cfdi_b64:
            raise RuntimeError(
                "No se encontró el nodo <xml> (CFDI timbrado en Base64) en la respuesta del PAC."
            )

        # Adjuntos opcionales
        pdf_b64 = _find_first_text(root, ["pdf", "PDF"]) if generar_pdf else None
        cbb_b64 = _find_first_text(root, ["cbb", "CBB"]) if generar_cbb else None
        txt_b64 = _find_first_text(root, ["txt", "TXT"]) if generar_txt else None

        # 5) Decodificar el CFDI timbrado
        try:
            cfdi_bytes = base64.b64decode(cfdi_b64)
        except Exception as e:
            raise RuntimeError(f"No se pudo decodificar el XML timbrado (base64): {e}")

        # Debug: previews de inicio/fin
        head = cfdi_bytes[:400].decode("utf-8", "ignore")
        tail = cfdi_bytes[-400:].decode("utf-8", "ignore")
        (logger.info if logger else print)(f"[CFDI preview:head]\n{head}")
        (logger.info if logger else print)(f"[CFDI preview:tail]\n{tail}")

        # 6) Extraer TFD (XML → regex fallback)
        tfd = _parse_tfd_fields(cfdi_bytes)
        if not tfd.get("uuid"):
            (logger.warning if logger else print)(
                "⚠️ TFD no detectado por parser/regex. Verifica respuesta del PAC."
            )
            # Aún así guardamos el XML y respondemos con detalle para inspección.
            out_dir = _ensure_cfdi_dir()
            xml_only = os.path.join(
                out_dir, _build_base_filename(p, None) + "-SINUUID.xml"
            )
            _save_bytes(xml_only, cfdi_bytes)
            raise RuntimeError("El PAC no devolvió UUID en el TFD.")

        # 7) Guardar archivos en disco
        out_dir = _ensure_cfdi_dir()
        base_name = _build_base_filename(p, tfd["uuid"])
        xml_path = os.path.join(out_dir, base_name + ".xml")
        _save_bytes(xml_path, cfdi_bytes)

        pdf_path = os.path.join(out_dir, base_name + ".pdf") if pdf_b64 else None
        cbb_path = os.path.join(out_dir, base_name + ".png") if cbb_b64 else None
        txt_path = os.path.join(out_dir, base_name + ".txt") if txt_b64 else None
        if pdf_b64:
            _save_b64(pdf_path, pdf_b64)
        if cbb_b64:
            _save_b64(cbb_path, cbb_b64)
        if txt_b64:
            _save_b64(txt_path, txt_b64)

        # 8) Persistir en DB
        p.uuid = tfd.get("uuid")

        # FechaTimbrado → datetime
        fecha_timbrado_iso = tfd.get("fecha_timbrado")
        fecha_timbrado_dt: Optional[datetime] = None
        if fecha_timbrado_iso:
            try:
                fecha_timbrado_dt = datetime.fromisoformat(
                    fecha_timbrado_iso.replace("Z", "+00:00")
                )
            except Exception:
                try:
                    fecha_timbrado_dt = datetime.fromisoformat(
                        fecha_timbrado_iso.split(".")[0]
                    )
                except Exception:
                    fecha_timbrado_dt = None
        p.fecha_timbrado = fecha_timbrado_dt

        # Campos TFD
        p.no_certificado_sat = tfd.get("no_certificado_sat")
        p.sello_sat = tfd.get("sello_sat")
        p.sello_cfdi = tfd.get("sello_cfdi")
        p.rfc_proveedor_sat = tfd.get("rfc_prov_certif")

        # Paths
        if hasattr(p, "xml_path"):
            p.xml_path = xml_path
        if hasattr(p, "pdf_path"):
            p.pdf_path = pdf_path if pdf_b64 else None
        # if hasattr(p, "cbb_path"):
        #     setattr(p, "cbb_path", cbb_path if cbb_b64 else None)
        # if hasattr(p, "txt_path"):
        #     setattr(p, "txt_path", txt_path if txt_b64 else None)

        p.estatus = "TIMBRADO"
        db.add(p)
        db.commit()
        db.refresh(p)

        # 9) Respuesta
        out: Dict[str, Any] = {
            "timbrada": True,
            "uuid": p.uuid,
            "fecha_timbrado": p.fecha_timbrado.isoformat()
            if p.fecha_timbrado
            else None,
            "rfc_proveedor_sat": tfd.get("rfc_prov_certif"),
            "no_certificado_sat": p.no_certificado_sat,
            "sello_cfdi": p.sello_cfdi,
            "sello_sat": p.sello_sat,
            "xml_path": xml_path,
        }
        if pdf_b64:
            out["pdf_path"] = pdf_path
        if cbb_b64:
            out["cbb_path"] = cbb_path
        if txt_b64:
            out["txt_path"] = txt_path
        # si quieres exponer el XML timbrado en base64:
        out["cfdi_b64"] = cfdi_b64
        return out

    def solicitar_cancelacion_cfdi(
        self,
        *,
        db: Session,
        factura_id: UUID,
        motivo: str,
        folio_sustitucion: str | None = None,
    ) -> dict:
        """
        Envía la SOLICITUD de cancelación (cola del PAC/SAT).
        NO cambia a CANCELADA aquí (el PAC la procesa en cola).
        """
        # 1) Cargar factura
        f: Factura | None = db.query(Factura).filter(Factura.id == factura_id).first()
        if not f:
            raise ValueError("Factura no encontrada")

        if (f.estatus or "").upper() != "TIMBRADA":
            raise ValueError(
                "Solo se puede solicitar cancelación de una factura TIMBRADA"
            )

        uuid = (getattr(f, "cfdi_uuid", None) or "").strip()
        if not uuid:
            raise ValueError("La factura TIMBRADA no tiene UUID registrado")

        emisor_rfc = (
            (getattr(getattr(f, "empresa", None), "rfc", None) or "").strip().upper()
        )
        if not emisor_rfc:
            raise ValueError("La factura no tiene RFC de emisor")

        # Regla del motivo 01
        if motivo == "01" and not (folio_sustitucion or "").strip():
            raise ValueError(
                "Para Motivo '01' es obligatorio FolioSustitucion (UUID que sustituye)"
            )

        # 2) SOAP envelope
        env = _soap_cancelar_envelope(
            user_id=_fm_user_id(),
            user_pass=_fm_user_pass(),
            emisor_rfc=emisor_rfc,
            uuid=uuid,
            motivo=motivo,
            folio_sustitucion=(folio_sustitucion or "").strip() or None,
        )

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "requestCancelarCFDI",
        }
        url = _fm_url()

        # 3) POST
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, content=env, headers=headers)
        except Exception as e:
            raise RuntimeError(f"Error de red al solicitar cancelación: {e}") from e

        soap_txt = resp.text
        soap_log = (
            soap_txt
            if len(soap_txt) <= 20000
            else soap_txt[:20000] + "\n... [truncated]"
        )
        (logger.info if logger else print)(
            f"[PAC SOAP Cancel] HTTP {resp.status_code}\n{soap_log}"
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"HTTP {resp.status_code} del PAC (cancelación): {soap_txt}"
            )

        try:
            root = fromstring(resp.content)
        except Exception as e:
            raise RuntimeError(f"Respuesta SOAP inválida (cancelación): {e}")

        # 4) Parse Code/Message
        res = _parse_cancel_response(root)  # {"code": "...", "message": "..."}

        # 5) Persistir marca opcional (no cambiamos estatus todavía)
        if hasattr(f, "cancelacion_solicitada_en"):
            from datetime import datetime as _dt

            f.cancelacion_solicitada_en = _dt.utcnow()
        if hasattr(f, "cancelacion_code"):
            f.cancelacion_code = res.get("code")
        if hasattr(f, "cancelacion_message"):
            f.cancelacion_message = res.get("message")

        db.add(f)
        db.commit()
        db.refresh(f)

        # 6) Devolvemos el estado actual + info del PAC
        return {
            "estatus": f.estatus,  # permanece TIMBRADA de momento
            "uuid": uuid,
            "code": res.get("code"),
            "message": res.get("message"),
        }
