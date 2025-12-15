import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import os
from pydantic import BaseModel

from app.utils.excel import generate_excel

from app.database import get_db
from app.schemas.egreso import Egreso, EgresoCreate, EgresoUpdate
from app.models.egreso import CategoriaEgreso, EstatusEgreso
from app.config import settings
from app.services.egreso_service import egreso_repo
from app.models.usuario import Usuario, RolUsuario
from app.api import deps
# Catálogos
from app.catalogos_sat.facturacion import FORMA_PAGO

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
def create_egreso(
    egreso: EgresoCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        if not current_user.empresa_id:
             raise HTTPException(status_code=400, detail="El usuario supervisor no tiene empresa asignada.")
        egreso.empresa_id = current_user.empresa_id
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
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

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

@router.get("/busqueda-proveedores", response_model=List[str])
def search_proveedores_endpoint(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    empresa_id = None
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id
    elif current_user.rol == RolUsuario.ADMIN:
         # Admin can search all or filter? For now search all unique providers or maybe current contest?
         # Usually filtering by company is best for UX
         pass
    
    # Actually, let's respect the current context if passed? 
    # But usually frontend passes empresa_id if admin. 
    # For simplicity, let's return global if admin, or scoped if supervisor.
    return egreso_repo.search_proveedores(db, mpresa_id=empresa_id, q=q)


@router.get("/export-excel")
def exportar_egresos_excel(
    db: Session = Depends(get_db),
    empresa_id: Optional[uuid.UUID] = Query(None),
    proveedor: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    estatus: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    if current_user.rol == RolUsuario.SUPERVISOR:
        empresa_id = current_user.empresa_id

    items, _ = egreso_repo.get_multi(
        db,
        skip=0,
        limit=5000,
        empresa_id=empresa_id,
        proveedor=proveedor,
        categoria=categoria,
        estatus=estatus,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    # Nota: En Egresos, el campo 'metodo_pago' suele guardar claves de 'Forma de Pago' (example: 03, 01)
    # por lo que usamos FORMA_PAGO para obtener la descripción.
    map_formas = {i["clave"]: i["descripcion"] for i in FORMA_PAGO}

    data_list = []
    for e in items:
        # Metodo pago desc (usando catálogo de formas)
        metodo_desc = e.metodo_pago
        if e.metodo_pago and e.metodo_pago in map_formas:
            metodo_desc = f"{e.metodo_pago} - {map_formas[e.metodo_pago]}"

        # Clean Enums
        cat_str = e.categoria.value if hasattr(e.categoria, 'value') else str(e.categoria)
        # Si por alguna razón sigue saliendo CategoriaEgreso.X, hacemos split
        if "CategoriaEgreso." in cat_str:
             cat_str = cat_str.replace("CategoriaEgreso.", "")
             
        estatus_str = e.estatus.value if hasattr(e.estatus, 'value') else str(e.estatus)

        data_list.append({
            "fecha_egreso": e.fecha_egreso,
            "proveedor": e.proveedor,
            "descripcion": e.descripcion,
            "categoria": cat_str,
            "estatus": estatus_str,
            "metodo_pago": metodo_desc,
            "monto": e.monto,
            "moneda": e.moneda,
        })

    headers = {
        "fecha_egreso": "Fecha",
        "proveedor": "Proveedor",
        "descripcion": "Descripción",
        "categoria": "Categoría",
        "estatus": "Estatus",
        "metodo_pago": "Método de Pago",
        "monto": "Monto",
        "moneda": "Moneda",
    }

    excel_file = generate_excel(data_list, headers, sheet_name="Egresos")
    
    headers_resp = {
        "Content-Disposition": 'attachment; filename="egresos.xlsx"'
    }
    return StreamingResponse(excel_file, headers=headers_resp, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/{egreso_id}", response_model=Egreso)
def read_egreso(
    egreso_id: uuid.UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    db_egreso = egreso_repo.get(db, id=egreso_id)
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
        
    if current_user.rol == RolUsuario.SUPERVISOR and db_egreso.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Egreso not found")
        
    return db_egreso

@router.put("/{egreso_id}", response_model=Egreso)
def update_egreso(
    egreso_id: uuid.UUID, 
    egreso: EgresoUpdate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    db_egreso = egreso_repo.get(db, id=egreso_id)
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
        
    if current_user.rol == RolUsuario.SUPERVISOR:
        if db_egreso.empresa_id != current_user.empresa_id:
            raise HTTPException(status_code=404, detail="Egreso not found")

    return egreso_repo.update(db, db_obj=db_egreso, obj_in=egreso)

@router.delete("/{egreso_id}", status_code=204)
def delete_egreso(
    egreso_id: uuid.UUID, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.get_current_active_user),
):
    db_egreso = egreso_repo.get(db, id=egreso_id)
    if db_egreso is None:
         raise HTTPException(status_code=404, detail="Egreso not found")
         
    if current_user.rol == RolUsuario.SUPERVISOR and db_egreso.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Egreso not found")

    egreso_repo.remove(db, id=egreso_id)
    if db_egreso is None:
        raise HTTPException(status_code=404, detail="Egreso not found")
    return