# app/api/deps.py
import uuid as _uuid
from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import security
from app.core import restricciones
from app.core import operativo as op_rules
from app.database import get_db
from app.models.usuario import Usuario, RolUsuario, UsuarioEmpresa
from app.schemas.token import TokenPayload
from app.config import settings

import logging

logger = logging.getLogger("app")

# Sufijos de ruta que se consideran exportación masiva de datos.
_SUFIJOS_EXPORTACION = ("/export-excel", "/export-csv")

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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Rechaza refresh tokens usados como access tokens.
    # Ambos están firmados con la misma clave — sin esta verificación un refresh
    # token (TTL 7 días) valdría como Bearer en cualquier endpoint protegido.
    if token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = _uuid.UUID(str(token_data.sub))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _registrar_bloqueo(db: Session, usuario: Usuario, request: Request, bloqueo) -> None:
    """Deja constancia del bloqueo, como mucho una vez cada MINUTOS_ENTRE_AVISOS.

    Una pestaña abierta reintenta cada minuto; sin este control el log y la
    auditoría se llenaban con la misma línea toda la noche. El 403 se devuelve
    igual en cada intento, sólo se limita la constancia.
    """
    if not restricciones.debe_avisar(usuario.id, bloqueo.tipo):
        return
    logger.warning(
        "[Restricciones] %s bloqueado en %s %s — %s",
        usuario.email, request.method, request.url.path, bloqueo.motivo,
    )
    try:
        from app.services import auditoria_service as audit_svc

        audit_svc.registrar(
            db, accion=audit_svc.ACCESO_DENEGADO, entidad="usuario",
            usuario_id=usuario.id, usuario_email=usuario.email,
            empresa_id=usuario.empresa_id, entidad_id=str(usuario.id),
            detalle={
                "tipo": bloqueo.tipo,
                "motivo": bloqueo.motivo,
                "ruta": f"{request.method} {request.url.path}",
            },
            ip=restricciones.ip_del_request(request),
        )
        db.commit()
    except Exception:  # noqa: BLE001 — la auditoría nunca debe tapar el 403
        db.rollback()


def get_current_active_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Puerta única de los endpoints protegidos.

    Además de la cuenta activa, aquí se aplican las restricciones por usuario
    (horario, red de origen y facultad de eliminar). Al estar en un solo punto
    cubren los endpoints que ya existen y los que se agreguen después, sin
    tener que acordarse de ponerlas en cada uno.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    bloqueo = restricciones.verificar_acceso(current_user, request)
    if bloqueo:
        _registrar_bloqueo(db, current_user, request, bloqueo)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=bloqueo.motivo,
            # El front distingue esto de un 403 por permisos: cierra la sesión
            # en vez de fallar en silencio y reintentar cada minuto.
            headers={"X-Restriccion": bloqueo.tipo},
        )

    # Los 5 endpoints de exportación masiva comparten el sufijo /export-excel.
    # Se filtra por la ruta para cubrirlos todos desde un solo punto; los que se
    # agreguen después deben respetar esa convención de nombre.
    if not current_user.puede_exportar and request.url.path.rstrip("/").endswith(
        _SUFIJOS_EXPORTACION
    ):
        _registrar_bloqueo(db, current_user, request, restricciones.Bloqueo(
            "Tu cuenta no tiene permitido exportar información.", "exportar"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no tiene permitido exportar información.",
            headers={"X-Restriccion": "exportar"},
        )

    # Una cuenta de técnico sólo llega a su agenda. Se niega todo y se abre lo
    # necesario (core/operativo.py), para que un endpoint nuevo no quede
    # expuesto por descuido.
    if current_user.rol == RolUsuario.OPERATIVO and not op_rules.ruta_permitida(
        request.url.path
    ):
        logger.info(
            "[Operativo] %s intentó entrar a %s %s",
            current_user.email, request.method, request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta solo tiene acceso a tu agenda de servicios.",
        )

    if request.method == "DELETE" and not current_user.puede_eliminar:
        _registrar_bloqueo(db, current_user, request, restricciones.Bloqueo(
            "Tu cuenta no tiene permitido eliminar registros.", "eliminar"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no tiene permitido eliminar registros.",
            headers={"X-Restriccion": "eliminar"},
        )

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
