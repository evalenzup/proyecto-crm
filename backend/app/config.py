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
    
    # Facturación Moderna (PAC) — requeridos en .env, sin defaults en código
    FM_USER_ID: str
    FM_USER_PASS: str
    FM_TIMBRADO_URL: str = "http://t1.facturacionmoderna.com/timbrado/soap"

    # URL pública del frontend (para QR de credenciales)
    APP_URL: str = "https://app.sistemas-erp.com"

    # HERE Maps API
    HERE_API_KEY: str = ""

    # API Prefix
    API_V1_STR: str = "/api"

    # Cookie para refresh token httpOnly
    # En producción (HTTPS) debe ser True. En desarrollo local, False.
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"   # "lax" es suficiente — frontend y API son same-site
    # Domain para que la cookie sea válida en todos los subdominios.
    # En desarrollo déjalo vacío. En producción: ".sistemas-erp.com"
    COOKIE_DOMAIN: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://192.168.68.136:3000",
        "http://192.168.68.136:5173",
        "http://localhost:3001",
        "http://192.168.68.136:3001",
        "https://app.sistemas-erp.com",
        "https://api.sistemas-erp.com",
    ]

    # Configuración de Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
