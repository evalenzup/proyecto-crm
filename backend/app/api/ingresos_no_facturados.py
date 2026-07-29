# app/api/ingresos_no_facturados.py
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.schemas.ingresos_no_facturados import (
    IngresosNoFacturadosOut,
    MarcarCobroIn,
)
from app.services import auditoria_service as audit_svc
from app.services import ingresos_no_facturados_service as svc

router = APIRouter()

# Permiso que otorga el SUPERADMIN por usuario, desde el form de usuarios.
PERMISO_INGRESOS = "ingresos_no_facturados"


def _puede_ver(current_user: Usuario) -> None:
    if current_user.rol == RolUsuario.SUPERADMIN:
        return
    if PERMISO_INGRESOS in (current_user.permisos or []):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para ver los ingresos no facturados.",
    )


def _scope(current_user: Usuario, empresa_id: Optional[UUID]) -> Optional[UUID]:
    if current_user.rol == RolUsuario.SUPERVISOR:
        return current_user.empresa_id
    return empresa_id


@router.get("", response_model=IngresosNoFacturadosOut)
def listar_ingresos(
    empresa_id: Optional[UUID] = Query(None),
    cliente_id: Optional[UUID] = Query(None),
    anio: Optional[int] = Query(None, ge=2000, le=2100),
    mes: Optional[int] = Query(None, ge=1, le=12),
    cobrado: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _puede_ver(current_user)
    return svc.listar(
        db,
        empresa_id=_scope(current_user, empresa_id),
        cliente_id=cliente_id,
        anio=anio,
        mes=mes,
        cobrado=cobrado,
    )


@router.patch("/{orden_id}/cobro")
def marcar_cobro(
    orden_id: UUID,
    payload: MarcarCobroIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    _puede_ver(current_user)
    orden = svc.marcar_cobro(
        db, orden_id,
        cobrado=payload.cobrado,
        fecha_cobro=payload.fecha_cobro,
        forma_cobro=payload.forma_cobro,
    )
    audit_svc.registrar(
        db, accion=audit_svc.MARCAR_COBRO_ORDEN, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=orden.empresa_id, entidad_id=str(orden.id),
        detalle={
            "folio_os": orden.folio_os,
            "operacion": "Marcada como cobrada" if payload.cobrado else "Regresada a pendiente",
            "cobrado": payload.cobrado,
            "forma_cobro": payload.forma_cobro,
            "fecha_cobro": str(orden.fecha_cobro) if orden.fecha_cobro else None,
        },
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    db.refresh(orden)
    return {
        "orden_id": str(orden.id),
        "cobrado": orden.cobrado,
        "fecha_cobro": str(orden.fecha_cobro) if orden.fecha_cobro else None,
        "forma_cobro": orden.forma_cobro,
    }
