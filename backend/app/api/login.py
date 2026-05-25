# app/api/login.py
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.config import settings
from app.core import security
from app.core.limiter import limiter
from app.database import get_db
from app.models.usuario import Usuario
from app.models.refresh_token import RefreshToken
from app.schemas.token import AccessTokenResponse
from app.schemas.usuario import Usuario as UsuarioSchema
from app.services import auditoria_service as audit_svc

router = APIRouter()

_REFRESH_MAX_AGE = security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600  # segundos


def _new_token_pair(user_id: Any, db: Session) -> dict:
    """
    Genera un par (access_token, refresh_token) y persiste el JTI en la whitelist.
    Limpia automáticamente los tokens expirados del usuario para mantener la tabla limpia.
    """
    now = datetime.now(timezone.utc)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.expires_at < now,
    ).delete(synchronize_session=False)

    jti = str(_uuid.uuid4())
    expires_at = now + timedelta(days=security.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at))
    db.flush()

    return {
        "access_token": security.create_access_token(user_id),
        "refresh_token": security.create_refresh_token(user_id, jti),
        "token_type": "bearer",
    }


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Adjunta el refresh token como cookie httpOnly en la respuesta."""
    kwargs: dict = dict(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=_REFRESH_MAX_AGE,
        path="/",
    )
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(**kwargs)


def _clear_refresh_cookie(response: Response) -> None:
    """Elimina la cookie de refresh token."""
    kwargs: dict = dict(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(**kwargs)


@router.post("/login/access-token", response_model=AccessTokenResponse)
@limiter.limit("5/minute")
def login_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 token login. Devuelve access_token en body y refresh_token como httpOnly cookie."""
    user = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    try:
        audit_svc.registrar(
            db=db, accion=audit_svc.LOGIN, entidad="usuario",
            usuario_id=user.id, usuario_email=user.email,
            empresa_id=user.empresa_id, entidad_id=str(user.id),
        )
    except Exception:
        pass

    tokens = _new_token_pair(user.id, db)
    db.commit()

    _set_refresh_cookie(response, tokens["refresh_token"])
    return AccessTokenResponse(access_token=tokens["access_token"])


@router.post("/login/refresh-token", response_model=AccessTokenResponse)
@limiter.limit("10/minute")
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(default=None),
) -> Any:
    """
    Renueva el access token usando el refresh token de la cookie httpOnly.
    Implementa rotación + whitelist: el token usado se invalida y se emite uno nuevo.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado",
        )

    payload = security.verify_refresh_token(refresh_token)
    jti = payload["jti"]
    user_id_str = payload["sub"]

    try:
        user_id = _uuid.UUID(user_id_str)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    stored = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revocado o no reconocido",
        )

    user = db.query(Usuario).filter(
        Usuario.id == user_id, Usuario.is_active == True
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    db.delete(stored)
    tokens = _new_token_pair(user.id, db)
    db.commit()

    _set_refresh_cookie(response, tokens["refresh_token"])
    return AccessTokenResponse(access_token=tokens["access_token"])


@router.post("/login/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    refresh_token: Optional[str] = Cookie(default=None),
) -> None:
    """
    Cierra la sesión invalidando el refresh token de la cookie httpOnly.
    Si el token ya no existe en la BD (expirado o doble-logout), se ignora silenciosamente.
    """
    if refresh_token:
        try:
            payload = security.verify_refresh_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                db.query(RefreshToken).filter(
                    RefreshToken.jti == jti,
                    RefreshToken.user_id == current_user.id,
                ).delete(synchronize_session=False)
                db.commit()
        except HTTPException:
            pass

    _clear_refresh_cookie(response)


@router.get("/users/me", response_model=UsuarioSchema)
def get_current_user_me(
    current_user: Usuario = Depends(deps.get_current_active_user),
) -> Any:
    """Retorna los datos del usuario autenticado."""
    return current_user
