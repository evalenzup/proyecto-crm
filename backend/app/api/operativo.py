# app/api/operativo.py
"""
Routers Sprint 6 — Catálogos Operativos:
  /api/servicios-operativos
  /api/tecnicos
  /api/unidades   (incluye sub-recurso /api/unidades/{id}/mantenimientos)
"""
from __future__ import annotations

import os
import uuid as _uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.config import settings
from app.database import get_db
from app.models.poliza_seguro import PolizaSeguro
from app.models.usuario import RolUsuario, Usuario
from app.schemas.servicio_operativo import (
    ServicioOperativoCreate,
    ServicioOperativoOut,
    ServicioOperativoPageOut,
    ServicioOperativoUpdate,
)
from app.schemas.tecnico import TecnicoCreate, TecnicoOut, TecnicoPageOut, TecnicoUpdate
from app.schemas.unidad import (
    UnidadCreate,
    UnidadOut,
    UnidadPageOut,
    UnidadUpdate,
    PolizaSeguroCreate,
    PolizaSeguroOut,
    PolizaSeguroUpdate,
)
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
from app.services.credencial_service import generar_credencial_pdf

# Directorios de archivos
_FOTOS_DIR = os.path.join(settings.DATA_DIR, "unidades_fotos")
_DOCS_DIR = os.path.join(settings.DATA_DIR, "unidades_docs")


_MAX_UPLOAD_BYTES = 10 * 1024 * 1024          # 10 MB
_ALLOWED_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
_ALLOWED_DOC_EXTS   = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".webp"})


def _save_upload(
    file: UploadFile,
    directory: str,
    allowed_extensions: frozenset = _ALLOWED_DOC_EXTS,
) -> str:
    """
    Guarda un UploadFile en el directorio indicado y devuelve el nombre relativo.
    Valida extensión y tamaño máximo (10 MB) antes de escribir a disco.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if not ext or ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Extensiones válidas: {', '.join(sorted(allowed_extensions))}",
        )
    content = file.file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo supera el tamaño máximo de {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    os.makedirs(directory, exist_ok=True)
    filename = f"{_uuid.uuid4()}{ext}"
    dest = os.path.join(directory, filename)
    with open(dest, "wb") as fh:
        fh.write(content)
    return filename


def _delete_file(directory: str, filename: Optional[str]) -> None:
    if not filename:
        return
    path = os.path.join(directory, filename)
    if os.path.exists(path):
        os.remove(path)

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

_TECNICOS_FOTOS_DIR = os.path.join(settings.DATA_DIR, "tecnicos_fotos")


@tecnicos_router.get("", response_model=TecnicoPageOut)
def listar_tecnicos(
    empresa_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    tipo_personal: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    items, total = svc_tecnico.list_tecnicos(
        db, empresa_id=empresa_id, q=q, activo=activo,
        tipo_personal=tipo_personal, limit=limit, offset=offset
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


@tecnicos_router.post("/{tecnico_id}/foto", response_model=TecnicoOut)
async def subir_foto_tecnico(
    tecnico_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Sube o reemplaza la foto del personal."""
    tecnico = svc_tecnico.get_tecnico(db, tecnico_id)
    _delete_file(_TECNICOS_FOTOS_DIR, tecnico.foto)
    filename = _save_upload(file, _TECNICOS_FOTOS_DIR, _ALLOWED_IMAGE_EXTS)
    tecnico.foto = filename
    db.commit()
    db.refresh(tecnico)
    return tecnico


@tecnicos_router.get("/{tecnico_id}/credencial")
def descargar_credencial(
    tecnico_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Genera y devuelve la credencial PDF del empleado."""
    tecnico = svc_tecnico.get_tecnico(db, tecnico_id)
    empresa = tecnico.empresa

    qr_data = f"{settings.APP_URL}/verificar/{tecnico_id}"

    pdf_bytes = generar_credencial_pdf(
        tecnico_id=tecnico_id,
        nombre=tecnico.nombre or "",
        primer_apellido=tecnico.primer_apellido or "",
        segundo_apellido=tecnico.segundo_apellido,
        curp=tecnico.curp,
        numero_trabajador=tecnico.numero_trabajador,
        tipo_personal=tecnico.tipo_personal,
        puesto=tecnico.puesto,
        tipo_sangre=tecnico.tipo_sangre,
        foto_filename=tecnico.foto,
        empresa_id=empresa.id,
        empresa_nombre=empresa.nombre_comercial or empresa.nombre,
        empresa_rfc=empresa.rfc,
        qr_data=qr_data,
        color_hex=empresa.color_credencial or "#1a6b3a",
        nss=tecnico.nss,
        rfc_personal=tecnico.rfc,
        area=tecnico.area,
        empresa_telefono=empresa.telefono,
        tecnico_direccion=tecnico.direccion,
    )

    nombre_archivo = f"credencial_{(tecnico.nombre_completo or 'empleado').replace(' ', '_').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@tecnicos_router.get("/{tecnico_id}/foto")
def obtener_foto_tecnico(
    tecnico_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Devuelve la foto del técnico como archivo (autenticado)."""
    tecnico = svc_tecnico.get_tecnico(db, tecnico_id)
    if not tecnico.foto:
        raise HTTPException(status_code=404, detail="Sin foto")
    path = os.path.join(_TECNICOS_FOTOS_DIR, tecnico.foto)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="image/jpeg")


