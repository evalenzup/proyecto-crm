from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.api import deps
from app.models.usuario import Usuario, RolUsuario
from app.schemas.cobranza import AgingReportResponse, CobranzaNotaCreate, CobranzaNotaOut, CobranzaEmailRequest
from app.services.cobranza_service import cobranza_service
from app.services.pdf_estado_cuenta import generate_account_statement_pdf

router = APIRouter()

@router.get("/aging", response_model=AgingReportResponse)
def get_aging_report(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: UUID = Query(None),
    rfc: Optional[str] = Query(None),
):
    """
    Obtiene el reporte de antigüedad de saldos.
    Acepta empresa_id individual o rfc para agrupar múltiples empresas.
    """
    _ADMIN = (RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

    # Roles no-admin: siempre su propia empresa
    if current_user.rol not in _ADMIN:
        if not current_user.empresa_id:
            raise HTTPException(status_code=400, detail="Usuario sin empresa asignada.")
        return cobranza_service.get_aging_report(db, empresa_ids=[current_user.empresa_id])

    # Admin/Superadmin con rfc → todas las empresas de ese RFC
    if rfc:
        from app.models.empresa import Empresa as EmpresaModel
        ids = [r.id for r in db.query(EmpresaModel.id).filter(EmpresaModel.rfc == rfc.upper()).all()]
        if not ids:
            raise HTTPException(status_code=404, detail=f"No se encontraron empresas con RFC {rfc}.")
        return cobranza_service.get_aging_report(db, empresa_ids=ids)

    # Admin/Superadmin con empresa_id individual
    effective = empresa_id or current_user.empresa_id
    if not effective:
        raise HTTPException(status_code=400, detail="Se requiere empresa_id o rfc.")
    return cobranza_service.get_aging_report(db, empresa_ids=[effective])

@router.post("/notas", response_model=CobranzaNotaOut)
def crear_nota_cobranza(
    payload: CobranzaNotaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: UUID = Query(None),
):
    effective_empresa_id = None

    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="Usuario supervisor sin empresa.")
        effective_empresa_id = current_user.empresa_id
    else:
        effective_empresa_id = empresa_id or current_user.empresa_id

    if not effective_empresa_id:
         raise HTTPException(status_code=400, detail="Se requiere contexto de empresa (empresa_id).")
    
    return cobranza_service.create_nota(db, payload, current_user.id, effective_empresa_id)

@router.get("/notas/{cliente_id}", response_model=List[CobranzaNotaOut])
def listar_notas_cliente(
    cliente_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: UUID = Query(None),
):
    effective_empresa_id = None

    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="Usuario supervisor sin empresa.")
        effective_empresa_id = current_user.empresa_id
    else:
        effective_empresa_id = empresa_id or current_user.empresa_id

    if not effective_empresa_id:
         raise HTTPException(status_code=400, detail="Se requiere contexto de empresa (empresa_id).")

    return cobranza_service.get_notas_by_cliente(db, cliente_id, effective_empresa_id)

@router.get("/estado-cuenta/{cliente_id}")
def descargar_estado_cuenta(
    cliente_id: UUID,
    empresa_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    effective_empresa_id = None
    
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="Usuario supervisor sin empresa.")
        effective_empresa_id = current_user.empresa_id
    else:
        effective_empresa_id = empresa_id or current_user.empresa_id
        
    if not effective_empresa_id:
         raise HTTPException(status_code=400, detail="Se requiere contexto de empresa (empresa_id) para generar estado de cuenta.")
    
    pdf_buffer = generate_account_statement_pdf(db, effective_empresa_id, cliente_id)
    
    filename = f"estado_cuenta_{cliente_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/enviar-estado-cuenta", status_code=202)
def enviar_estado_cuenta(
    payload: CobranzaEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: UUID = Query(None),
):
    effective_empresa_id = None
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="Usuario supervisor sin empresa.")
        effective_empresa_id = current_user.empresa_id
    else:
        effective_empresa_id = empresa_id or current_user.empresa_id

    if not effective_empresa_id:
         raise HTTPException(status_code=400, detail="Se requiere contexto de empresa (empresa_id).")

    background_tasks.add_task(
        cobranza_service.process_email_estado_cuenta,
        db,
        effective_empresa_id,
        payload.cliente_id,
        payload.recipients,
        current_user.id,
    )
    return {"message": f"Estado de cuenta programado para envío a: {', '.join(payload.recipients)}"}

@router.delete("/notas/{nota_id}")
def eliminar_nota(
    nota_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: UUID = Query(None),
):
    try:
        is_admin = current_user.rol in (RolUsuario.ADMIN, RolUsuario.SUPERADMIN)
        success = cobranza_service.delete_nota(db, nota_id, current_user.id, is_admin)
        if not success:
            raise HTTPException(status_code=404, detail="Nota no encontrada")
        return {"message": "Nota eliminada correctamente"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
