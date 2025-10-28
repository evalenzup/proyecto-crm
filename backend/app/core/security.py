from cryptography.fernet import Fernet
from app.config import settings

# Genera una clave si no existe y la guarda, o carga la existente.
# En un entorno real, la clave DEBE ser gestionada de forma segura (ej. Vault, AWS KMS).
# Por simplicidad aquí, la leemos de la configuración.
SECRET_KEY = settings.ENCRYPTION_KEY.encode()
if not SECRET_KEY:
    raise ValueError("La clave de encriptación (ENCRYPTION_KEY) no está configurada.")

fernet = Fernet(SECRET_KEY)


def encrypt_data(data: str) -> str:
    """Cifra una cadena de texto y la devuelve como una cadena."""
    if not data:
        return data
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_data(encrypted_data: str) -> str:
    """Descifra una cadena de texto."""
    if not encrypted_data:
        return encrypted_data
    decrypted_data = fernet.decrypt(encrypted_data.encode())
    return decrypted_data.decode()
