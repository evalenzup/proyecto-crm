import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import os

from app.database import get_db
from app.schemas.egreso import Egreso, EgresoCreate, EgresoUpdate
from app.models.egreso import Egreso as EgresoModel, CategoriaEgreso, EstatusEgreso
from app.config import settings # Importar settings

router = APIRouter()

@router.post("/upload-documento/", response_model=dict)
async def upload_documento(file: UploadFile = File(...)):
    try:
        # Construir ruta de subida dinámicamente desde la configuración
        upload_dir = os.path.join(settings.DATA_DIR, "egresos")
        os.makedirs(upload_dir, exist_ok=True)

        # Generar un nombre de archivo único
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Guardar el archivo
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        return {"path_documento": file_path}
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
    db_egreso = EgresoModel(**egreso.model_dump())
    db.add(db_egreso)
    db.commit()
    db.refresh(db_egreso)
    return db_egreso

@router.get("/", response_model=List[Egreso])
def read_egresos(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    empresa_id: Optional[uuid.UUID] = None,
    proveedor: Optional[str] = None,
    categoria: Optional[str] = None,
    estatus: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
):
    query = db.query(EgresoModel)
    if empresa_id:
        query = query.filter(EgresoModel.empresa_id == empresa_id)
    if proveedor:
        query = query.filter(EgresoModel.proveedor.ilike(f"%{proveedor}%"))
    if categoria:
        query = query.filter(EgresoModel.categoria == categoria)
    if estatus:
        query = query.filter(EgresoModel.estatus == estatus)
    if fecha_desde:
        query = query.filter(EgresoModel.fecha_egreso >= fecha_desde)
    if fecha_hasta:
        query = query.filter(EgresoModel.fecha_egreso <= fecha_hasta)
        
    egresos = query.offset(skip).limit(limit).all()
    return egresos

@router.get("/{egreso_id}", response_model=Egreso)
def read_egreso(egreso_id: uuid.UUID, db: Session = Depends(get_db)):
    db_egreso = db.query(EgresoModel).filter(EgresoModel.id == egreso_id).first()
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    return db_egreso

@router.put("/{egreso_id}", response_model=Egreso)
def update_egreso(egreso_id: uuid.UUID, egreso: EgresoUpdate, db: Session = Depends(get_db)):
    db_egreso = db.query(EgresoModel).filter(EgresoModel.id == egreso_id).first()
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    
    update_data = egreso.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_egreso, key, value)
    
    db.commit()
    db.refresh(db_egreso)
    return db_egreso

@router.delete("/{egreso_id}", response_model=Egreso)
def delete_egreso(egreso_id: uuid.UUID, db: Session = Depends(get_db)):
    db_egreso = db.query(EgresoModel).filter(EgresoModel.id == egreso_id).first()
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    
    db.delete(db_egreso)
    db.commit()
    return db_egreso
