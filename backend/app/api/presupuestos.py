# app/api/presupuestos.py

from fastapi import APIRouter, Depends, HTTPException, Path, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import io

from app.database import get_db
from app.schemas.presupuestos import (
    Presupuesto as PresupuestoOut,
    PresupuestoCreate,
    PresupuestoUpdate,
    PresupuestoSimpleOut,
    PresupuestoPageOut,
    StatusUpdatePayload,
)
from app.schemas.factura import FacturaOut
from app.services.presupuesto_service import presupuesto_repo
from app.services.pdf_generator import generate_presupuesto_pdf
from app.services.email_sender import send_presupuesto_email
from app.models.presupuestos import PresupuestoEvento
from pydantic import BaseModel, EmailStr

router = APIRouter()

class FolioOut(BaseModel):
    folio: str

class EmailSchema(BaseModel):
    recipient_email: EmailStr

@router.get("/siguiente-folio", response_model=FolioOut)
def obtener_siguiente_folio(
    empresa_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Sugiere el siguiente folio para un nuevo presupuesto para una empresa.
    """
    # La lógica para generar el folio ya está en el repositorio.
    # El guion bajo indica que es un método "privado", pero lo usaremos aquí
    # por pragmatismo para no duplicar código.
    folio = presupuesto_repo._generate_folio(db, empresa_id=empresa_id)
    return {"folio": folio}

@router.get("/", response_model=PresupuestoPageOut)
def listar_presupuestos(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    empresa_id: UUID = Query(None, description="Filtrar por empresa"),
    cliente_id: UUID = Query(None, description="Filtrar por cliente"),
    estado: str = Query(None, description="Filtrar por estado"),
    fecha_inicio: str = Query(None, description="Fecha de inicio para el rango de búsqueda"),
    fecha_fin: str = Query(None, description="Fecha de fin para el rango de búsqueda"),
):
    """
    Obtiene una lista paginada y filtrada de presupuestos.
    """
    items, total = presupuesto_repo.get_multi(
        db,
        skip=offset,
        limit=limit,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        estado=estado,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/", response_model=PresupuestoOut, status_code=201)
def crear_presupuesto(
    payload: PresupuestoCreate, 
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo presupuesto con sus detalles.
    """
    return presupuesto_repo.create(db, obj_in=payload)

@router.get("/{id}", response_model=PresupuestoOut)
def obtener_presupuesto(
    id: UUID = Path(...), 
    db: Session = Depends(get_db)
):
    """
    Obtiene un presupuesto por su ID.
    """
    presupuesto = presupuesto_repo.get(db, id=id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return presupuesto

@router.put("/{id}", response_model=PresupuestoOut)
def actualizar_presupuesto(
    id: UUID, 
    payload: PresupuestoUpdate, 
    db: Session = Depends(get_db)
):
    """
    Actualiza un presupuesto.
    """
    db_obj = presupuesto_repo.get(db, id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return presupuesto_repo.update(db, db_obj=db_obj, obj_in=payload)

@router.patch("/{id}/estado", response_model=PresupuestoOut)
def actualizar_estado_presupuesto(
    id: UUID,
    payload: StatusUpdatePayload,
    db: Session = Depends(get_db),
):
    """
    Actualiza el estado de un presupuesto sin crear una nueva versión.
    """
    db_obj = presupuesto_repo.get(db, id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    # Placeholder for user_id from token
    user_id = db_obj.responsable_id

    return presupuesto_repo.update_status(db, db_obj=db_obj, new_status=payload.estado, user_id=user_id)


@router.post("/{id}/evidencia", response_model=PresupuestoOut)
def subir_evidencia_presupuesto(
    id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Sube un archivo de evidencia para un presupuesto, lo cual también lo marca como ACEPTADO.
    """
    db_obj = presupuesto_repo.get(db, id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    user_id = db_obj.responsable_id

    return presupuesto_repo.add_evidencia(db, db_obj=db_obj, file=file, user_id=user_id)


@router.delete("/{id}", status_code=204)
def eliminar_presupuesto(id: UUID, db: Session = Depends(get_db)):
    """
    Elimina un presupuesto.
    """
    presupuesto = presupuesto_repo.remove(db, id=id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return

@router.get("/{id}/pdf", response_class=StreamingResponse)
def descargar_presupuesto_pdf(
    id: UUID = Path(...),
    db: Session = Depends(get_db)
):
    """
    Genera y descarga el presupuesto en formato PDF.
    """
    presupuesto = presupuesto_repo.get(db, id=id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    pdf_bytes = generate_presupuesto_pdf(presupuesto, db)
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=presupuesto_{presupuesto.folio}.pdf"}
    )

@router.post("/{id}/enviar", status_code=200)
def enviar_presupuesto_email(
    id: UUID,
    payload: EmailSchema,
    db: Session = Depends(get_db),
    # TODO: Get user from token
    # current_user: models.Usuario = Depends(get_current_user),
):
    """
    Envía el presupuesto por correo electrónico a un destinatario.
    """
    presupuesto = presupuesto_repo.get(db, id=id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    try:
        send_presupuesto_email(
            db,
            empresa_id=presupuesto.empresa_id,
            presupuesto_id=id,
            recipient_email=payload.recipient_email,
        )

        # Actualizar estado y registrar evento
        presupuesto.estado = "ENVIADO"
        evento = PresupuestoEvento(
            presupuesto_id=id,
            # TODO: Usar el ID del usuario autenticado
            usuario_id=presupuesto.responsable_id, # Placeholder
            accion="ENVIADO",
            comentario=f"Enviado a {payload.recipient_email}",
        )
        db.add(evento)
        db.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Presupuesto enviado con éxito"}

@router.get("/historial/{folio}", response_model=List[PresupuestoOut])
def obtener_historial_presupuesto(
    folio: str,
    empresa_id: UUID = Query(..., description="ID de la empresa a la que pertenece el presupuesto"),
    db: Session = Depends(get_db),
):
    """
    Obtiene el historial de versiones de un presupuesto por su folio.
    """
    historial = presupuesto_repo.get_history_by_folio(db, folio=folio, empresa_id=empresa_id)
    if not historial:
        raise HTTPException(status_code=404, detail="No se encontró historial para el folio especificado")
    return historial


@router.post("/{id}/convertir-a-factura", response_model=FacturaOut)
def convertir_a_factura(
    id: UUID,
    db: Session = Depends(get_db),
):
    """
    Convierte un presupuesto aceptado en una nueva factura en estado borrador.
    """
    factura_creada = presupuesto_repo.convertir_a_factura(db, presupuesto_id=id)
    return factura_creada
