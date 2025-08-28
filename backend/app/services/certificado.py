import os
import shutil
import re
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple

from cryptography import x509
from cryptography.hazmat.primitives.serialization import load_der_private_key, load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import (
    NameOID,
    ExtensionOID,
    ExtendedKeyUsageOID,
    ObjectIdentifier,
)

from app.core.logger import logger
from app.config import settings

CERT_DIR = settings.CERT_DIR

OID_SERIALNUMBER = NameOID.SERIAL_NUMBER
OID_UNIQUE_ID = ObjectIdentifier("2.5.4.45")

RFC_REGEX = re.compile(r"\b([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})\b", re.IGNORECASE)
CURP_REGEX = re.compile(r"\b([A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z0-9]\d)\b", re.IGNORECASE)

def _abs(path_or_name: str) -> str:
    return path_or_name if os.path.isabs(path_or_name) else os.path.join(CERT_DIR, os.path.basename(path_or_name))

def _utc_pair(cert: x509.Certificate) -> Tuple[datetime, datetime]:
    nvb = getattr(cert, "not_valid_before_utc", None)
    nva = getattr(cert, "not_valid_after_utc", None)
    if nvb is None:
        base = cert.not_valid_before
        nvb = base if base.tzinfo else base.replace(tzinfo=timezone.utc)
    if nva is None:
        base = cert.not_valid_after
        nva = base if base.tzinfo else base.replace(tzinfo=timezone.utc)
    return nvb, nva

def _name_attr(name: x509.Name, oid: NameOID | ObjectIdentifier) -> Optional[str]:
    try:
        attrs = name.get_attributes_for_oid(oid)
        return attrs[0].value.strip() if attrs else None
    except Exception:
        return None

def _rfc_curp_from_subject(name: x509.Name) -> Dict[str, Optional[str]]:
    text = name.rfc4514_string()
    serial = _name_attr(name, OID_SERIALNUMBER) or _name_attr(name, OID_UNIQUE_ID)
    r_rfc = RFC_REGEX.search(text)
    r_curp = CURP_REGEX.search(text)
    real_rfc = r_rfc.group(1).upper() if r_rfc else (serial.upper() if serial and RFC_REGEX.fullmatch(serial.upper()) else None)
    real_curp = r_curp.group(1).upper() if r_curp else (serial.upper() if serial and CURP_REGEX.fullmatch(serial.upper()) else None)
    return {"rfc": real_rfc, "curp": real_curp}

def _key_usage(cert: x509.Certificate) -> Optional[List[str]]:
    try:
        ku = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
    except x509.ExtensionNotFound:
        return None
    out: List[str] = []
    if ku.digital_signature: out.append("digitalSignature")
    if ku.content_commitment: out.append("nonRepudiation")
    if ku.key_encipherment: out.append("keyEncipherment")
    if ku.data_encipherment: out.append("dataEncipherment")
    if ku.key_agreement: out.append("keyAgreement")
    if ku.key_cert_sign: out.append("keyCertSign")
    if ku.crl_sign: out.append("cRLSign")
    if getattr(ku, "key_agreement", False):
        try:
            if getattr(ku, "encipher_only", False):
                out.append("encipherOnly")
        except ValueError:
            pass
        try:
            if getattr(ku, "decipher_only", False):
                out.append("decipherOnly")
        except ValueError:
            pass
    return out

def _eku(cert: x509.Certificate) -> Optional[List[str]]:
    try:
        eku = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
    except x509.ExtensionNotFound:
        return None
    out: List[str] = []
    for oid in eku:
        if oid == ExtendedKeyUsageOID.CLIENT_AUTH:
            out.append("clientAuth")
        elif oid == ExtendedKeyUsageOID.SERVER_AUTH:
            out.append("serverAuth")
        elif oid == ExtendedKeyUsageOID.EMAIL_PROTECTION:
            out.append("emailProtection")
        elif oid == ExtendedKeyUsageOID.CODE_SIGNING:
            out.append("codeSigning")
        elif oid == ExtendedKeyUsageOID.TIME_STAMPING:
            out.append("timeStamping")
        else:
            out.append(oid.dotted_string)
    return out