@tecnicos_router.delete("/{tecnico_id}/foto", status_code=204)
def eliminar_foto_tecnico(
    tecnico_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    tecnico = svc_tecnico.get_tecnico(db, tecnico_id)
    _delete_file(_TECNICOS_FOTOS_DIR, tecnico.foto)
    tecnico.foto = None
    db.commit()


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


# ════════════════════════════════════════════════════════════════════════════
# Unidad — Fotos y documentos (upload)
# ════════════════════════════════════════════════════════════════════════════

@unidades_router.post("/{unidad_id}/fotos/{campo}", response_model=UnidadOut)
async def subir_foto_unidad(
    unidad_id: UUID,
    campo: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """
    Sube una foto de la unidad. campo puede ser: foto_frontal | foto_lateral | foto_placa
    """
    campos_validos = {"foto_frontal", "foto_lateral", "foto_placa"}
    if campo not in campos_validos:
        raise HTTPException(status_code=400, detail=f"Campo inválido. Use: {campos_validos}")

    unidad = svc_unidad.get_unidad(db, unidad_id)
    # Borrar foto anterior si existe
    _delete_file(_FOTOS_DIR, getattr(unidad, campo))
    filename = _save_upload(file, _FOTOS_DIR, _ALLOWED_IMAGE_EXTS)
    setattr(unidad, campo, filename)
    db.commit()
    db.refresh(unidad)
    return unidad


@unidades_router.get("/{unidad_id}/fotos/{campo}")
def obtener_foto_unidad(
    unidad_id: UUID,
    campo: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Devuelve una foto de la unidad como archivo (autenticado)."""
    campos_validos = {"foto_frontal", "foto_lateral", "foto_placa"}
    if campo not in campos_validos:
        raise HTTPException(status_code=400, detail=f"Campo inválido. Use: {campos_validos}")
    unidad = svc_unidad.get_unidad(db, unidad_id)
    filename = getattr(unidad, campo)
    if not filename:
        raise HTTPException(status_code=404, detail="Sin foto")
    path = os.path.join(_FOTOS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="image/jpeg")


@unidades_router.delete("/{unidad_id}/fotos/{campo}", status_code=204)
def eliminar_foto_unidad(
    unidad_id: UUID,
    campo: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    campos_validos = {"foto_frontal", "foto_lateral", "foto_placa"}
    if campo not in campos_validos:
        raise HTTPException(status_code=400, detail=f"Campo inválido. Use: {campos_validos}")

    unidad = svc_unidad.get_unidad(db, unidad_id)
    _delete_file(_FOTOS_DIR, getattr(unidad, campo))
    setattr(unidad, campo, None)
    db.commit()


@unidades_router.post("/{unidad_id}/doc-tarjeta-circulacion", response_model=UnidadOut)
async def subir_doc_tarjeta_circulacion(
    unidad_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Sube el documento de la tarjeta de circulación."""
    unidad = svc_unidad.get_unidad(db, unidad_id)
    _delete_file(_DOCS_DIR, unidad.doc_tarjeta_circulacion)
    filename = _save_upload(file, _DOCS_DIR)
    unidad.doc_tarjeta_circulacion = filename
    db.commit()
    db.refresh(unidad)
    return unidad


@unidades_router.delete("/{unidad_id}/doc-tarjeta-circulacion", status_code=204)
def eliminar_doc_tarjeta_circulacion(
    unidad_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    unidad = svc_unidad.get_unidad(db, unidad_id)
    _delete_file(_DOCS_DIR, unidad.doc_tarjeta_circulacion)
    unidad.doc_tarjeta_circulacion = None
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# Unidad — Pólizas de Seguro
# ════════════════════════════════════════════════════════════════════════════

def _get_poliza(db: Session, unidad_id: UUID, poliza_id: UUID) -> PolizaSeguro:
    obj = (
        db.query(PolizaSeguro)
        .filter(PolizaSeguro.id == poliza_id, PolizaSeguro.unidad_id == unidad_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Póliza de seguro no encontrada.")
    return obj


@unidades_router.post("/{unidad_id}/polizas-seguro", response_model=PolizaSeguroOut, status_code=201)
def crear_poliza_seguro(
    unidad_id: UUID,
    data: PolizaSeguroCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    svc_unidad.get_unidad(db, unidad_id)  # verifica que la unidad existe
    obj = PolizaSeguro(unidad_id=unidad_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@unidades_router.put("/{unidad_id}/polizas-seguro/{poliza_id}", response_model=PolizaSeguroOut)
def actualizar_poliza_seguro(
    unidad_id: UUID,
    poliza_id: UUID,
    data: PolizaSeguroUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_poliza(db, unidad_id, poliza_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@unidades_router.delete("/{unidad_id}/polizas-seguro/{poliza_id}", status_code=204)
def eliminar_poliza_seguro(
    unidad_id: UUID,
    poliza_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_poliza(db, unidad_id, poliza_id)
    # Borrar documento adjunto si existe
    _delete_file(_DOCS_DIR, obj.documento)
    db.delete(obj)
    db.commit()


@unidades_router.post(
    "/{unidad_id}/polizas-seguro/{poliza_id}/documento",
    response_model=PolizaSeguroOut,
)
async def subir_documento_poliza(
    unidad_id: UUID,
    poliza_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Sube el documento PDF/imagen de una póliza de seguro."""
    obj = _get_poliza(db, unidad_id, poliza_id)
    _delete_file(_DOCS_DIR, obj.documento)
    filename = _save_upload(file, _DOCS_DIR)
    obj.documento = filename
    db.commit()
    db.refresh(obj)
    return obj


@unidades_router.delete(
    "/{unidad_id}/polizas-seguro/{poliza_id}/documento",
    status_code=204,
)
def eliminar_documento_poliza(
    unidad_id: UUID,
    poliza_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_poliza(db, unidad_id, poliza_id)
    _delete_file(_DOCS_DIR, obj.documento)
    obj.documento = None
    db.commit()
