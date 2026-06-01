# app/api/public.py
"""
Endpoints públicos (sin autenticación) para verificación de credenciales.
Solo expone datos necesarios para confirmar identidad en campo.
"""
from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings

router = APIRouter()

_TECNICOS_FOTOS_DIR = os.path.join(settings.DATA_DIR, "tecnicos_fotos")
_LOGOS_DIR = os.path.join(settings.DATA_DIR, "logos")


# ── Agenda pública ────────────────────────────────────────────────────────────

class AgendaItemOut(BaseModel):
    id: str
    folio_os: str
    fecha_programada: str
    hora_inicio: str | None
    hora_fin: str | None
    estado: str
    prioridad: str
    cliente_nombre: str | None
    tecnico_nombre: str | None
    direccion_servicio: str | None
    notas_tecnico: str | None


@router.get("/agenda", response_model=dict)
def agenda_publica(
    empresa_id: UUID,
    fecha: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Devuelve las órdenes de servicio del día para una empresa (sin auth).
    Usado por la página pública de agenda para técnicos.
    """
    from datetime import date as date_type, datetime
    from app.models.orden_servicio import OrdenServicio
    from app.models.cliente import Cliente
    from app.models.tecnico import Tecnico

    # Fecha: hoy si no se especifica
    try:
        target_date = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else date_type.today()
    except ValueError:
        target_date = date_type.today()

    rows = (
        db.query(OrdenServicio)
        .filter(
            OrdenServicio.empresa_id == empresa_id,
            OrdenServicio.fecha_programada == target_date,
            OrdenServicio.activo == True,
        )
        .order_by(OrdenServicio.hora_inicio.asc().nullslast())
        .all()
    )

    items = []
    for o in rows:
        items.append(AgendaItemOut(
            id=str(o.id),
            folio_os=o.folio_os,
            fecha_programada=str(o.fecha_programada),
            hora_inicio=str(o.hora_inicio)[:5] if o.hora_inicio else None,
            hora_fin=str(o.hora_fin)[:5] if o.hora_fin else None,
            estado=o.estado,
            prioridad=o.prioridad,
            cliente_nombre=o.cliente.nombre_comercial if o.cliente else None,
            tecnico_nombre=o.tecnico.nombre_completo if o.tecnico else None,
            direccion_servicio=o.direccion_servicio,
            notas_tecnico=o.notas_tecnico,
        ))

    return {"items": items, "fecha": str(target_date), "total": len(items)}


class VerificacionOut(BaseModel):
    id: str
    nombre_completo: str
    tipo_personal: str
    area: str | None
    puesto: str | None
    activo: bool
    empresa_nombre: str
    empresa_id: str
    empresa_color: str


@router.get("/tecnicos/{tecnico_id}/verificar", response_model=VerificacionOut)
def verificar_tecnico(tecnico_id: UUID, db: Session = Depends(get_db)):
    """Devuelve datos públicos de verificación del técnico (sin auth)."""
    from app.models.tecnico import Tecnico
    tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    empresa = tecnico.empresa
    return VerificacionOut(
        id=str(tecnico.id),
        nombre_completo=tecnico.nombre_completo or "",
        tipo_personal=tecnico.tipo_personal or "TECNICO",
        area=tecnico.area,
        puesto=tecnico.puesto,
        activo=tecnico.activo,
        empresa_nombre=empresa.nombre_comercial or empresa.nombre,
        empresa_id=str(empresa.id),
        empresa_color=empresa.color_credencial or "#1a6b3a",
    )


@router.get("/tecnicos/{tecnico_id}/foto")
def foto_publica_tecnico(tecnico_id: UUID, db: Session = Depends(get_db)):
    """Devuelve la foto del técnico sin autenticación (para verificación pública)."""
    from app.models.tecnico import Tecnico
    tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not tecnico or not tecnico.foto:
        raise HTTPException(status_code=404, detail="Sin foto")
    path = os.path.join(_TECNICOS_FOTOS_DIR, tecnico.foto)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/empresas/{empresa_id}/logo")
def logo_publico_empresa(empresa_id: UUID, db: Session = Depends(get_db)):
    """Devuelve el logo de la empresa sin autenticación (para verificación pública)."""
    from app.models.empresa import Empresa
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    path = os.path.join(_LOGOS_DIR, f"{empresa_id}.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    return FileResponse(path, media_type="image/png")
