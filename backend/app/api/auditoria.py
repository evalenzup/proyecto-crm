# app/api/auditoria.py
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.auditoria import AuditoriaLog
from app.models.usuario import RolUsuario, Usuario  # noqa: F401 (RolUsuario used in checks)
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
    order_by: Optional[str] = Query(None),
    order_dir: Optional[str] = Query(None),
):
    """
    Retorna el historial de auditoría. Solo accesible para ADMIN.
    Los SUPERVISOR solo ven registros de su propia empresa.
    """
    # Supervisores solo ven su propia empresa
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    # ADMIN (sin SUPERADMIN) necesita especificar empresa_id
    if current_user.rol == RolUsuario.ADMIN and not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes especificar empresa_id.",
        )

    # Usuarios sin acceso
    if current_user.rol not in (
        RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.SUPERVISOR
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver la auditoría.",
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
    from app.services.ordering import apply_order
    # Por defecto: más reciente primero (creado_en desc)
    eff_by = order_by or "creado_en"
    eff_dir = order_dir or ("desc" if eff_by == "creado_en" else "asc")
    query = apply_order(
        query, AuditoriaLog, eff_by, eff_dir,
        allowed={"creado_en", "usuario_email", "accion", "entidad"},
        default="creado_en",
    )
    items = query.offset(offset).limit(limit).all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}


# Permiso para ver los reportes de actividad del personal (info sensible).
# Lo otorga el SUPERADMIN por usuario, desde el formulario de usuarios.
PERMISO_ACTIVIDAD = "reportes_actividad"


def _puede_ver_actividad(current_user: Usuario):
    if current_user.rol == RolUsuario.SUPERADMIN:
        return
    if PERMISO_ACTIVIDAD in (current_user.permisos or []):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para ver los reportes de actividad del personal.",
    )


@router.get("/actividad", summary="Reporte de actividad del personal (solo administradores)")
def reporte_actividad(
    usuario_ids: str = Query(..., description="IDs de usuario separados por coma"),
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    empresa_id: Optional[UUID] = Query(None),
    hora_ini: int = Query(8, ge=0, le=23),
    hora_fin: int = Query(18, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _puede_ver_actividad(current_user)
    # Solo el SUPERADMIN puede ver todas las empresas o filtrar una; el resto
    # queda acotado a su propia empresa.
    if current_user.rol != RolUsuario.SUPERADMIN:
        empresa_id = current_user.empresa_id

    try:
        ids = [UUID(x.strip()) for x in usuario_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="usuario_ids inválidos")
    if not ids:
        raise HTTPException(status_code=400, detail="Selecciona al menos un usuario")

    from app.services.actividad_service import reporte_actividad as _rep
    return _rep(
        db, empresa_id=empresa_id, usuario_ids=ids,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        hora_ini=hora_ini, hora_fin=hora_fin,
    )


@router.get("/export-excel", summary="Exportar la bitácora a Excel")
def exportar_auditoria_excel(
    empresa_id: Optional[UUID] = Query(None),
    accion: Optional[str] = Query(None),
    entidad: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    from app.utils.excel import generate_excel
    from app.utils.datetime_utils import to_tijuana
    from fastapi.responses import StreamingResponse
    import json as _json

    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    if current_user.rol == RolUsuario.ADMIN and not empresa_id:
        empresa_id = current_user.empresa_id

    query = db.query(AuditoriaLog)
    if empresa_id:
        query = query.filter(AuditoriaLog.empresa_id == empresa_id)
    if accion:
        query = query.filter(AuditoriaLog.accion == accion.upper())
    if entidad:
        query = query.filter(AuditoriaLog.entidad == entidad.lower())
    if fecha_desde:
        query = query.filter(AuditoriaLog.creado_en >= fecha_desde)
    if fecha_hasta:
        from datetime import datetime as _dt
        query = query.filter(AuditoriaLog.creado_en <= _dt.combine(fecha_hasta, _dt.max.time()))
    rows = query.order_by(AuditoriaLog.creado_en.desc()).limit(50000).all()

    data = []
    for r in rows:
        tj = to_tijuana(r.creado_en)
        detalle = r.detalle or ""
        try:
            d = _json.loads(detalle)
            detalle = ", ".join(f"{k}: {v}" for k, v in d.items())
        except Exception:
            pass
        data.append({
            "fecha": tj.strftime("%d/%m/%Y %H:%M:%S") if tj else "",
            "usuario": r.usuario_email or "",
            "accion": r.accion,
            "entidad": r.entidad or "",
            "detalle": detalle,
            "ip": r.ip or "",
        })

    headers = {
        "fecha": "Fecha / Hora",
        "usuario": "Usuario",
        "accion": "Acción",
        "entidad": "Entidad",
        "detalle": "Detalle",
        "ip": "IP",
    }
    excel_file = generate_excel(data, headers, sheet_name="Auditoria")
    return StreamingResponse(
        excel_file,
        headers={"Content-Disposition": 'attachment; filename="auditoria.xlsx"'},
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
