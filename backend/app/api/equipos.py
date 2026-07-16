# app/api/equipos.py
"""
Equipos de control por cliente — configurable por empresa.

Rutas (prefijo /api/equipos):
  Config por empresa:
    GET/POST            /tipos
    GET/PUT/DELETE      /tipos/{tipo_id}
    GET/POST            /estados
    GET/PUT/DELETE      /estados/{estado_id}
  Equipos por cliente:
    GET/POST            /
    POST                /bulk
    GET/PUT/DELETE      /{equipo_id}
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.services import auditoria_service as audit_svc
from app.schemas.equipo import (
    EquipoControlBulkCreate,
    EquipoControlCreate,
    EquipoControlOut,
    EquipoControlPageOut,
    EquipoControlUpdate,
    EstadoEquipoCreate,
    EstadoEquipoOut,
    EstadoEquipoUpdate,
    TipoEquipoCreate,
    TipoEquipoOut,
    TipoEquipoUpdate,
)
from app.services import equipo_service as svc

router = APIRouter()


def _scope_empresa(current_user: Usuario, empresa_id: Optional[UUID]) -> Optional[UUID]:
    """Los supervisores quedan acotados a su propia empresa."""
    if current_user.rol == RolUsuario.SUPERVISOR:
        return current_user.empresa_id
    return empresa_id


# ════════════════════════════════════════════════════════════════════════════
# Tipos de equipo (config por empresa)
# ════════════════════════════════════════════════════════════════════════════
@router.get("/tipos", response_model=List[TipoEquipoOut])
def listar_tipos(
    empresa_id: UUID = Query(...),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_id = _scope_empresa(current_user, empresa_id)
    return svc.list_tipos_equipo(db, empresa_id=empresa_id, activo=activo)


@router.post("/tipos", response_model=TipoEquipoOut, status_code=201)
def crear_tipo(
    data: TipoEquipoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.create_tipo_equipo(db, data)
    audit_svc.registrar(
        db, accion=audit_svc.CREAR_TIPO_EQUIPO, entidad="tipo_equipo",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(obj.id),
        detalle={"nombre": obj.nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()
    return obj


@router.get("/tipos/{tipo_id}", response_model=TipoEquipoOut)
def obtener_tipo(
    tipo_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.get_tipo_equipo(db, tipo_id)


@router.put("/tipos/{tipo_id}", response_model=TipoEquipoOut)
def actualizar_tipo(
    tipo_id: UUID,
    data: TipoEquipoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.update_tipo_equipo(db, tipo_id, data)
    audit_svc.registrar(
        db, accion=audit_svc.ACTUALIZAR_TIPO_EQUIPO, entidad="tipo_equipo",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(tipo_id),
        detalle={"nombre": obj.nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()
    return obj


@router.delete("/tipos/{tipo_id}", status_code=204)
def eliminar_tipo(
    tipo_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_tipo_equipo(db, tipo_id)
    empresa_id, nombre = obj.empresa_id, obj.nombre
    svc.delete_tipo_equipo(db, tipo_id)
    audit_svc.registrar(
        db, accion=audit_svc.ELIMINAR_TIPO_EQUIPO, entidad="tipo_equipo",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=empresa_id, entidad_id=str(tipo_id),
        detalle={"nombre": nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# Estados de equipo (config por empresa)
# ════════════════════════════════════════════════════════════════════════════
@router.get("/estados", response_model=List[EstadoEquipoOut])
def listar_estados(
    empresa_id: UUID = Query(...),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_id = _scope_empresa(current_user, empresa_id)
    return svc.list_estados_equipo(db, empresa_id=empresa_id, activo=activo)


@router.post("/estados", response_model=EstadoEquipoOut, status_code=201)
def crear_estado(
    data: EstadoEquipoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.create_estado_equipo(db, data)
    audit_svc.registrar(
        db, accion=audit_svc.CREAR_ESTADO_EQUIPO, entidad="estado_equipo",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(obj.id),
        detalle={"nombre": obj.nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()
    return obj


@router.put("/estados/{estado_id}", response_model=EstadoEquipoOut)
def actualizar_estado(
    estado_id: UUID,
    data: EstadoEquipoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.update_estado_equipo(db, estado_id, data)
    audit_svc.registrar(
        db, accion=audit_svc.ACTUALIZAR_ESTADO_EQUIPO, entidad="estado_equipo",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(estado_id),
        detalle={"nombre": obj.nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()
    return obj


@router.delete("/estados/{estado_id}", status_code=204)
def eliminar_estado(
    estado_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_estado_equipo(db, estado_id)
    empresa_id, nombre = obj.empresa_id, obj.nombre
    svc.delete_estado_equipo(db, estado_id)
    audit_svc.registrar(
        db, accion=audit_svc.ELIMINAR_ESTADO_EQUIPO, entidad="estado_equipo",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=empresa_id, entidad_id=str(estado_id),
        detalle={"nombre": nombre}, ip=audit_svc.get_ip(request),
    )
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# Equipos de control (por cliente)
# ════════════════════════════════════════════════════════════════════════════
@router.get("", response_model=EquipoControlPageOut)
def listar_equipos(
    cliente_id: Optional[UUID] = Query(None),
    empresa_id: Optional[UUID] = Query(None),
    tipo_equipo_id: Optional[UUID] = Query(None),
    estado_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_id = _scope_empresa(current_user, empresa_id)
    items, total = svc.list_equipos(
        db,
        cliente_id=cliente_id,
        empresa_id=empresa_id,
        tipo_equipo_id=tipo_equipo_id,
        estado_id=estado_id,
        q=q,
        activo=activo,
        limit=limit,
        offset=offset,
    )
    return EquipoControlPageOut(
        items=[svc.to_out_dict(o) for o in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=EquipoControlOut, status_code=201)
def crear_equipo(
    data: EquipoControlCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.create_equipo(db, data)
    audit_svc.registrar(
        db, accion=audit_svc.CREAR_EQUIPO, entidad="equipo_control",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(obj.id),
        detalle={"identificador": obj.identificador, "area": obj.area, "cliente_id": str(obj.cliente_id)},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return svc.to_out_dict(obj)


@router.post("/bulk", response_model=List[EquipoControlOut], status_code=201)
def crear_equipos_masivo(
    data: EquipoControlBulkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    creados = svc.bulk_create_equipos(db, data)
    audit_svc.registrar(
        db, accion=audit_svc.ALTA_MASIVA_EQUIPOS, entidad="equipo_control",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=data.empresa_id, entidad_id=None,
        detalle={"cantidad": len(creados), "area": data.area, "cliente_id": str(data.cliente_id)},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return [svc.to_out_dict(o) for o in creados]


@router.get("/{equipo_id}", response_model=EquipoControlOut)
def obtener_equipo(
    equipo_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.to_out_dict(svc.get_equipo(db, equipo_id))


@router.put("/{equipo_id}", response_model=EquipoControlOut)
def actualizar_equipo(
    equipo_id: UUID,
    data: EquipoControlUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.update_equipo(db, equipo_id, data)
    audit_svc.registrar(
        db, accion=audit_svc.ACTUALIZAR_EQUIPO, entidad="equipo_control",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(equipo_id),
        detalle={"identificador": obj.identificador, "area": obj.area},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return svc.to_out_dict(obj)


@router.delete("/{equipo_id}", status_code=204)
def eliminar_equipo(
    equipo_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_equipo(db, equipo_id)
    empresa_id, ident, area = obj.empresa_id, obj.identificador, obj.area
    svc.delete_equipo(db, equipo_id)
    audit_svc.registrar(
        db, accion=audit_svc.ELIMINAR_EQUIPO, entidad="equipo_control",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=empresa_id, entidad_id=str(equipo_id),
        detalle={"identificador": ident, "area": area},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
