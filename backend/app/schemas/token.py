# app/schemas/token.py
from typing import Optional
from pydantic import BaseModel


class AccessTokenResponse(BaseModel):
    """Respuesta de login y refresh — el refresh token viaja como httpOnly cookie."""
    access_token: str
    token_type: str = "bearer"


class Token(BaseModel):
    """Uso interno: par completo de tokens (no se expone directamente en respuestas)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Mantenido para compatibilidad con scripts internos que envíen el token en body."""
    refresh_token: str
