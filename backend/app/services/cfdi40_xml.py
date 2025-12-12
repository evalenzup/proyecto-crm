# app/services/cfdi40_xml.py
from __future__ import annotations

import os
import re
import base64
from typing import Optional, List, Tuple, Dict
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle

# ─────────────────────────────────────────────────────────────────────────────
# crypto / xslt
# ─────────────────────────────────────────────────────────────────────────────
try:
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        load_der_private_key,
        load_pem_private_key,
        pkcs12,
    )
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.x509.oid import ExtensionOID

    _CRYPTO_OK = True
except Exception:
    _CRYPTO_OK = False

# libxslt (XSLT 1.0)
try:
    from lxml import etree as LET

    _LXML_OK = True
except Exception:
    _LXML_OK = False

# Saxon/C (XSLT 2.0/3.0)
try:
    import saxonche

    _SAXON_OK = True
except Exception:
    _SAXON_OK = False

try:
    from app.core.logger import logger
except Exception:
    logger = None

# ─────────────────────────────────────────────────────────────────────────────
# Decimales
# ─────────────────────────────────────────────────────────────────────────────
getcontext().prec = 28


def D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def money2(v) -> str:
    return f"{D(v).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def qty_any(v, max_dec=6) -> str:
    q = Decimal("1").scaleb(-max_dec)
    return f"{D(v).quantize(q, rounding=ROUND_HALF_UP)}"


def tasa6(v) -> str:
    return qty_any(v, 6)


def pad2(code: Optional[str | int]) -> Optional[str]:
    if code is None:
        return None
    s = str(code).strip()
    if s.isdigit() and len(s) == 1:
        return f"0{s}"
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Zona horaria (America/Tijuana)
# ─────────────────────────────────────────────────────────────────────────────
TIJUANA_TZ = ZoneInfo("America/Tijuana")


def _fmt_cfdi_fecha_local(dt: Optional[datetime]) -> str:
    """
    Devuelve la fecha/hora local (America/Tijuana) en formato CFDI, con salvaguarda para no
    quedar en el futuro respecto al reloj del servidor (evita error del PAC por expedición > certificación).
    Reglas:
      - Si dt es None → usar ahora (Tijuana).
      - Si dt es naive → asumir que ya está en hora local (Tijuana) y asignar tz.
      - Si dt es aware → convertir a Tijuana.
      - Aplicar skew de seguridad: si dt_local > now_local - 120s, recortar a now_local - 120s.
    """
    now_local = datetime.now(TIJUANA_TZ)
    if dt is None:
        dt_local = now_local
    else:
        if dt.tzinfo is None:
            # interpretar como hora local ya (evita suposiciones de UTC)
            dt_local = dt.replace(tzinfo=TIJUANA_TZ)
        else:
            dt_local = dt.astimezone(TIJUANA_TZ)

    # Skew de seguridad (2 minutos)
    max_allowed = now_local - timedelta(seconds=120)
    if dt_local > max_allowed:
        if logger:
            logger.info(
                f"Ajuste Fecha CFDI (clamp): {dt_local.isoformat()} -> {max_allowed.isoformat()}"
            )
        dt_local = max_allowed

    return dt_local.strftime("%Y-%m-%dT%H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ─────────────────────────────────────────────────────────────────────────────
def _load_factura_full(db: Session, factura_id: UUID) -> Optional[Factura]:
    return (
        db.query(Factura)
        .options(
            selectinload(Factura.empresa),
            selectinload(Factura.cliente),
            selectinload(Factura.conceptos),
        )
        .filter(Factura.id == factura_id)
        .first()
    )


def _decode_no_certificado(cert: "x509.Certificate") -> Optional[str]:
    try:
        serial_hex = f"{cert.serial_number:x}"
        if len(serial_hex) % 2:
            serial_hex = "0" + serial_hex
        ascii_bytes = bytes.fromhex(serial_hex)
        ascii_str = ascii_bytes.decode("ascii", errors="ignore")
        ascii_str = "".join(ch for ch in ascii_str if ch.isdigit())
        if len(ascii_str) >= 20:
            return ascii_str[:20]
        if 0 < len(ascii_str) < 20:
            return ascii_str.zfill(20)
    except Exception:
        pass
    try:
        dec = str(cert.serial_number)
        if len(dec) >= 20:
            return dec[:20]
        return dec.zfill(20)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Contraseña desde DB (texto plano)
# ─────────────────────────────────────────────────────────────────────────────
def _get_empresa_csd_password(empresa) -> Optional[str]:
    raw = getattr(empresa, "contrasena", None)
    if raw is None:
        return None
    s = str(raw)
    s = s.replace("\ufeff", "").strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1]
    s = s.strip()
    return s or None


