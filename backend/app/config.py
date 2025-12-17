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
    
    # Facturación Moderna (PAC)
    FM_USER_ID: str = "BORO850708SZ7"  # Default de prueba, sobreescribir en .env para prod
    FM_USER_PASS: str = "ddf6f5be0deeac05a0c144a81cad9d5da63c7bba"             # Contraseña del PAC
    FM_TIMBRADO_URL: str = "http://t1.facturacionmoderna.com/timbrado/soap" # URL Producción por default
    # Para pruebas: http://t1.facturacionmoderna.com/timbrado/soap

    # API Prefix
    API_V1_STR: str = "/api"

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
