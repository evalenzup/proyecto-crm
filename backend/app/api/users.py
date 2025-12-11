from typing import Any, List, Dict
from uuid import UUID
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.usuario import Usuario, UsuarioCreate, UsuarioUpdate, RolUsuario, UsuarioPreferences, UsuarioPreferencesUpdate
from app.services.usuario_service import usuario_repo
from app.database import get_db
from app.models.usuario import Usuario as UsuarioModel

router = APIRouter()

PREFERENCES_FILE = "data/preferences.json"

def _load_preferences() -> Dict[str, Any]:
    if not os.path.exists(PREFERENCES_FILE):
        return {}
    try:
        with open(PREFERENCES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_preferences(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(PREFERENCES_FILE), exist_ok=True)
    with open(PREFERENCES_FILE, "w") as f:
        json.dump(data, f, indent=2)

@router.get("/preferences", response_model=UsuarioPreferences)
def get_user_preferences(
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user preferences.
    """
    all_prefs = _load_preferences()
    user_prefs = all_prefs.get(str(current_user.id), {"theme": "light"})
    return user_prefs

@router.put("/preferences", response_model=UsuarioPreferences)
def update_user_preferences(
    prefs_in: UsuarioPreferencesUpdate,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update current user preferences.
    """
    all_prefs = _load_preferences()
    user_id = str(current_user.id)
    
    # Get existing or default
    current_prefs = all_prefs.get(user_id, {"theme": "light"})
    
    # Update
    current_prefs["theme"] = prefs_in.theme
    
    # Save
    all_prefs[user_id] = current_prefs
    _save_preferences(all_prefs)
    
    return current_prefs


@router.get("/me", response_model=Usuario)
def read_user_me(
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.get("/", response_model=List[Usuario])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve users.
    """
    if current_user.rol != RolUsuario.ADMIN:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    users, total = usuario_repo.get_multi(db, skip=skip, limit=limit)
    return users

@router.post("/", response_model=Usuario)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UsuarioCreate,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new user.
    """
    if current_user.rol != RolUsuario.ADMIN:
        raise HTTPException(status_code=400, detail="Not enough permissions")
        
    user = usuario_repo.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = usuario_repo.create(db, obj_in=user_in)
    return user

@router.get("/{user_id}", response_model=Usuario)
def read_user_by_id(
    user_id: UUID,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    if current_user.rol != RolUsuario.ADMIN:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    user = usuario_repo.get(db, id=user_id)
    if user == current_user:
        return user
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return user

@router.put("/{user_id}", response_model=Usuario)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: UUID,
    user_in: UsuarioUpdate,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a user.
    """
    if current_user.rol != RolUsuario.ADMIN:
        raise HTTPException(status_code=400, detail="Not enough permissions")
        
    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    user = usuario_repo.update(db, db_obj=user, obj_in=user_in)
    return user

@router.delete("/{user_id}", response_model=Usuario)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: UUID,
    current_user: UsuarioModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a user.
    """
    if current_user.rol != RolUsuario.ADMIN:
        raise HTTPException(status_code=400, detail="Not enough permissions")
        
    user = usuario_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
        
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete yourself",
        )
        
    user = usuario_repo.remove(db, id=user_id)
    return user