def _tipo_cert(subject: x509.Name) -> str:
    s = subject.rfc4514_string().upper()
    if "SELLO" in s:
        return "CSD"
    if "FIEL" in s or "E.FIRMA" in s or "FIRMA ELECTR" in s:
        return "FIEL"
    return "DESCONOCIDO"

class CertificadoService:
    @staticmethod
    def guardar(upload_file, filename: str) -> str:
        os.makedirs(CERT_DIR, exist_ok=True)
        path = os.path.join(CERT_DIR, filename)
        with open(path, "wb") as buf:
            shutil.copyfileobj(upload_file.file, buf)
        logger.info("💾 Guardado archivo: %s", path)
        return path

    @staticmethod
    def extraer_info(cer_path: str) -> Dict:
        path = _abs(cer_path)
        with open(path, "rb") as f:
            cer_bytes = f.read()
        return CertificadoService.extraer_info_bytes(cer_bytes)

    @staticmethod
    def extraer_info_bytes(cer_bytes: bytes) -> Dict:
        try:
            cert = x509.load_der_x509_certificate(cer_bytes, backend=default_backend())
        except Exception:
            cert = x509.load_pem_x509_certificate(cer_bytes, backend=default_backend())
        nvb, nva = _utc_pair(cert)
        subject, issuer = cert.subject, cert.issuer
        subj_ids = _rfc_curp_from_subject(subject)

        return {
            "nombre_cn": _name_attr(subject, NameOID.COMMON_NAME),
            "rfc": subj_ids["rfc"],
            "curp": subj_ids["curp"],
            "numero_serie": format(cert.serial_number, "x").upper(),
            "valido_desde": nvb.isoformat(),
            "valido_hasta": nva.isoformat(),
            "issuer_cn": _name_attr(issuer, NameOID.COMMON_NAME),
            "key_usage": _key_usage(cert),
            "extended_key_usage": _eku(cert),
            "tipo_cert": _tipo_cert(subject),
        }

    @staticmethod
    def validar(cer_path: str, key_path: str, password: str) -> Dict:
        cer_abs = _abs(cer_path)
        key_abs = _abs(key_path)
        with open(cer_abs, "rb") as cf, open(key_abs, "rb") as kf:
            return CertificadoService.validar_bytes(cf.read(), kf.read(), password)

    @staticmethod
    def validar_bytes(cer_bytes: bytes, key_bytes: bytes, password: str) -> Dict:
        try:
            try:
                cert = x509.load_der_x509_certificate(cer_bytes, backend=default_backend())
            except Exception:
                cert = x509.load_pem_x509_certificate(cer_bytes, backend=default_backend())

            _, nva = _utc_pair(cert)
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            if nva < now:
                return {"valido": False, "valido_hasta": nva.isoformat(), "error": "El certificado está vencido"}

            # Intentar descifrar la private key con la contraseña (DER → PEM)
            try:
                private_key = load_der_private_key(key_bytes, password.encode("utf-8"), backend=default_backend())
            except ValueError as e_der:
                try:
                    private_key = load_pem_private_key(key_bytes, password.encode("utf-8"), backend=default_backend())
                except ValueError as e_pem:
                    msg = (str(e_pem) or str(e_der) or "").lower()
                    if "decrypt" in msg or "password" in msg:
                        return {"valido": False, "valido_hasta": nva.isoformat(), "error": "Contraseña incorrecta"}
                    return {"valido": False, "valido_hasta": nva.isoformat(), "error": str(e_pem) or str(e_der)}

            # Comparar llaves pública/privada
            pub = cert.public_key()
            if not isinstance(pub, rsa.RSAPublicKey):
                return {"valido": False, "valido_hasta": nva.isoformat(), "error": "Tipo de clave no compatible"}
            if pub.public_numbers() != private_key.public_key().public_numbers():
                return {"valido": False, "valido_hasta": nva.isoformat(), "error": "La llave privada no corresponde al certificado"}

            return {"valido": True, "valido_hasta": nva.isoformat(), "error": None}

        except Exception as e:
            logger.warning(f"❌ validar_bytes error: {e}")
            return {"valido": False, "valido_hasta": None, "error": str(e)}