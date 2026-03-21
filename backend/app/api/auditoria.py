# app/api/auditoria.py
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.auditoria import AuditoriaLog
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auditoria import AuditoriaPageOut

router = APIRouter()


@router.get("/", response_model=AuditoriaPageOut, summary="Historial de auditoría")
def listar_auditoria(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: Optional[UUID] = Query(None),
    accion: Optional[str] = Query(None, description="Filtrar por tipo de acción"),
    entidad: Optional[str] = Query(None, description="Filtrar por entidad (factura, cliente…)"),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Retorna el historial de auditoría. Solo accesible para ADMIN.
    Los SUPERVISOR solo ven registros de su propia empresa.
    """
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    if current_user.rol == RolUsuario.ADMIN and not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes especificar empresa_id.",
        )

    query = db.query(AuditoriaLog).filter(AuditoriaLog.empresa_id == empresa_id)

    if accion:
        query = query.filter(AuditoriaLog.accion == accion.upper())
    if entidad:
        query = query.filter(AuditoriaLog.entidad == entidad.lower())
    if fecha_desde:
        query = query.filter(AuditoriaLog.creado_en >= fecha_desde)
    if fecha_hasta:
        from datetime import datetime, timezone, timedelta
        hasta_fin = datetime.combine(fecha_hasta, datetime.max.time())
        query = query.filter(AuditoriaLog.creado_en <= hasta_fin)

    total = query.count()
    items = (
        query.order_by(AuditoriaLog.creado_en.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {"items": items, "total": total, "limit": limit, "offset": offset}
