# check_csd.py
from __future__ import annotations
import os
import sys
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.serialization import (
    load_der_private_key,
    load_pem_private_key,
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa


def load_cert_bytes(p: Path) -> bytes:
    b = p.read_bytes()
    try:
        return x509.load_der_x509_certificate(
            b, backend=default_backend()
        ).public_bytes(x509.Encoding.DER)
    except Exception:
        # si venía en PEM
        cer = x509.load_pem_x509_certificate(b, backend=default_backend())
        return cer.public_bytes(x509.Encoding.DER)


def main():
    cert_dir = Path(os.environ.get("CERT_DIR", "/data/certificados"))
    empresa_id = None
    if len(sys.argv) >= 2:
        empresa_id = sys.argv[1]
    else:
        print("Uso: python check_csd.py <empresa_id>")
        sys.exit(2)

    cer_path = cert_dir / f"{empresa_id}.cer"
    key_path = cert_dir / f"{empresa_id}.key"
    pwd = (
        os.environ.get("CERT_PASSPHRASE")
        or os.environ.get(f"CSD_PASS_{empresa_id}")
        or os.environ.get("CSD_PASS")
    )

    print(f"CERT_DIR={cert_dir}")
    print(f"CER={cer_path}  KEY={key_path}")
    print(
        f"PASS source={'CERT_PASSPHRASE' if os.environ.get('CERT_PASSPHRASE') else ('CSD_PASS_' + empresa_id if os.environ.get(f'CSD_PASS_{empresa_id}') else ('CSD_PASS' if os.environ.get('CSD_PASS') else '(ninguna)'))}"
    )

    if not cer_path.exists() or not key_path.exists():
        print("❌ Faltan archivos .cer o .key")
        sys.exit(1)

    # Carga .cer (DER/PEM indiferente)
    try:
        cer_bytes = cer_path.read_bytes()
        try:
            cert = x509.load_der_x509_certificate(cer_bytes, backend=default_backend())
        except Exception:
            cert = x509.load_pem_x509_certificate(cer_bytes, backend=default_backend())
        print("✓ Certificado cargado")
    except Exception as e:
        print(f"❌ Error cargando .cer: {e}")
        sys.exit(1)

    # Fechas
    nvb = getattr(cert, "not_valid_before_utc", cert.not_valid_before)
    nva = getattr(cert, "not_valid_after_utc", cert.not_valid_after)
    print(f"  Válido desde: {nvb.isoformat()}  hasta: {nva.isoformat()}")

    # Carga .key (DER/PEM, requiere password)
    key_bytes = key_path.read_bytes()
    if not pwd:
        print("❌ No se encontró contraseña en variables de entorno.")
        sys.exit(3)
    try:
        try:
            pkey = load_der_private_key(
                key_bytes, password=pwd.encode("utf-8"), backend=default_backend()
            )
        except ValueError:
            # intento PEM
            pkey = load_pem_private_key(
                key_bytes, password=pwd.encode("utf-8"), backend=default_backend()
            )
        print("✓ Llave privada descifrada con la contraseña")
    except Exception as e:
        print(f"❌ Error descifrando .key con la contraseña: {e}")
        sys.exit(4)

    # Comparar par de claves
    pub = cert.public_key()
    if not isinstance(pub, rsa.RSAPublicKey):
        print("❌ El certificado no es RSA (incompatible)")
        sys.exit(5)

    if pub.public_numbers() != pkey.public_key().public_numbers():
        print("❌ La llave privada NO corresponde al .cer (par no coincide)")
        sys.exit(6)

    print("✅ El .cer y la .key corresponden y la contraseña es correcta.")
    sys.exit(0)


if __name__ == "__main__":
    main()
