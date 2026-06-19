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
_CROQUIS_DIR = os.path.join(settings.DATA_DIR, "croquis")


def _safe_path(base_dir: str, filename: str) -> str:
    """Verifica que filename no escape de base_dir mediante secuencias '../'."""
    base = os.path.realpath(base_dir)
    resolved = os.path.realpath(os.path.join(base, filename))
    if not resolved.startswith(base + os.sep):
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")
    return resolved


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
    servicio_nombre: str | None
    direccion_servicio: str | None
    notas_tecnico: str | None
    precio_acordado: float | None
    cliente_id: str | None
    croquis_count: int = 0
    equipos_resumen: list[dict] = []


class AgendaEmpresaOut(BaseModel):
    nombre: str
    color: str


class CroquisPublicoOut(BaseModel):
    id: str
    titulo: str
    area: str | None
    descripcion: str | None


@router.get("/agenda", response_model=dict)
def agenda_publica(
    agenda_token: str,
    fecha: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Devuelve las órdenes de servicio del día para una empresa (sin auth).
    Requiere el token rotable de agenda — distinto del UUID de empresa.
    Usado por la página pública de agenda para técnicos de campo.
    """
    from datetime import date as date_type, datetime
    from app.models.orden_servicio import OrdenServicio
    from app.models.empresa import Empresa

    # Buscar empresa por token (no por UUID — el token es el único secreto)
    empresa = db.query(Empresa).filter(Empresa.agenda_token == agenda_token).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Enlace de agenda inválido")

    # Fecha: hoy si no se especifica
    try:
        target_date = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else date_type.today()
    except ValueError:
        target_date = date_type.today()

    rows = (
        db.query(OrdenServicio)
        .filter(
            OrdenServicio.empresa_id == empresa.id,
            OrdenServicio.fecha_programada == target_date,
            OrdenServicio.activo == True,
        )
        .order_by(OrdenServicio.hora_inicio.asc().nullslast())
        .all()
    )

    # Conteo de croquis por cliente (de esta empresa) para los clientes del día
    from sqlalchemy import func
    from app.models.croquis import Croquis
    cliente_ids = {o.cliente_id for o in rows if o.cliente_id}
    croquis_por_cliente: dict = {}
    if cliente_ids:
        for cid, cnt in (
            db.query(Croquis.cliente_id, func.count(Croquis.id))
            .filter(Croquis.empresa_id == empresa.id, Croquis.cliente_id.in_(cliente_ids))
            .group_by(Croquis.cliente_id)
            .all()
        ):
            croquis_por_cliente[cid] = cnt

    # Resumen de equipos de control por cliente (por tipo)
    from app.services.equipo_service import resumen_equipos_por_cliente
    equipos_por_cliente = resumen_equipos_por_cliente(db, empresa.id, list(cliente_ids))

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
            servicio_nombre=o.servicio.nombre if o.servicio else None,
            direccion_servicio=o.direccion_servicio,
            notas_tecnico=o.notas_tecnico,
            precio_acordado=float(o.precio_acordado) if o.precio_acordado is not None else None,
            cliente_id=str(o.cliente_id) if o.cliente_id else None,
            croquis_count=croquis_por_cliente.get(o.cliente_id, 0),
            equipos_resumen=equipos_por_cliente.get(o.cliente_id, []),
        ))

    return {
        "items": items,
        "fecha": str(target_date),
        "total": len(items),
        "empresa": AgendaEmpresaOut(
            nombre=empresa.nombre_comercial or empresa.nombre,
            color=empresa.color_empresa or "#0a5c91",
        ),
    }


def _empresa_y_orden_por_token(db: Session, agenda_token: str, orden_id: UUID):
    """Valida el token de agenda y que la orden pertenezca a esa empresa."""
    from app.models.orden_servicio import OrdenServicio
    from app.models.empresa import Empresa

    empresa = db.query(Empresa).filter(Empresa.agenda_token == agenda_token).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Enlace de agenda inválido")
    orden = (
        db.query(OrdenServicio)
        .filter(OrdenServicio.id == orden_id, OrdenServicio.empresa_id == empresa.id)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return empresa, orden


@router.get("/agenda/ordenes/{orden_id}/croquis", response_model=list[CroquisPublicoOut])
def croquis_publicos_orden(
    orden_id: UUID,
    agenda_token: str,
    db: Session = Depends(get_db),
):
    """Croquis del cliente de la orden (sin auth, gated por el token de agenda)."""
    from app.models.croquis import Croquis

    empresa, orden = _empresa_y_orden_por_token(db, agenda_token, orden_id)
    if not orden.cliente_id:
        return []
    rows = (
        db.query(Croquis)
        .filter(Croquis.empresa_id == empresa.id, Croquis.cliente_id == orden.cliente_id)
        .order_by(Croquis.creado_en.desc())
        .all()
    )
    return [
        CroquisPublicoOut(id=str(c.id), titulo=c.titulo, area=c.area, descripcion=c.descripcion)
        for c in rows
    ]


@router.get("/agenda/ordenes/{orden_id}/croquis/{croquis_id}/archivo")
def descargar_croquis_publico(
    orden_id: UUID,
    croquis_id: UUID,
    agenda_token: str,
    db: Session = Depends(get_db),
):
    """Descarga/visualización del archivo de un croquis (gated por token de agenda)."""
    import mimetypes
    from app.models.croquis import Croquis

    empresa, orden = _empresa_y_orden_por_token(db, agenda_token, orden_id)
    croq = (
        db.query(Croquis)
        .filter(
            Croquis.id == croquis_id,
            Croquis.empresa_id == empresa.id,
            Croquis.cliente_id == orden.cliente_id,
        )
        .first()
    )
    if not croq:
        raise HTTPException(status_code=404, detail="Croquis no encontrado")

    resolved = _safe_path(_CROQUIS_DIR, croq.archivo)
    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    mime, _ = mimetypes.guess_type(resolved)
    return FileResponse(
        resolved,
        media_type=mime or "application/octet-stream",
        filename=f"{croq.titulo}{os.path.splitext(croq.archivo)[1]}",
    )


class VerificacionOut(BaseModel):
    id: str
    nombre_completo: str
    tipo_personal: str
    area: str | None
    puesto: str | None
    activo: bool
    empresa_nombre: str
    # empresa_id eliminado — no es necesario para verificación y reducía la superficie de ataque
    empresa_color: str


@router.get("/tecnicos/{tecnico_id}/verificar", response_model=VerificacionOut)
def verificar_tecnico(tecnico_id: UUID, db: Session = Depends(get_db)):
    """Devuelve datos públicos de verificación del técnico (sin auth).
    Solo responde para técnicos activos — los dados de baja devuelven 404.
    """
    from app.models.tecnico import Tecnico
    tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    # VULN-006: ex-empleados no deben ser verificables
    if not tecnico.activo:
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
        empresa_color=empresa.color_empresa or "#1a6b3a",
    )


@router.get("/tecnicos/{tecnico_id}/logo-empresa")
def logo_empresa_via_tecnico(tecnico_id: UUID, db: Session = Depends(get_db)):
    """Logo de la empresa del técnico — evita exponer empresa_id en la respuesta de /verificar."""
    from app.models.tecnico import Tecnico
    tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id, Tecnico.activo == True).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    path = os.path.join(_LOGOS_DIR, f"{tecnico.empresa_id}.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    return FileResponse(path, media_type="image/png")


@router.get("/tecnicos/{tecnico_id}/foto")
def foto_publica_tecnico(tecnico_id: UUID, db: Session = Depends(get_db)):
    """Devuelve la foto del técnico sin autenticación (para verificación pública)."""
    from app.models.tecnico import Tecnico
    tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not tecnico or not tecnico.foto:
        raise HTTPException(status_code=404, detail="Sin foto")
    path = _safe_path(_TECNICOS_FOTOS_DIR, tecnico.foto)
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
