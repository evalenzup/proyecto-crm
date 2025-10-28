import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import os
from pydantic import BaseModel

from app.database import get_db
from app.schemas.egreso import Egreso, EgresoCreate, EgresoUpdate
from app.models.egreso import CategoriaEgreso, EstatusEgreso
from app.config import settings
from app.services.egreso_service import egreso_repo

router = APIRouter()

class EgresoPageOut(BaseModel):
    items: List[Egreso]
    total: int
    limit: int
    offset: int

@router.post("/upload-documento/", response_model=dict)
async def upload_documento(file: UploadFile = File(...)):
    try:
        upload_dir = os.path.join(settings.DATA_DIR, "egresos")
        os.makedirs(upload_dir, exist_ok=True)
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        return {"path_documento": os.path.join("egresos", unique_filename)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el archivo: {e}")

@router.get("/enums", response_model=dict)
def get_egreso_enums():
    return {
        "categorias": [e.value for e in CategoriaEgreso],
        "estatus": [e.value for e in EstatusEgreso],
    }

@router.post("/", response_model=Egreso, status_code=201)
def create_egreso(egreso: EgresoCreate, db: Session = Depends(get_db)):
    return egreso_repo.create(db, obj_in=egreso)

@router.get("/", response_model=EgresoPageOut)
def read_egresos(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    empresa_id: Optional[uuid.UUID] = None,
    proveedor: Optional[str] = None,
    categoria: Optional[str] = None,
    estatus: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
):
    items, total = egreso_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        empresa_id=empresa_id,
        proveedor=proveedor,
        categoria=categoria,
        estatus=estatus,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return {"items": items, "total": total, "limit": limit, "offset": skip}

@router.get("/{egreso_id}", response_model=Egreso)
def read_egreso(egreso_id: uuid.UUID, db: Session = Depends(get_db)):
    db_egreso = egreso_repo.get(db, id=egreso_id)
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    return db_egreso

@router.put("/{egreso_id}", response_model=Egreso)
def update_egreso(
    egreso_id: uuid.UUID, egreso: EgresoUpdate, db: Session = Depends(get_db)
):
    db_egreso = egreso_repo.get(db, id=egreso_id)
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    return egreso_repo.update(db, db_obj=db_egreso, obj_in=egreso)

@router.delete("/{egreso_id}", status_code=204)
def delete_egreso(egreso_id: uuid.UUID, db: Session = Depends(get_db)):
    db_egreso = egreso_repo.remove(db, id=egreso_id)
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    return