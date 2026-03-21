from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.api import deps
from app.models.usuario import Usuario
from app.schemas.notificacion import NotificacionListResponse, NotificacionOut
from app.services import notificacion_service as svc

router = APIRouter()


@router.get("/", response_model=NotificacionListResponse)
def listar_notificaciones(
    solo_no_leidas: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Lista las notificaciones de la empresa del usuario autenticado."""
    items, total, no_leidas = svc.listar_notificaciones(
        db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        solo_no_leidas=solo_no_leidas,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "no_leidas": no_leidas}


@router.patch("/{id}/leer", response_model=NotificacionOut)
def marcar_leida(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Marca una notificación como leída."""
    notif = svc.marcar_leida(db, notificacion_id=id, empresa_id=current_user.empresa_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    return notif


@router.patch("/leer-todas", status_code=200)
def marcar_todas_leidas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Marca todas las notificaciones del usuario como leídas."""
    count = svc.marcar_todas_leidas(
        db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
    )
    return {"message": f"{count} notificaciones marcadas como leídas."}
