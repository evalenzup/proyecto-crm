# app/api/contratos.py
"""Router de Contratos: CRUD, precarga (mixta desde presupuesto), generación y descarga."""
from __future__ import annotations

import os
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.config import settings
from app.database import get_db
from app.models.usuario import Usuario, RolUsuario
from app.models.contrato import Contrato
from app.models.cliente import Cliente
from app.models.presupuestos import Presupuesto
from app.models.tecnico import Tecnico
from app.schemas.contrato import ContratoCreate, ContratoUpdate, ContratoOut
from app.services import contrato_service
from app.services import auditoria_service as audit_svc

router = APIRouter()

_CONTRATOS_DIR = os.path.join(settings.DATA_DIR, "contratos")


def _get_or_404(db: Session, contrato_id: UUID) -> Contrato:
    obj = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return obj


@router.get("/precarga", response_model=dict)
def precarga_contrato(
    cliente_id: UUID,
    presupuesto_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    """Sugiere valores iniciales: empresa del cliente, técnicos disponibles y,
    si se pasa un presupuesto, su total como precio combo."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    empresa_id = cliente.empresas[0].id if cliente.empresas else None
    servicios = {}
    if presupuesto_id:
        pres = db.query(Presupuesto).filter(Presupuesto.id == presupuesto_id).first()
        if pres:
            servicios = {"combo": float(pres.total or 0)}
            if not empresa_id:
                empresa_id = pres.empresa_id

    tecnicos = []
    if empresa_id:
        for t in db.query(Tecnico).filter(Tecnico.empresa_id == empresa_id, Tecnico.activo == True).all():
            tecnicos.append({"id": str(t.id), "nombre": t.nombre_completo, "puesto": t.puesto})

    return {
        "empresa_id": str(empresa_id) if empresa_id else None,
        "servicios": servicios,
        "tecnicos_disponibles": tecnicos,
    }


@router.get("", response_model=List[ContratoOut])
def listar_contratos(
    cliente_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    q = db.query(Contrato)
    if cliente_id:
        q = q.filter(Contrato.cliente_id == cliente_id)
    return q.order_by(Contrato.creado_en.desc()).all()


@router.post("", response_model=ContratoOut, status_code=201)
def crear_contrato(
    data: ContratoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    payload = data.model_dump()
    payload["personal_asignado"] = [str(t) for t in (payload.get("personal_asignado") or [])]
    payload["empresa_id"] = data.empresa_id
    payload["cliente_id"] = data.cliente_id
    obj = Contrato(**payload)
    db.add(obj)
    db.flush()
    audit_svc.registrar(
        db=db, accion="CREAR_CONTRATO", entidad="contrato",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=data.empresa_id, entidad_id=str(obj.id),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{contrato_id}", response_model=ContratoOut)
def obtener_contrato(
    contrato_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return _get_or_404(db, contrato_id)


@router.put("/{contrato_id}", response_model=ContratoOut)
def actualizar_contrato(
    contrato_id: UUID,
    data: ContratoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_or_404(db, contrato_id)
    update = data.model_dump(exclude_unset=True)
    if "personal_asignado" in update and update["personal_asignado"] is not None:
        update["personal_asignado"] = [str(t) for t in update["personal_asignado"]]
    for field, value in update.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{contrato_id}", status_code=204)
def eliminar_contrato(
    contrato_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_or_404(db, contrato_id)
    for attr in ("archivo_docx", "archivo_pdf"):
        fn = getattr(obj, attr, None)
        if fn:
            path = os.path.join(_CONTRATOS_DIR, fn)
            if os.path.exists(path):
                os.remove(path)
    db.delete(obj)
    db.commit()


@router.post("/{contrato_id}/generar", response_model=ContratoOut)
def generar_contrato(
    contrato_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_or_404(db, contrato_id)
    try:
        contrato_service.generar_documento(db, obj)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar el contrato: {e}")
    audit_svc.registrar(
        db=db, accion="GENERAR_CONTRATO", entidad="contrato",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(obj.id),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{contrato_id}/documento")
def descargar_contrato(
    contrato_id: UUID,
    fmt: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = _get_or_404(db, contrato_id)
    filename = obj.archivo_pdf if fmt == "pdf" else obj.archivo_docx
    if not filename:
        raise HTTPException(status_code=404, detail="El contrato no tiene documento generado")

    base = os.path.realpath(_CONTRATOS_DIR)
    resolved = os.path.realpath(os.path.join(base, filename))
    if not resolved.startswith(base + os.sep) or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    media = "application/pdf" if fmt == "pdf" else (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(resolved, media_type=media, filename=f"contrato_{contrato_id}.{fmt}")