def _load_csd_cert_for_empresa(
    empresa,
) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
    try:
        cer_path = os.path.join(settings.CERT_DIR, f"{empresa.id}.cer")
        if not os.path.exists(cer_path):
            return None, None, None
        data = open(cer_path, "rb").read()

        if not _CRYPTO_OK:
            try:
                return None, base64.b64encode(data).decode("ascii"), data
            except Exception:
                return None, None, None

        try:
            cert = x509.load_der_x509_certificate(data)
        except Exception:
            cert = x509.load_pem_x509_certificate(data)

        no_cert = _decode_no_certificado(cert)
        cert_der = cert.public_bytes(Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode("ascii")
        return no_cert, cert_b64, cert_der
    except Exception:
        return None, None, None


def _load_csd_key_for_empresa(empresa):
    if not _CRYPTO_OK:
        return None

    key_path = os.path.join(settings.CERT_DIR, f"{empresa.id}.key")
    if not os.path.exists(key_path):
        if logger:
            logger.info(f"[CSD] No existe KEY: {key_path}")
        else:
            print(f"[CSD] No existe KEY: {key_path}")
        return None

    pwd = _get_empresa_csd_password(empresa)
    if not pwd:
        if logger:
            logger.warning("[CSD] Password DB vacía/nula")
        else:
            print("[CSD] Password DB vacía/nula")
        return None
    pwd_bytes = pwd.encode("utf-8")
    key_bytes = open(key_path, "rb").read()

    # DER PKCS#8
    try:
        return load_der_private_key(key_bytes, password=pwd_bytes)
    except Exception as e:
        print(f"[CSD] Falló DER: {e}")

    # PEM PKCS#8
    try:
        return load_pem_private_key(key_bytes, password=pwd_bytes)
    except Exception as e:
        print(f"[CSD] Falló PEM: {e}")

    # PKCS#12 fallback
    try:
        key, cert, _ = pkcs12.load_key_and_certificates(key_bytes, pwd_bytes)
        if key:
            return key
    except Exception as e:
        print(f"[CSD] Falló PKCS#12: {e}")

    if logger:
        logger.warning("[CSD] No se pudo abrir KEY (DER/PEM/P12).")
    else:
        print("[CSD] No se pudo abrir KEY (DER/PEM/P12).")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# XSLT helpers
# ─────────────────────────────────────────────────────────────────────────────
def _find_xslt_cadena40_path() -> Optional[str]:
    candidates = []
    p = getattr(settings, "CADENA40_XSLT_PATH", None)
    if p:
        candidates.append(p)
    base = getattr(settings, "DATA_DIR", "/data")
    candidates.append(os.path.join(base, "sat", "cadenaoriginal_4_0.xslt"))
    candidates.append(
        os.path.join(base, "sat", "cadenaoriginal_4_0", "cadenaoriginal_4_0.xslt")
    )

    if logger:
        logger.info("Buscando XSLT en settings/candidates:")
    else:
        print("Buscando XSLT en settings/candidates:")
    for c in candidates:
        try:
            exists = os.path.exists(c)
            info = ""
            if exists:
                st = os.stat(c)
                info = f"(size={st.st_size} bytes, mode={oct(st.st_mode)})"
            (logger.info if logger else print)(
                f"  - {c} -> {'OK' if exists else 'NO'} {info}"
            )
        except Exception as e:
            (logger.info if logger else print)(f"  - {c} -> error al verificar: {e}")
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _xslt_version(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            head = f.read(2048).decode("utf-8", "ignore")
        m = re.search(r'<xsl:stylesheet[^>]*\bversion\s*=\s*"[^\"]+"', head)
        if m:
            v = re.search(r'version\s*=\s*"([^"]+)"', m.group(0))
            return v.group(1) if v else None
    except Exception:
        pass
    try:
        if _LXML_OK:
            root = LET.parse(path).getroot()
            return root.get("version")
    except Exception:
        pass
    return None


class SATResolver(LET.Resolver):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def resolve(self, url, pubid, context):
        if url and url.startswith("http://www.sat.gob.mx/"):
            local_rel = url.replace("http://www.sat.gob.mx/", "")
            local_path = os.path.join(self.base_dir, local_rel)
            if os.path.exists(local_path):
                print(f"[SATResolver] Resuelto {url} -> {local_path}")
                return self.resolve_filename(local_path, context)
            print(f"[SATResolver] No encontrado local: {local_path} (para {url})")
        return None


def _rewrite_xslt_urls_to_local(xslt_path: str, sat_base_dir: str) -> str:
    with open(xslt_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    def repl(match):
        url = match.group(1)
        if url.startswith("http://www.sat.gob.mx/"):
            rel = url.replace("http://www.sat.gob.mx/", "")
            local = os.path.join(sat_base_dir, rel)
            local_url = "file://" + local
            print(f"[SaxonURL] {url} -> {local_url}")
            return f'href="{local_url}"'
        return match.group(0)

    text2 = re.sub(r'href\s*=\s*"([^"]+)"', repl, text)
    tmp_path = xslt_path + ".local.saxon.xslt"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text2)
    return tmp_path


def _apply_xslt10_with_lxml(xml_bytes: bytes, xslt_path: str) -> Optional[str]:
    base_sat_dir = os.path.join(getattr(settings, "DATA_DIR", "/data"), "sat")
    parser = LET.XMLParser()
    parser.resolvers.add(SATResolver(base_sat_dir))
    try:
        xslt_doc = LET.parse(xslt_path, parser)
        transform = LET.XSLT(xslt_doc)
        result = transform(LET.fromstring(xml_bytes))
        return str(result).strip()
    except Exception as e:
        head = b""
        try:
            with open(xslt_path, "rb") as f:
                head = f.read(200)
        except Exception:
            pass
        (logger.error if logger else print)(f"Error XSLT 1.0: {e}. Head: {head!r}")
        return None


def _apply_xslt20_with_saxon(xml_bytes: bytes, xslt_path: str) -> Optional[str]:
    if not _SAXON_OK:
        (logger.error if logger else print)("saxonche no está instalado (XSLT 2.0).")
        return None
    base_sat_dir = os.path.join(getattr(settings, "DATA_DIR", "/data"), "sat")
    xslt_local = _rewrite_xslt_urls_to_local(xslt_path, base_sat_dir)
    try:
        with saxonche.PySaxonProcessor(license=False) as proc:
            xsltproc = proc.new_xslt30_processor()
            xsltproc.set_cwd(base_sat_dir)
            executable = xsltproc.compile_stylesheet(stylesheet_file=xslt_local)
            doc = proc.parse_xml(xml_text=xml_bytes.decode("utf-8"))
            result = executable.transform_to_string(xdm_node=doc)
            return (result or "").strip()
    except Exception as e:
        (logger.error if logger else print)(f"Error XSLT 2.0 Saxon/C: {e}")
        return None
    finally:
        try:
            os.remove(xslt_local)
        except Exception:
            pass


def _build_cadena_original_40(xml_bytes: bytes) -> Optional[str]:
    xslt_path = _find_xslt_cadena40_path()
    if not xslt_path:
        (logger.error if logger else print)(
            "No se encontró el XSLT de cadena original."
        )
        return None
    ver = _xslt_version(xslt_path) or "1.0"
    (logger.info if logger else print)(f"Usando XSLT: {xslt_path} (version={ver})")
    if ver.startswith("2"):
        return _apply_xslt20_with_saxon(xml_bytes, xslt_path)
    else:
        if not _LXML_OK:
            (logger.error if logger else print)("lxml no está disponible.")
            return None
        return _apply_xslt10_with_lxml(xml_bytes, xslt_path)


# ─────────────────────────────────────────────────────────────────────────────
# Firma
# ─────────────────────────────────────────────────────────────────────────────
def _sign_cadena_sha256_pkcs1v15(cadena: str, private_key) -> Optional[str]:
    if not (_CRYPTO_OK and private_key and cadena):
        return None
    try:
        sig = private_key.sign(
            cadena.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(sig).decode("ascii")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de pago (sin defaults)
# ─────────────────────────────────────────────────────────────────────────────
def _clean_str_opt(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _read_pago_attrs_from_factura(
    f: Factura,
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Lee tipo_comprobante, metodo_pago, forma_pago del modelo tal cual están en BD.
    - tipo: upper (default lógico sólo interno 'I' para construir), pero NO se usa para defaults de pago.
    - metodo_pago: upper o None
    - forma_pago: string sin espacios o None (no se rellena)
    """
    tipo = (_clean_str_opt(getattr(f, "tipo_comprobante", None)) or "I").upper()
    metodo = _clean_str_opt(getattr(f, "metodo_pago", None))
    metodo = metodo.upper() if metodo else None
    forma = _clean_str_opt(getattr(f, "forma_pago", None))
    # Log de depuración
    msg = f"[Pago attrs DB] tipo={tipo!r} metodo={metodo!r} forma={forma!r}"
    (logger.info if logger else print)(msg)
    return tipo, metodo, forma


def _apply_attrs_pago_cfdi40_strict(
    attrs: dict, *, tipo: str, metodo_pago: Optional[str], forma_pago: Optional[str]
):
    """
    Reglas sin defaults:
      - I/E:
        * MetodoPago OBLIGATORIO. Si falta → error.
        * Si MetodoPago == 'PPD' → FormaPago debe OMITIRSE.
        * Si MetodoPago != 'PPD' → FormaPago OBLIGATORIA. Si falta → error.
      - P/T/N:
        * No incluir MetodoPago/FormaPago.
    """
    t = (tipo or "").upper()
    mp = (metodo_pago or "").upper() or None
    fp = (forma_pago or "").strip() or None

    # Tipos que no llevan estos atributos
    if t in {"P", "T", "N"}:
        attrs.pop("MetodoPago", None)
        attrs.pop("FormaPago", None)
        return

    if t in {"I", "E"}:
        if not mp:
            raise RuntimeError(
                "MetodoPago es requerido para TipoDeComprobante I/E y viene vacío en la factura (BD)."
            )
        attrs["MetodoPago"] = mp

        if mp == "PPD":
            attrs.pop("FormaPago", None)  # no va
        else:
            if not fp:
                raise RuntimeError(
                    "FormaPago es requerida cuando MetodoPago != 'PPD' (I/E) y viene vacía en la factura (BD)."
                )
            attrs["FormaPago"] = pad2(fp)
        return

    # Cualquier otro: limpia por seguridad
    attrs.pop("MetodoPago", None)
    attrs.pop("FormaPago", None)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de modelo → CFDI
# ─────────────────────────────────────────────────────────────────────────────
def _is_global_invoice(f: Factura) -> bool:
    cli = getattr(f, "cliente", None)
    rfc = (getattr(cli, "rfc", None) or "").upper()
    uso = (getattr(f, "uso_cfdi", None) or "").upper()
    return rfc == "XAXX010101000" or uso == "S01"


def _receptor_nombre(cli) -> str:
    return (
        getattr(cli, "nombre_razon_social", None)
        or getattr(cli, "nombre_comercial", None)
        or getattr(cli, "nombre", None)
        or "PUBLICO EN GENERAL"
    )


def _calc_totales_desde_conceptos(
    conceptos: List[FacturaDetalle],
) -> Dict[str, Decimal]:
    subtotal = Decimal("0")
    descuento = Decimal("0")
    base_gravada = Decimal("0")
    for c in conceptos:
        cantidad = D(getattr(c, "cantidad", 0) or 0)
        vunit = D(getattr(c, "valor_unitario", 0) or 0)
        imp_sin_iva = cantidad * vunit
        dsc = D(getattr(c, "descuento", 0) or 0)
        subtotal += imp_sin_iva
        descuento += dsc
        base_gravada += imp_sin_iva - dsc
    return dict(subtotal=subtotal, descuento=descuento, base_gravada=base_gravada)


def _group_traslados_por_tasa(
    bases_e_tasas: List[Tuple[Decimal, Decimal]],
) -> Tuple[Decimal, List[Tuple[str, str, str, Decimal, Decimal]]]:
    grupos: Dict[str, Dict[str, Decimal]] = {}
    total = Decimal("0")
    for base, tasa in bases_e_tasas:
        if base <= 0 or tasa <= 0:
            continue
        imp = (base * tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += imp
        key = tasa6(tasa)
        if key not in grupos:
            grupos[key] = {"base": Decimal("0"), "importe": Decimal("0")}
        grupos[key]["base"] += base
        grupos[key]["importe"] += imp
    filas: List[Tuple[str, str, str, Decimal, Decimal]] = []
    for key, acc in grupos.items():
        filas.append(("002", "Tasa", key, acc["base"], acc["importe"]))
    return total, filas


def _tipo_cert(subject: "x509.Name", cert_obj: "x509.Certificate | None" = None) -> str:
    try:
        s = subject.rfc4514_string().upper()
    except Exception:
        # Si falla el parsing estricto del subject, intentamos usar str() o string vacío
        # Esto permite que el código continúe y cheque EKU abajo.
        try:
            s = str(subject).upper()
        except Exception:
            s = ""

    if "FIEL" in s or "E.FIRMA" in s or "FIRMA ELECTR" in s:
        return "FIEL"
    if "SELLO" in s:
        return "CSD"
    try:
        if cert_obj is not None:
            eku = cert_obj.extensions.get_extension_for_oid(
                ExtensionOID.EXTENDED_KEY_USAGE
            ).value
            eku_oids = {oid.dotted_string for oid in eku}
            if eku_oids:
                # Si tiene EKU, por defecto asumimos CSD si no se detectó FIEL explícitamente antes
                # (Las FIEL suelen tener 'secureEmail' etc, pero los CSD tienen OIDs específicos de SAT a veces, 
                #  o simplemente el hecho de tener EKU suele diferenciarlo de algunos certs legacy, 
                #  pero lo importante es que si llegamos aquí, no es FIEL por nombre).
                return "CSD"
    except Exception:
        pass
    return "DESCONOCIDO"


# ─────────────────────────────────────────────────────────────────────────────
# Builder principal
# ─────────────────────────────────────────────────────────────────────────────
def build_cfdi40_xml_sin_timbrar(db: Session, factura_id: UUID) -> bytes:
    f = _load_factura_full(db, factura_id)
    if not f:
        raise ValueError("Factura no encontrada")

    emp = f.empresa
    cli = f.cliente
    conceptos: List[FacturaDetalle] = list(f.conceptos or [])

    NS_CFDI = "http://www.sat.gob.mx/cfd/4"
    NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
    register_namespace("cfdi", NS_CFDI)
    register_namespace("xsi", NS_XSI)

    # Totales
    calc = _calc_totales_desde_conceptos(conceptos)
    subtotal = D(getattr(f, "subtotal", None) or calc["subtotal"])
    descuento = D(getattr(f, "descuento", None) or calc["descuento"])
    traslados = D(getattr(f, "impuestos_trasladados", None) or 0)
    retenidos = D(getattr(f, "impuestos_retenidos", None) or 0)
    
    
    total = D(
        getattr(f, "total", None) or (subtotal - descuento + traslados - retenidos)
    )

    schema_loc = "http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"
    # Construimos sin FormaPago/MetodoPago aquí (se aplican estrictamente abajo)
    compro_attrs = {
        "Version": "4.0",
        **({"Serie": str(f.serie)} if getattr(f, "serie", None) else {}),
        **({"Folio": str(f.folio)} if getattr(f, "folio", None) else {}),
        "Fecha": _fmt_cfdi_fecha_local(getattr(f, "fecha_emision", None)),
        "SubTotal": money2(subtotal),
        **({"Descuento": money2(descuento)} if descuento > 0 else {}),
        "Moneda": getattr(f, "moneda", None) or "MXN",
        **(
            {"TipoCambio": qty_any(f.tipo_cambio, 6)}
            if getattr(f, "tipo_cambio", None)
            else {}
        ),
        "Total": money2(total),
        "TipoDeComprobante": (getattr(f, "tipo_comprobante", None) or "I").upper(),
        "Exportacion": getattr(f, "exportacion", None) or "01",
        "LugarExpedicion": (
            getattr(f, "lugar_expedicion", None)
            or (getattr(emp, "codigo_postal", None) or "")
        )[:5],
        f"{{{NS_XSI}}}schemaLocation": schema_loc,
    }

    # Aplicar reglas de pago STRICT (sin defaults, usando valores BD)
    tipo_db, mp_db, fp_db = _read_pago_attrs_from_factura(f)
    _apply_attrs_pago_cfdi40_strict(
        compro_attrs, tipo=tipo_db, metodo_pago=mp_db, forma_pago=fp_db
    )

    compro = Element(f"{{{NS_CFDI}}}Comprobante", compro_attrs)

    # Certificado / NoCertificado
    no_cert, cert_b64, cert_der = _load_csd_cert_for_empresa(emp)
    if no_cert:
        compro.set("NoCertificado", no_cert)
    if cert_b64:
        compro.set("Certificado", cert_b64)

    if _CRYPTO_OK and cert_der:
        cert_obj = x509.load_der_x509_certificate(cert_der)
        try:
            tipo = _tipo_cert(cert_obj.subject, cert_obj)
        except Exception as e:
            # Si falla el acceso a .subject (ValueError ASN1), intentamos inferir por EKU si es posible
            # sin acceder a subject, o asumimos CSD si tenemos key_usage adecuado.
            # Como _tipo_cert intenta leer subject, aquí hacemos un fallback manual.
            (logger.warning if logger else print)(f"Error leyendo subject del certificado: {e}")
            tipo = "DESCONOCIDO"
            try:
                eku = cert_obj.extensions.get_extension_for_oid(
                    ExtensionOID.EXTENDED_KEY_USAGE
                ).value
                if eku:
                    tipo = "CSD"
            except Exception:
                pass
            # Si seguimos sin saber, y no pudimos leer subject para ver si es FIEL, 
            # asumimos CSD (riesgoso pero permite timbrar si es valido para el PAC)
            if tipo == "DESCONOCIDO":
                 tipo = "CSD"
        try:
            subj = cert_obj.subject.rfc4514_string()
        except Exception:
            subj = "ERROR_PARSING_SUBJECT"

        (logger.info if logger else print)(
            f"[CSD check] subject={subj} tipo_inferido={tipo}"
        )
        if tipo == "FIEL":
            raise RuntimeError(
                "Se detectó un certificado de FIEL/e.firma. Debes usar el CSD."
            )

    # InformacionGlobal (requerido por SAT cuando receptor es PÚBLICO EN GENERAL / XAXX...)
    if _is_global_invoice(f):
        per = getattr(f, "global_periodicidad", None)
        mes = getattr(f, "global_meses", None)
        anio = getattr(f, "global_anio", None)
        if not (per and mes and anio):
            # Fallback automático: mensual del mes/año de la fecha de emisión local
            # Periodicidad: '04' (Mensual). Meses: 'MM'. Año: 'YYYY'.
            try:
                dt = getattr(f, "fecha_emision", None)
                if dt is None:
                    from datetime import datetime as _dt

                    dt_local = _dt.now(TIJUANA_TZ)
                else:
                    dt_local = (
                        dt.replace(tzinfo=TIJUANA_TZ)
                        if dt.tzinfo is None
                        else dt.astimezone(TIJUANA_TZ)
                    )
                per = "04"  # Mensual
                mes = f"{dt_local.month:02d}"
                anio = str(dt_local.year)
                if logger:
                    logger.info(
                        f"[InformacionGlobal fallback] Periodicidad={per} Meses={mes} Año={anio}"
                    )
            except Exception as _e:
                if logger:
                    logger.warning(f"No se pudo inferir InformacionGlobal: {_e}")
                per = mes = anio = None
        if per and mes and anio:
            SubElement(
                compro,
                f"{{{NS_CFDI}}}InformacionGlobal",
                {"Periodicidad": str(per), "Meses": str(mes), "Año": str(anio)},
            )

    # CfdiRelacionados
    if getattr(f, "cfdi_relacionados_tipo", None) and getattr(
        f, "cfdi_relacionados", None
    ):
        rel = SubElement(
            compro,
            f"{{{NS_CFDI}}}CfdiRelacionados",
            {"TipoRelacion": f.cfdi_relacionados_tipo},
        )
        for uuid in str(f.cfdi_relacionados).split(","):
            uuid = uuid.strip()
            if uuid:
                SubElement(rel, f"{{{NS_CFDI}}}CfdiRelacionado", {"UUID": uuid})

    # Emisor
    SubElement(
        compro,
        f"{{{NS_CFDI}}}Emisor",
        {
            "Rfc": getattr(emp, "rfc", "") or "",
            **(
                {"Nombre": getattr(emp, "nombre", None)}
                if getattr(emp, "nombre", None)
                else {}
            ),
            "RegimenFiscal": getattr(emp, "regimen_fiscal", "") or "",
        },
    )

    # Receptor
    if _is_global_invoice(f):
        receptor_attrs = {
            "Rfc": "XAXX010101000",
            "Nombre": "PUBLICO EN GENERAL",
            "DomicilioFiscalReceptor": (
                getattr(f, "lugar_expedicion", None)
                or (getattr(emp, "codigo_postal", None) or "")
            )[:5],
            "RegimenFiscalReceptor": "616",
            "UsoCFDI": "S01",
        }
    else:
        cli_nombre = (
            getattr(cli, "nombre_razon_social", None)
            or getattr(cli, "nombre_comercial", None)
            or getattr(cli, "nombre", None)
            or ""
        )
        receptor_attrs = {
            "Rfc": getattr(cli, "rfc", "") or "",
            **({"Nombre": cli_nombre} if cli_nombre else {}),
            "DomicilioFiscalReceptor": (
                getattr(cli, "codigo_postal", None)
                or (getattr(f, "lugar_expedicion", None) or "")
            )[:5],
            "RegimenFiscalReceptor": getattr(cli, "regimen_fiscal", None) or "",
            "UsoCFDI": getattr(f, "uso_cfdi", None) or "G01",
        }
    SubElement(compro, f"{{{NS_CFDI}}}Receptor", receptor_attrs)

    # Conceptos
    conceptos_node = SubElement(compro, f"{{{NS_CFDI}}}Conceptos")
    bases_para_resumen: List[Tuple[Decimal, Decimal]] = []
    for cpt in conceptos:
        cantidad = D(getattr(cpt, "cantidad", 0) or 0)
        vunit = D(getattr(cpt, "valor_unitario", 0) or 0)
        imp = cantidad * vunit
        dsc = D(getattr(cpt, "descuento", 0) or 0)
        base = imp - dsc
        objeto = (
            "02"
            if (base > 0 and getattr(cpt, "iva_tasa", None) not in (None, Decimal("0")))
            else "01"
        )
        c_attrs = {
            "ClaveProdServ": getattr(cpt, "clave_producto", None) or "01010101",
            **(
                {"NoIdentificacion": str(getattr(cpt, "no_identificacion"))}
                if getattr(cpt, "no_identificacion", None)
                else {}
            ),
            "Cantidad": qty_any(cantidad, 6),
            "ClaveUnidad": getattr(cpt, "clave_unidad", None) or "ACT",
            "Descripcion": getattr(cpt, "descripcion", None) or "Venta",
            "ValorUnitario": qty_any(vunit, 6),
            "Importe": qty_any(imp, 6),
            **({"Descuento": qty_any(dsc, 6)} if dsc > 0 else {}),
            "ObjetoImp": objeto,
        }
        concepto = SubElement(conceptos_node, f"{{{NS_CFDI}}}Concepto", c_attrs)

        if objeto == "02" and base > 0:
            impuestos_c = SubElement(concepto, f"{{{NS_CFDI}}}Impuestos")
            traslados_c = SubElement(impuestos_c, f"{{{NS_CFDI}}}Traslados")
            tasa_usada = getattr(cpt, "iva_tasa", None) or Decimal("0.160000")
            SubElement(
                traslados_c,
                f"{{{NS_CFDI}}}Traslado",
                {
                    "Base": qty_any(base, 6),
                    "Impuesto": "002",
                    "TipoFactor": "Tasa",
                    "TasaOCuota": tasa6(tasa_usada),
                    "Importe": qty_any(
                        (base * tasa_usada).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        ),
                        6,
                    ),
                },
            )
            bases_para_resumen.append((base, tasa_usada))

    # Impuestos resumen
    total_tras, filas = _group_traslados_por_tasa(bases_para_resumen)
    if total_tras > 0:
        impuestos_node = SubElement(
            compro,
            f"{{{NS_CFDI}}}Impuestos",
            {
                "TotalImpuestosTrasladados": money2(total_tras),
            },
        )
        traslados_res = SubElement(impuestos_node, f"{{{NS_CFDI}}}Traslados")
        for imp_clave, tipo_factor, tasa, base_sum, imp_sum in filas:
            SubElement(
                traslados_res,
                f"{{{NS_CFDI}}}Traslado",
                {
                    "Base": money2(base_sum),
                    "Impuesto": imp_clave,
                    "TipoFactor": tipo_factor,
                    "TasaOCuota": tasa,
                    "Importe": money2(imp_sum),
                },
            )

    # ── Cadena Original y Firma ──────────────────────────────────────────────
    xml_tmp = tostring(compro, encoding="UTF-8", xml_declaration=False)
    print("Intentando generar Cadena Original 4.0…")
    cadena = _build_cadena_original_40(xml_tmp)
    if not cadena:
        raise RuntimeError(
            "No se pudo generar la Cadena Original 4.0. Revisa los logs anteriores (ruta, versión XSLT y resolver)."
        )

    private_key = _load_csd_key_for_empresa(emp)
    if not private_key:
        raise RuntimeError(
            "No se pudo cargar la llave privada del CSD (verifica .key y contraseña en DB)."
        )

    sello_b64 = _sign_cadena_sha256_pkcs1v15(cadena, private_key)
    if not sello_b64:
        raise RuntimeError("No se pudo firmar la cadena original (sello vacío).")
    print(f"Sello generado (len={len(sello_b64)}).")

    compro.set("Sello", sello_b64)

    xml_final = tostring(compro, encoding="UTF-8", xml_declaration=True)
    print(f"XML CFDI listo (bytes={len(xml_final)}).")
    return xml_final


def render_cfdi40_xml_bytes_from_model(db, factura_id, **_):
    return build_cfdi40_xml_sin_timbrar(db, factura_id)
