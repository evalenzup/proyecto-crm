# app/api/programacion_facturas.py
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import Usuario
from app.services import auditoria_service as audit_svc
from app.schemas.programacion_factura import (
    ProgramacionFacturaCreate,
    ProgramacionFacturaListOut,
    ProgramacionFacturaOut,
    ProgramacionFacturaUpdate,
)
from app.services import programacion_factura_service as svc

router = APIRouter()


def _enrich(prog) -> dict:
    """Agrega campos denormalizados para la UI."""
    d = {c.name: getattr(prog, c.name) for c in prog.__table__.columns}
    d["cliente_nombre"] = (
        getattr(getattr(prog, "cliente", None), "nombre_comercial", None)
        or getattr(getattr(prog, "cliente", None), "nombre", None)
    )
    d["empresa_nombre"] = (
        getattr(getattr(prog, "empresa", None), "nombre_comercial", None)
        or getattr(getattr(prog, "empresa", None), "nombre", None)
    )
    # JSONB ya viene como lista de dicts — convertir conceptos a ConceptoPlantilla
    return d


@router.get("", response_model=ProgramacionFacturaListOut)
def listar(
    empresa_id: Optional[UUID] = Query(None),
    activo: Optional[bool]     = Query(None),
    offset: int                = Query(0, ge=0),
    limit: int                 = Query(50, ge=1, le=200),
    db: Session                = Depends(get_db),
    _: Usuario                 = Depends(deps.get_current_active_user),
):
    items, total = svc.listar_programaciones(db, empresa_id=empresa_id, activo=activo, offset=offset, limit=limit)
    return {"items": [_enrich(p) for p in items], "total": total}


@router.post("", response_model=ProgramacionFacturaOut, status_code=201)
def crear(
    payload: ProgramacionFacturaCreate,
    request: Request,
    db: Session  = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    prog = svc.crear_programacion(db, payload)
    audit_svc.registrar(
        db, accion=audit_svc.CREAR_PROGRAMACION_FACTURA, entidad="programacion_factura",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=prog.empresa_id, entidad_id=str(prog.id),
        detalle={"nombre": prog.nombre, "periodicidad": prog.periodicidad, "cliente_id": str(prog.cliente_id)},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return _enrich(prog)


@router.get("/{prog_id}", response_model=ProgramacionFacturaOut)
def obtener(
    prog_id: UUID,
    db: Session = Depends(get_db),
    _: Usuario  = Depends(deps.get_current_active_user),
):
    prog = svc.obtener_programacion(db, prog_id)
    return _enrich(prog)


@router.patch("/{prog_id}", response_model=ProgramacionFacturaOut)
def actualizar(
    prog_id: UUID,
    payload: ProgramacionFacturaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    prog = svc.actualizar_programacion(db, prog_id, payload)
    audit_svc.registrar(
        db, accion=audit_svc.ACTUALIZAR_PROGRAMACION_FACTURA, entidad="programacion_factura",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=prog.empresa_id, entidad_id=str(prog_id),
        detalle={"nombre": prog.nombre, "campos": list(payload.model_dump(exclude_unset=True).keys())},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return _enrich(prog)


@router.delete("/{prog_id}", status_code=204)
def eliminar(
    prog_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    prog = svc.obtener_programacion(db, prog_id)
    empresa_id, nombre = prog.empresa_id, prog.nombre
    svc.eliminar_programacion(db, prog_id)
    audit_svc.registrar(
        db, accion=audit_svc.ELIMINAR_PROGRAMACION_FACTURA, entidad="programacion_factura",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=empresa_id, entidad_id=str(prog_id),
        detalle={"nombre": nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()


@router.post("/{prog_id}/ejecutar-ahora", response_model=ProgramacionFacturaOut)
def ejecutar_ahora(
    prog_id: UUID,
    db: Session = Depends(get_db),
    _: Usuario  = Depends(deps.get_current_active_user),
):
    """Ejecuta la programación de forma manual sin esperar al cron."""
    from datetime import date
    prog = svc.obtener_programacion(db, prog_id)

    # Temporalmente poner proxima_ejecucion = hoy para que el ejecutor la tome
    original_fecha = prog.proxima_ejecucion
    prog.proxima_ejecucion = date.today()
    db.add(prog)
    db.commit()

    svc.ejecutar_programaciones_pendientes(db)
    db.refresh(prog)
    return _enrich(prog)
