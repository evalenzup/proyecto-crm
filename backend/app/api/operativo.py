# app/api/operativo.py
"""
Routers Sprint 6 — Catálogos Operativos:
  /api/servicios-operativos
  /api/tecnicos
  /api/unidades   (incluye sub-recurso /api/unidades/{id}/mantenimientos)
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.schemas.servicio_operativo import (
    ServicioOperativoCreate,
    ServicioOperativoOut,
    ServicioOperativoPageOut,
    ServicioOperativoUpdate,
)
from app.schemas.tecnico import TecnicoCreate, TecnicoOut, TecnicoPageOut, TecnicoUpdate
from app.schemas.unidad import UnidadCreate, UnidadOut, UnidadPageOut, UnidadUpdate
from app.schemas.mantenimiento_unidad import (
    MantenimientoCreate,
    MantenimientoOut,
    MantenimientoPageOut,
    MantenimientoUpdate,
)
from app.services import servicio_operativo_service as svc_servicio
from app.services import tecnico_service as svc_tecnico
from app.services import unidad_service as svc_unidad
from app.services import mantenimiento_unidad_service as svc_mant

# ─── Routers ─────────────────────────────────────────────────────────────────

servicios_router = APIRouter()
tecnicos_router = APIRouter()
unidades_router = APIRouter()


# ════════════════════════════════════════════════════════════════════════════
# ServicioOperativo
# ════════════════════════════════════════════════════════════════════════════

@servicios_router.get("", response_model=ServicioOperativoPageOut)
def listar_servicios(
    empresa_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None, description="Búsqueda por nombre"),
    activo: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    items, total = svc_servicio.list_servicios(
        db, empresa_id=empresa_id, q=q, activo=activo, limit=limit, offset=offset
    )
    return ServicioOperativoPageOut(items=items, total=total, limit=limit, offset=offset)


@servicios_router.post("", response_model=ServicioOperativoOut, status_code=201)
def crear_servicio(
    data: ServicioOperativoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_servicio.create_servicio(db, data)


@servicios_router.get("/{servicio_id}", response_model=ServicioOperativoOut)
def obtener_servicio(
    servicio_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_servicio.get_servicio(db, servicio_id)


@servicios_router.put("/{servicio_id}", response_model=ServicioOperativoOut)
def actualizar_servicio(
    servicio_id: UUID,
    data: ServicioOperativoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_servicio.update_servicio(db, servicio_id, data)


@servicios_router.delete("/{servicio_id}", status_code=204)
def eliminar_servicio(
    servicio_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    svc_servicio.delete_servicio(db, servicio_id)


# ════════════════════════════════════════════════════════════════════════════
# Tecnico
# ════════════════════════════════════════════════════════════════════════════

@tecnicos_router.get("", response_model=TecnicoPageOut)
def listar_tecnicos(
    empresa_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    items, total = svc_tecnico.list_tecnicos(
        db, empresa_id=empresa_id, q=q, activo=activo, limit=limit, offset=offset
    )
    return TecnicoPageOut(items=items, total=total, limit=limit, offset=offset)


@tecnicos_router.post("", response_model=TecnicoOut, status_code=201)
def crear_tecnico(
    data: TecnicoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_tecnico.create_tecnico(db, data)


@tecnicos_router.get("/{tecnico_id}", response_model=TecnicoOut)
def obtener_tecnico(
    tecnico_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_tecnico.get_tecnico(db, tecnico_id)


@tecnicos_router.put("/{tecnico_id}", response_model=TecnicoOut)
def actualizar_tecnico(
    tecnico_id: UUID,
    data: TecnicoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_tecnico.update_tecnico(db, tecnico_id, data)


@tecnicos_router.delete("/{tecnico_id}", status_code=204)
def eliminar_tecnico(
    tecnico_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    svc_tecnico.delete_tecnico(db, tecnico_id)


# ════════════════════════════════════════════════════════════════════════════
# Unidad  (+ sub-recurso mantenimientos)
# ════════════════════════════════════════════════════════════════════════════

@unidades_router.get("", response_model=UnidadPageOut)
def listar_unidades(
    empresa_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    items, total = svc_unidad.list_unidades(
        db, empresa_id=empresa_id, q=q, activo=activo, limit=limit, offset=offset
    )
    return UnidadPageOut(items=items, total=total, limit=limit, offset=offset)


@unidades_router.post("", response_model=UnidadOut, status_code=201)
def crear_unidad(
    data: UnidadCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_unidad.create_unidad(db, data)


@unidades_router.get("/{unidad_id}", response_model=UnidadOut)
def obtener_unidad(
    unidad_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_unidad.get_unidad(db, unidad_id)


@unidades_router.put("/{unidad_id}", response_model=UnidadOut)
def actualizar_unidad(
    unidad_id: UUID,
    data: UnidadUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_unidad.update_unidad(db, unidad_id, data)


@unidades_router.delete("/{unidad_id}", status_code=204)
def eliminar_unidad(
    unidad_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    svc_unidad.delete_unidad(db, unidad_id)


# ── Mantenimientos (sub-recurso de Unidad) ───────────────────────────────────

@unidades_router.get("/{unidad_id}/mantenimientos", response_model=MantenimientoPageOut)
def listar_mantenimientos(
    unidad_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    items, total = svc_mant.list_mantenimientos(
        db, unidad_id=unidad_id, limit=limit, offset=offset
    )
    return MantenimientoPageOut(items=items, total=total, limit=limit, offset=offset)


@unidades_router.post("/{unidad_id}/mantenimientos", response_model=MantenimientoOut, status_code=201)
def crear_mantenimiento(
    unidad_id: UUID,
    data: MantenimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_mant.create_mantenimiento(db, unidad_id, data)


@unidades_router.put("/{unidad_id}/mantenimientos/{mant_id}", response_model=MantenimientoOut)
def actualizar_mantenimiento(
    unidad_id: UUID,
    mant_id: UUID,
    data: MantenimientoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc_mant.update_mantenimiento(db, mant_id, data)


@unidades_router.delete("/{unidad_id}/mantenimientos/{mant_id}", status_code=204)
def eliminar_mantenimiento(
    unidad_id: UUID,
    mant_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    svc_mant.delete_mantenimiento(db, mant_id)
