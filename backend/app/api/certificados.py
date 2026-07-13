# app/api/certificados.py
"""Certificados de servicio (Aplicación de Plaguicidas)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import get_db
from app.models.certificado_servicio import CertificadoServicio
from app.models.empresa import Empresa
from app.models.usuario import Usuario, RolUsuario
from app.schemas.certificado_servicio import (
    CertificadoServicioCreate,
    CertificadoServicioOut,
    CertificadoServicioPageOut,
    CertificadoServicioUpdate,
)
from app.services import auditoria_service as audit_svc
from app.services import certificado_servicio_service as svc

router = APIRouter()


def _get_empresa(db: Session, empresa_id: UUID) -> Empresa:
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return emp


@router.get("", response_model=CertificadoServicioPageOut)
def listar_certificados(
    empresa_id: Optional[UUID] = Query(None),
    tipo: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: Optional[str] = Query(None),
    order_dir: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    items, total = svc.list_certificados(
        db, empresa_id=empresa_id, tipo=tipo, q=q,
        limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
    )
    return CertificadoServicioPageOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/siguiente-folio")
def siguiente_folio(
    empresa_id: UUID = Query(...),
    tipo: str = Query("PLAGUICIDAS"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return {"folio": svc.siguiente_folio(db, empresa_id, tipo.upper())}


@router.post("", response_model=CertificadoServicioOut, status_code=201)
def crear_certificado(
    request: Request,
    data: CertificadoServicioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa = _get_empresa(db, data.empresa_id)
    svc.validar_empresa_permitida(empresa, data.tipo)

    obj = CertificadoServicio(**data.model_dump(exclude={"folio"}))
    obj.tipo = data.tipo.upper()
    if data.folio:
        # Folio manual (para continuar la numeración que llevan en papel)
        existe = (
            db.query(CertificadoServicio)
            .filter(
                CertificadoServicio.empresa_id == data.empresa_id,
                CertificadoServicio.tipo == obj.tipo,
                CertificadoServicio.folio == data.folio,
            )
            .first()
        )
        if existe:
            raise HTTPException(status_code=409, detail=f"El folio {data.folio} ya existe.")
        obj.folio = data.folio
    else:
        obj.folio = svc.siguiente_folio(db, data.empresa_id, obj.tipo)
    db.add(obj)
    db.flush()
    audit_svc.registrar(
        db=db, accion="CREAR_CERTIFICADO", entidad="certificado_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(obj.id),
        ip=audit_svc.get_ip(request),
        detalle={"tipo": obj.tipo, "folio": obj.folio, "establecimiento": obj.nombre_razon_social},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{cert_id}", response_model=CertificadoServicioOut)
def obtener_certificado(
    cert_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    return svc.get_certificado(db, cert_id)


@router.put("/{cert_id}", response_model=CertificadoServicioOut)
def actualizar_certificado(
    cert_id: UUID,
    request: Request,
    data: CertificadoServicioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_certificado(db, cert_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    audit_svc.registrar(
        db=db, accion="ACTUALIZAR_CERTIFICADO", entidad="certificado_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(cert_id),
        ip=audit_svc.get_ip(request),
        detalle={"tipo": obj.tipo, "folio": obj.folio},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{cert_id}", status_code=204)
def eliminar_certificado(
    cert_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_certificado(db, cert_id)
    audit_svc.registrar(
        db=db, accion="ELIMINAR_CERTIFICADO", entidad="certificado_servicio",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=obj.empresa_id, entidad_id=str(cert_id),
        ip=audit_svc.get_ip(request),
        detalle={"tipo": obj.tipo, "folio": obj.folio},
    )
    db.delete(obj)
    db.commit()


@router.get("/{cert_id}/pdf")
def descargar_pdf(
    cert_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    obj = svc.get_certificado(db, cert_id)
    pdf = svc.generar_pdf(obj)
    filename = f"certificado_{obj.tipo.lower()}_{obj.folio}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
