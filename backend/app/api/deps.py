# app/api/deps.py
import uuid as _uuid
from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import security
from app.database import get_db
from app.models.usuario import Usuario, RolUsuario, UsuarioEmpresa
from app.schemas.token import TokenPayload
from app.config import settings

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db_session() -> Generator:
    try:
        db = get_db()
        yield next(db)
    except Exception:
        pass


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> Usuario:
    try:
        payload = jwt.decode(
            token, security.SECRET_KEY_JWT, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    try:
        user_id = _uuid.UUID(str(token_data.sub))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Could not validate credentials")
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ── Helpers de jerarquía ───────────────────────────────────────────────────────

_ADMIN_AND_ABOVE = {RolUsuario.SUPERADMIN, RolUsuario.ADMIN}
_PRIVILEGED = {RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.SUPERVISOR}


def require_superadmin(
    current_user: Usuario = Depends(get_current_active_user),
) -> Usuario:
    if current_user.rol != RolUsuario.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Se requiere rol SUPERADMIN")
    return current_user


def require_admin_or_above(
    current_user: Usuario = Depends(get_current_active_user),
) -> Usuario:
    if current_user.rol not in _ADMIN_AND_ABOVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Se requiere rol ADMIN o superior")
    return current_user


def get_empresa_ids_accesibles(
    current_user: Usuario,
    db: Session,
) -> Optional[List[_uuid.UUID]]:
    """
    Devuelve la lista de empresa_ids a los que tiene acceso el usuario.
    - SUPERADMIN / ADMIN: lista desde usuario_empresas (puede ser vacía si no tiene asignadas aún)
    - SUPERVISOR / ESTANDAR / OPERATIVO: [empresa_id] directo
    Retorna None solo si es SUPERADMIN sin restricción (acceso total).
    """
    if current_user.rol == RolUsuario.SUPERADMIN:
        # SUPERADMIN tiene acceso a todo: retorna None → sin filtro
        return None
    if current_user.rol == RolUsuario.ADMIN:
        rows = (
            db.query(UsuarioEmpresa.empresa_id)
            .filter(UsuarioEmpresa.usuario_id == current_user.id)
            .all()
        )
        return [r.empresa_id for r in rows]
    # SUPERVISOR / ESTANDAR / OPERATIVO → su única empresa asignada
    if current_user.empresa_id:
        return [current_user.empresa_id]
    return []
