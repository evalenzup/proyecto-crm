from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.dashboard_service import ingresos_egresos_metrics
from app.api import deps
from app.models.usuario import Usuario, RolUsuario

router = APIRouter()


@router.get("/ingresos-egresos")
def get_ingresos_egresos(
    empresa_id: Optional[str] = Query(default=None),
    months: int = Query(default=12, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = str(current_user.empresa_id) if current_user.empresa_id else None
        
    return ingresos_egresos_metrics(db, empresa_id=empresa_id, months=months)


@router.get("/presupuestos")
def get_presupuestos_metrics(
    empresa_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = str(current_user.empresa_id) if current_user.empresa_id else None

    from app.services.dashboard_service import presupuestos_metrics
    return presupuestos_metrics(db, empresa_id=empresa_id)
