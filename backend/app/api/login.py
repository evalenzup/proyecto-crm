# app/api/login.py
import uuid as _uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.limiter import limiter
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.token import Token, RefreshTokenRequest
from app.schemas.usuario import Usuario as UsuarioSchema

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
@limiter.limit("5/minute")
def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 compatible token login, retorna access token y refresh token."""
    user = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/login/refresh-token", response_model=Token)
@limiter.limit("10/minute")
def refresh_access_token(
    request: Request,
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Renueva el access token usando un refresh token válido (rotación de tokens)."""
    user_id_str = security.verify_refresh_token(body.refresh_token)
    try:
        user_id = _uuid.UUID(user_id_str)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.get("/users/me", response_model=UsuarioSchema)
def get_current_user_me(
    current_user: Usuario = Depends(deps.get_current_active_user),
) -> Any:
    """Retorna los datos del usuario autenticado."""
    return current_user
