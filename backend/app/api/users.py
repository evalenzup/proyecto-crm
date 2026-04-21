from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.usuario import (
    Usuario, UsuarioCreate, UsuarioUpdate, RolUsuario,
    UsuarioPreferences, UsuarioPreferencesUpdate, ChangePassword,
    AsignarEmpresasIn, AsignarPermisosIn,
)
from app.services.usuario_service import usuario_repo
from app.database import get_db
from app.models.usuario import Usuario as UsuarioModel, UsuarioEmpresa, UsuarioPermiso

router = APIRouter()

_PREF_DEFAULTS = {"theme": "light", "font_size": 14}

# Roles que se consideran "admin o superior" para gestionar usuarios
_ADMIN_ROLES = {RolUsuario.SUPERADMIN, RolUsuario.ADMIN}


def _get_prefs(user: UsuarioModel) -> dict:
    prefs = dict(user.preferences or {})
    for k, v in _PREF_DEFAULTS.items():
        prefs.setdefault(k, v)
    return prefs


def _sync_empresas(db: Session, user: UsuarioModel, empresas_ids: List[UUID]) -> None:
    """Reemplaza las empresas accesibles del usuario."""
    db.query(UsuarioEmpresa).filter(UsuarioEmpresa.usuario_id == user.id).delete()
    db.flush()  # asegurar que los deletes se procesen antes de los inserts
    for eid in empresas_ids:
        db.add(UsuarioEmpresa(usuario_id=user.id, empresa_id=eid))


def _sync_permisos(db: Session, user: UsuarioModel, modulos: List[str]) -> None:
    """Reemplaza los permisos de módulo del usuario."""
    db.query(UsuarioPermiso).filter(UsuarioPermiso.usuario_id == user.id).delete()
    db.flush()  # asegurar que los deletes se procesen antes de los inserts
    for m in modulos:
        db.add(UsuarioPermiso(usuario_id=user.id, modulo=m))


# ── Preferences ───────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=UsuarioPreferences)
def get_user_preferences(
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    return _get_prefs(current_user)


@router.put("/preferences", response_model=UsuarioPreferences)
def update_user_preferences(
    prefs_in: UsuarioPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    current_prefs = _get_prefs(current_user)
    if prefs_in.theme is not None:
        current_prefs["theme"] = prefs_in.theme
    if prefs_in.font_size is not None:
        current_prefs["font_size"] = prefs_in.font_size
    current_user.preferences = current_prefs
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _get_prefs(current_user)


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=Usuario)
def read_user_me(
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    return current_user


@router.put("/me/password", response_model=Usuario)
def change_own_password(
    *,
    db: Session = Depends(get_db),
    body: ChangePassword,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    from app.core.security import verify_password
    if not verify_password(body.password_actual, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    if len(body.password_nuevo) < 6:
        raise HTTPException(status_code=400,
                            detail="La nueva contraseña debe tener al menos 6 caracteres")
    usuario_repo.update(db, db_obj=current_user, obj_in={"password": body.password_nuevo})
    return current_user


# ── CRUD usuarios (requiere ADMIN o superior) ─────────────────────────────────

@router.get("/", response_model=List[Usuario])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.rol not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    users, _ = usuario_repo.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=Usuario)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UsuarioCreate,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.rol not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    # Solo SUPERADMIN puede crear otros SUPERADMIN o ADMIN
    if user_in.rol in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN):
        if current_user.rol != RolUsuario.SUPERADMIN:
            raise HTTPException(status_code=403,
                                detail="Solo el SUPERADMIN puede crear usuarios ADMIN")
    existing = usuario_repo.get_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(status_code=400,
                            detail="Ya existe un usuario con ese email.")
    user = usuario_repo.create(db, obj_in=user_in)
    # Empresas accesibles (para admin)
    if user_in.empresas_ids is not None:
        _sync_empresas(db, user, user_in.empresas_ids)
    # Permisos de módulo (para estandar)
    if user_in.permisos is not None:
        _sync_permisos(db, user, user_in.permisos)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=Usuario)
def read_user_by_id(
    user_id: UUID,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    if current_user.rol not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404,
                            detail="El usuario no existe")
    return user


@router.put("/{user_id}", response_model=Usuario)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: UUID,
    user_in: UsuarioUpdate,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.rol not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    # Solo SUPERADMIN puede cambiar roles a ADMIN/SUPERADMIN
    if user_in.rol in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN):
        if current_user.rol != RolUsuario.SUPERADMIN:
            raise HTTPException(status_code=403,
                                detail="Solo el SUPERADMIN puede asignar roles ADMIN")

    update_data = user_in.model_dump(exclude_unset=True)
    resulting_rol = update_data.get("rol", user.rol)
    resulting_empresa_id = update_data.get("empresa_id", user.empresa_id)

    if resulting_rol in (RolUsuario.SUPERVISOR, RolUsuario.ESTANDAR) and not resulting_empresa_id:
        raise HTTPException(
            status_code=400,
            detail="Este rol requiere una empresa asignada (empresa_id requerido)",
        )

    # Extraer campos de relaciones antes de actualizar el modelo base
    empresas_ids = update_data.pop("empresas_ids", None)
    permisos = update_data.pop("permisos", None)

    user = usuario_repo.update(db, db_obj=user, obj_in=user_in)

    if empresas_ids is not None:
        _sync_empresas(db, user, empresas_ids)
    if permisos is not None:
        _sync_permisos(db, user, permisos)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=Usuario)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: UUID,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.rol not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="El usuario no existe")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    # SUPERADMIN no puede ser eliminado por un ADMIN
    if user.rol == RolUsuario.SUPERADMIN and current_user.rol != RolUsuario.SUPERADMIN:
        raise HTTPException(status_code=403,
                            detail="No tienes permiso para eliminar al SUPERADMIN")
    user = usuario_repo.remove(db, id=user_id)
    return user


# ── Endpoints dedicados para gestión de accesos ───────────────────────────────

@router.put("/{user_id}/empresas", response_model=Usuario)
def asignar_empresas(
    *,
    db: Session = Depends(get_db),
    user_id: UUID,
    body: AsignarEmpresasIn,
    current_user: UsuarioModel = Depends(deps.require_superadmin),
) -> Any:
    """Solo SUPERADMIN puede asignar las empresas accesibles a un ADMIN."""
    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="El usuario no existe")
    _sync_empresas(db, user, body.empresas_ids)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/permisos", response_model=Usuario)
def asignar_permisos(
    *,
    db: Session = Depends(get_db),
    user_id: UUID,
    body: AsignarPermisosIn,
    current_user: UsuarioModel = Depends(deps.require_admin_or_above),
) -> Any:
    """ADMIN o superior puede asignar módulos permitidos a un usuario ESTANDAR."""
    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="El usuario no existe")
    _sync_permisos(db, user, body.permisos)
    db.commit()
    db.refresh(user)
    return user
