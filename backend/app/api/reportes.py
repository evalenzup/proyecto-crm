from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api import deps
from app.models.usuario import Usuario, RolUsuario
from app.services.reportes_service import (
    financiero_mensual,
    financiero_por_empresa,
    egresos_categoria_rango,
    ventas_reporte,
    clientes_reporte,
)

router = APIRouter()


def _parse_fecha(periodo: str, param_name: str) -> datetime:
    """Parse a 'YYYY-MM' string into a datetime for the first day of that month."""
    try:
        return datetime.strptime(periodo, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"El parámetro '{param_name}' debe tener formato YYYY-MM (ej. 2025-01).",
        )


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
    2. rfc proporcionado → todas las empresas con ese RFC.
    3. empresa_id proporcionado → lista de un solo elemento.
    4. Nada (SUPERADMIN/ADMIN sin filtro) → None (sin filtro = todas las empresas).
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

    # SUPERADMIN/ADMIN with no filter → None means all empresas
    return None


@router.get("/financiero")
def get_financiero(
    fecha_inicio: str = Query(..., description="Mes de inicio en formato YYYY-MM"),
    fecha_fin: str = Query(..., description="Mes de fin en formato YYYY-MM"),
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    fi = _parse_fecha(fecha_inicio, "fecha_inicio")
    ff = _parse_fecha(fecha_fin, "fecha_fin")
    if fi > ff:
        raise HTTPException(status_code=422, detail="fecha_inicio no puede ser posterior a fecha_fin.")
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    return financiero_mensual(db, empresa_ids=empresa_ids, fecha_inicio=fi, fecha_fin=ff)


@router.get("/egresos-categoria")
def get_egresos_categoria(
    fecha_inicio: str = Query(..., description="Mes de inicio en formato YYYY-MM"),
    fecha_fin: str = Query(..., description="Mes de fin en formato YYYY-MM"),
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    fi = _parse_fecha(fecha_inicio, "fecha_inicio")
    ff = _parse_fecha(fecha_fin, "fecha_fin")
    if fi > ff:
        raise HTTPException(status_code=422, detail="fecha_inicio no puede ser posterior a fecha_fin.")
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    return egresos_categoria_rango(db, empresa_ids=empresa_ids, fecha_inicio=fi, fecha_fin=ff)


@router.get("/ventas")
def get_ventas(
    fecha_inicio: str = Query(..., description="Mes de inicio en formato YYYY-MM"),
    fecha_fin: str = Query(..., description="Mes de fin en formato YYYY-MM"),
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    fi = _parse_fecha(fecha_inicio, "fecha_inicio")
    ff = _parse_fecha(fecha_fin, "fecha_fin")
    if fi > ff:
        raise HTTPException(status_code=422, detail="fecha_inicio no puede ser posterior a fecha_fin.")
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    return ventas_reporte(db, empresa_ids=empresa_ids, fecha_inicio=fi, fecha_fin=ff)


@router.get("/clientes")
def get_clientes(
    fecha_inicio: str = Query(..., description="Mes de inicio en formato YYYY-MM"),
    fecha_fin: str = Query(..., description="Mes de fin en formato YYYY-MM"),
    empresa_id: Optional[str] = Query(default=None),
    rfc: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    fi = _parse_fecha(fecha_inicio, "fecha_inicio")
    ff = _parse_fecha(fecha_fin, "fecha_fin")
    if fi > ff:
        raise HTTPException(status_code=422, detail="fecha_inicio no puede ser posterior a fecha_fin.")
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    return clientes_reporte(db, empresa_ids=empresa_ids, fecha_inicio=fi, fecha_fin=ff)


@router.get("/financiero-por-empresa")
def get_financiero_por_empresa(
    fecha_inicio: str = Query(..., description="Formato YYYY-MM"),
    fecha_fin:    str = Query(..., description="Formato YYYY-MM"),
    empresa_id: Optional[str] = Query(default=None),
    rfc:        Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    fi = _parse_fecha(fecha_inicio, "fecha_inicio")
    ff = _parse_fecha(fecha_fin,    "fecha_fin")
    if fi > ff:
        raise HTTPException(status_code=422, detail="fecha_inicio no puede ser posterior a fecha_fin.")
    empresa_ids = _resolve_empresa_ids(db, empresa_id, rfc, current_user)
    return financiero_por_empresa(db, empresa_ids=empresa_ids, fecha_inicio=fi, fecha_fin=ff)
