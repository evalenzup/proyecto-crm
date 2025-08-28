# /app/diagnose_key.py
import os, sys
from cryptography import x509
from cryptography.hazmat.primitives.serialization import load_der_private_key, load_pem_private_key
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates

CERT_DIR = os.environ.get("CERT_DIR", "/data/certificados")

def readb(path):
    with open(path, "rb") as f:
        return f.read()

def main(emp_id, cer_name=None, key_name=None, password=None):
    cer_path = os.path.join(CERT_DIR, cer_name or f"{emp_id}.cer")
    key_path = os.path.join(CERT_DIR, key_name or f"{emp_id}.key")

    print(f"CER={cer_path}\nKEY={key_path}\nPASS={'<provista>' if password else '<vacía>'}")

    cer = readb(cer_path)
    try:
        cert = x509.load_der_x509_certificate(cer)
        print("✓ .cer = DER")
    except Exception:
        cert = x509.load_pem_x509_certificate(cer)
        print("✓ .cer = PEM")

    key = readb(key_path)
    if not password:
        print("❌ Sin contraseña: no puedo abrir la .key cifrada")
        return 2

    pwd = password.encode("utf-8")

    # DER
    try:
        load_der_private_key(key, password=pwd)
        print("✓ .key = DER (PKCS#8) — contraseña correcta")
        return 0
    except Exception as e_der:
        print(f"→ DER falló: {e_der.__class__.__name__} {e_der}")

    # PEM
    try:
        load_pem_private_key(key, password=pwd)
        print("✓ .key = PEM (PKCS#8) — contraseña correcta")
        return 0
    except Exception as e_pem:
        print(f"→ PEM falló: {e_pem.__class__.__name__} {e_pem}")

    # PKCS12
    try:
        priv, _c, _chain = load_key_and_certificates(key, pwd)
        if priv:
            print("✓ .key = PKCS#12 (.pfx/.p12) — contraseña correcta, se extrajo private key")
            return 0
    except Exception as e_p12:
        print(f"→ PKCS#12 falló: {e_p12.__class__.__name__} {e_p12}")

    print("❌ No se pudo abrir la .key con la contraseña dada (formato o password incorrectos)")
    return 3

if __name__ == "__main__":
    # Uso:
    # docker compose exec backend bash -lc "python /app/diagnose_key.py <empresa_uuid> <opcional:archivo.cer> <opcional:archivo.key> '<password>'"
    if len(sys.argv) < 3:
        print("Uso: diagnose_key.py <empresa_uuid> <password> [archivo_cer] [archivo_key]")
        sys.exit(1)
    emp_id = sys.argv[1]
    password = sys.argv[2]
    cer = sys.argv[3] if len(sys.argv) > 3 else None
    key = sys.argv[4] if len(sys.argv) > 4 else None
    sys.exit(main(emp_id, cer, key, password))