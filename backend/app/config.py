# app/config.py
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str

    # JWT / Auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ENCRYPTION_KEY: str

    # Certificados
    CERT_DIR: str = "/data/certificados"
    DATA_DIR: str = "/data"
    CADENA40_XSLT_PATH: str = "/data/sat/cadenaoriginal_4_0.xslt"
    FM_USER_ID: str = "BORO850708SZ7"
    FM_USER_PASS: str = "ddf6f5be0deeac05a0c144a81cad9d5da63c7bba"
    FM_TIMBRADO_URL: str = "http://t1.facturacionmoderna.com/timbrado/soap"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://158.97.12.153:3000", "http://158.97.12.153:5173"]

    # Configuración de Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

settings = Settings()