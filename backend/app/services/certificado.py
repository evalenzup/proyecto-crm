import os
import shutil
from datetime import datetime
from typing import Dict
from cryptography import x509
from cryptography.hazmat.primitives.serialization import load_der_private_key
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

CERT_DIR = os.getenv("CERT_DIR", "/data/cert")

class CertificadoService:
    @staticmethod
    def guardar(upload_file, filename: str) -> str:
        """
        Guarda el upload_file en CERT_DIR/filename y devuelve la ruta absoluta.
        """
        os.makedirs(CERT_DIR, exist_ok=True)
        path = os.path.join(CERT_DIR, filename)
        with open(path, "wb") as buf:
            shutil.copyfileobj(upload_file.file, buf)
        return path

    @staticmethod
    def validar(cer_path: str, key_path: str, password: str) -> Dict:
        """
        Valida la correspondencia y vigencia entre .cer y .key.
        Acepta:
          - nombres de archivo (p.ej. "1234.cer"), o
          - rutas absolutas (/data/cert/1234.cer).
        Siempre normaliza internamente a la ruta real.
        """
        # 1) Si recibimos sólo un nombre, lo convertimos a absoluta
        if not os.path.isabs(cer_path):
            cer_path = os.path.join(CERT_DIR, os.path.basename(cer_path))
        if not os.path.isabs(key_path):
            key_path = os.path.join(CERT_DIR, os.path.basename(key_path))

        # 2) Validaciones
        try:
            cert_data = open(cer_path, "rb").read()
            cert = x509.load_der_x509_certificate(cert_data, backend=default_backend())
            if cert.not_valid_after < datetime.utcnow():
                return {"valido": False, "error": "El certificado está vencido"}

            key_data = open(key_path, "rb").read()
            private_key = load_der_private_key(key_data, password.encode("utf-8"), backend=default_backend())

            pub = cert.public_key()
            if not (isinstance(pub, rsa.RSAPublicKey) and isinstance(private_key, rsa.RSAPrivateKey)):
                return {"valido": False, "error": "Tipo de clave no compatible"}
            if pub.public_numbers() != private_key.public_key().public_numbers():
                return {"valido": False, "error": "La llave privada no corresponde"}

            return {"valido": True, "valido_hasta": cert.not_valid_after.isoformat()}

        except ValueError as e:
            msg = str(e)
            if "could not decrypt key" in msg:
                return {"valido": False, "error": "Contraseña incorrecta"}
            return {"valido": False, "error": msg}
        except Exception as e:
            print(f"Error al validar certificado: {e}")
            return {"valido": False, "error": str(e)}