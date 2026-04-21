from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.services.dashboard_service import ingresos_egresos_metrics
from app.api import deps
from app.models.usuario import Usuario, RolUsuario

router = APIRouter()


def _resolve_empresa_ids(
    db: Session,
    empresa_id: Optional[str],
    rfc: Optional[str],
    current_user: Usuario,
) -> Optional[List[str]]:
    """
    Devuelve la lista de empresa_ids a filtrar, o None si se deben incluir todas.

    Prioridad:
    1. SUPERVISOR/ESTANDAR/OPERATIVO → solo su empresa_id (ignora params externos).
    2. rfc proporcionado → todas las empresas con ese RFC accesibles al usuario.
    3. empresa_id proporcionado → lista de un solo elemento.
    4. Nada → None (sin filtro de empresa).
    """
    # Roles no-admin siempre ven solo su empresa
    if current_user.rol not in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN):
        eid = str(current_user.empresa_id) if current_user.empresa_id else None
        return [eid] if eid else None

    if rfc:
        from app.models.empresa import Empresa as EmpresaModel
        rows = db.query(EmpresaModel.id).filter(EmpresaModel.rfc == rfc.upper()).all()
        ids = [str(r.id) for r in rows]
        return ids if ids else None

    if empresa_id:
        return [empresa_id]

    return None


@router.get("/ingresos-egresos")
def get_ingresos_egresos(
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    months: int = Query(default=12, ge=1, le=24),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    return ingresos_egresos_metrics(db, empresa_ids=empresa_ids, months=months, year=year, month=month)


@router.get("/presupuestos")
def get_presupuestos_metrics(
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    from app.services.dashboard_service import presupuestos_metrics
    return presupuestos_metrics(db, empresa_ids=empresa_ids)


@router.get("/alertas")
def get_alertas(
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    from app.services.dashboard_service import alertas_metrics
    return alertas_metrics(db, empresa_ids=empresa_ids)


@router.get("/reportes")
def get_reportes(
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    from app.services.dashboard_service import reportes_metrics
    return reportes_metrics(db, empresa_ids=empresa_ids)


@router.get("/egresos-categoria")
def get_egresos_por_categoria(
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    from app.services.dashboard_service import egresos_por_categoria_metrics
    return egresos_por_categoria_metrics(db, empresa_ids=empresa_ids, year=year, month=month)
