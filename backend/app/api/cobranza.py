from fastapi import APIRouter, Depends, HTTPException, Query
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
):
    """
    Obtiene el reporte de antigüedad de saldos.
    """
    effective_empresa_id = None

    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="Usuario supervisor sin empresa.")
        effective_empresa_id = current_user.empresa_id
    else:
        # Si es Admin, preferimos el query param, sino el del usuario
        effective_empresa_id = empresa_id or current_user.empresa_id

    if not effective_empresa_id:
         raise HTTPException(status_code=400, detail="Se requiere contexto de empresa.")

    return cobranza_service.get_aging_report(db, effective_empresa_id)

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

@router.post("/enviar-estado-cuenta")
def enviar_estado_cuenta(
    payload: CobranzaEmailRequest,
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
         
    try:
        cobranza_service.process_email_estado_cuenta(
            db, 
            effective_empresa_id, 
            payload.cliente_id, 
            payload.recipients, 
            current_user.id
        )
        return {"message": "Correo enviado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/notas/{nota_id}")
def eliminar_nota(
    nota_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
    empresa_id: UUID = Query(None),
):
    try:
        is_admin = current_user.rol == RolUsuario.ADMIN
        success = cobranza_service.delete_nota(db, nota_id, current_user.id, is_admin)
        if not success:
            raise HTTPException(status_code=404, detail="Nota no encontrada")
        return {"message": "Nota eliminada correctamente"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
