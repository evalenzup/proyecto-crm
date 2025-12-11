from cryptography.fernet import Fernet
from app.config import settings
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
import bcrypt

# pwd_context eliminado


ALGORITHM = "HS256"
# En entorno real, esto debería estar en config.py
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 8 # 8 dias

# Genera una clave si no existe y la guarda, o carga la existente.
# En un entorno real, la clave DEBE ser gestionada de forma segura (ej. Vault, AWS KMS).
# Por simplicidad aquí, la leemos de la configuración.
SECRET_KEY_ENCRYPTION = settings.ENCRYPTION_KEY.encode()
if not SECRET_KEY_ENCRYPTION:
    raise ValueError("La clave de encriptación (ENCRYPTION_KEY) no está configurada.")

# Usamos una secret key distinta para JWT si es posible, si no, usamos la misma pero decodificada si es string
SECRET_KEY_JWT = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "SUPER_SECRET_KEY_CHANGE_ME"

fernet = Fernet(SECRET_KEY_ENCRYPTION)


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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt requiere bytes
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY_JWT, algorithm=ALGORITHM)
    return encoded_jwt
