# app/api/planes_servicio.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.schemas.plan_servicio import (
    PlanServicioCreate,
    PlanServicioOut,
    PlanServicioUpdate,
    ProgramarRequest,
    TableroOut,
)
from app.services import auditoria_service as audit_svc
from app.services import plan_servicio_service as svc

router = APIRouter()


def _scope(current_user: Usuario, empresa_id: Optional[UUID]) -> Optional[UUID]:
    """Los supervisores quedan acotados a su empresa."""
    if current_user.rol == RolUsuario.SUPERVISOR:
        return current_user.empresa_id
    return empresa_id


def _out(plan) -> dict:
    d = {c.name: getattr(plan, c.name) for c in plan.__table__.columns}
    d.update(svc._to_out_extra(plan))
    return d


@router.get("", response_model=List[PlanServicioOut])
def listar_planes(
    empresa_id: Optional[UUID] = Query(None),
    cliente_id: Optional[UUID] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    planes = svc.listar_planes(
        db, empresa_id=_scope(current_user, empresa_id), cliente_id=cliente_id, activo=activo
    )
    return [_out(p) for p in planes]


@router.get("/tablero", response_model=TableroOut)
def tablero(
    empresa_id: UUID = Query(...),
    anio: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.tablero(db, empresa_id=_scope(current_user, empresa_id), anio=anio, mes=mes)


@router.get("/{plan_id}", response_model=PlanServicioOut)
def obtener_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return _out(svc.obtener_plan(db, plan_id))


@router.post("", response_model=PlanServicioOut, status_code=201)
def crear_plan(
    payload: PlanServicioCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    plan = svc.crear_plan(db, payload)
    audit_svc.registrar(
        db, accion=audit_svc.CREAR_PLAN_SERVICIO, entidad="plan_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=plan.empresa_id, entidad_id=str(plan.id),
        detalle={"cliente_id": str(plan.cliente_id), "periodicidad": plan.periodicidad},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return _out(plan)


@router.put("/{plan_id}", response_model=PlanServicioOut)
def actualizar_plan(
    plan_id: UUID,
    payload: PlanServicioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    plan = svc.actualizar_plan(db, plan_id, payload)
    audit_svc.registrar(
        db, accion=audit_svc.ACTUALIZAR_PLAN_SERVICIO, entidad="plan_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=plan.empresa_id, entidad_id=str(plan_id),
        detalle={"campos": list(payload.model_dump(exclude_unset=True).keys())},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return _out(plan)


@router.delete("/{plan_id}", status_code=204)
def eliminar_plan(
    plan_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    plan = svc.obtener_plan(db, plan_id)
    empresa_id, cliente_id = plan.empresa_id, plan.cliente_id
    svc.eliminar_plan(db, plan_id)
    audit_svc.registrar(
        db, accion=audit_svc.ELIMINAR_PLAN_SERVICIO, entidad="plan_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=empresa_id, entidad_id=str(plan_id),
        detalle={"cliente_id": str(cliente_id)},
        ip=audit_svc.get_ip(request),
    )
    db.commit()


@router.post("/{plan_id}/programar", status_code=201)
def programar(
    plan_id: UUID,
    payload: ProgramarRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    orden = svc.programar(db, plan_id, payload, usuario_id=current_user.id)
    audit_svc.registrar(
        db, accion=audit_svc.PROGRAMAR_PLAN_SERVICIO, entidad="orden_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=orden.empresa_id, entidad_id=str(orden.id),
        detalle={"plan_id": str(plan_id), "folio_os": orden.folio_os, "fecha": str(orden.fecha_programada)},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return {"id": str(orden.id), "folio_os": orden.folio_os, "fecha_programada": str(orden.fecha_programada)}
