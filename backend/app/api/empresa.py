import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Path, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaOut, EmpresaCreate, EmpresaUpdate
from app.catalogos_sat import obtener_todos_regimenes
from app.services import empresa_service
from app.config import settings

CERT_DIR = settings.CERT_DIR
# Intentamos crear carpeta, ignoramos errores de permisos
try:
    os.makedirs(CERT_DIR, exist_ok=True)
except Exception:
    pass

router = APIRouter()

@router.get(
    "/certificados/{filename}",
    summary="Descargar certificado .cert o .key",)
def descargar_certificado(filename: str = Path(..., regex=r"^[\w\-.]+$")):
    """
    Descarga los certificados .cert o .key
    """
    path = os.path.join(CERT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=filename)

@router.get(
    "/schema",
    summary="Obtener el schema del modelo")
def get_form_schema():
    """
    Devuelve el schema del modelo empresa
    """
    schema = EmpresaCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])
    regimenes = obtener_todos_regimenes()
    props["regimen_fiscal"]["x-options"] = [
        {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"} for r in regimenes
    ]
    props["regimen_fiscal"]["enum"] = [r["clave"] for r in regimenes]
    props["archivo_cer"] = {"type": "string", "format": "binary", "title": "Archivo CER"}
    props["archivo_key"] = {"type": "string", "format": "binary", "title": "Archivo KEY"}
    return {"properties": props, "required": required}

@router.get(
    "/", 
    response_model=List[EmpresaOut], 
    summary="Listar empresas")
def listar_empresas(db: Session = Depends(get_db)):
    """
    Devuelve todas las empresas registradas en el sistema.
    """
    return db.query(Empresa).all()

@router.get(
    "/{id}",
    response_model=EmpresaOut,
    summary="Obtener empresa por ID"
)
def obtener_empresa(
    id: UUID = Path(..., description="ID de la empresa a consultar"),
    db=Depends(get_db)
):
    """
    Obtiene la información de una empresa existente a partir de su UUID.
    """
    empresa = db.query(Empresa).get(id)
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")
    return empresa


@router.post(
    "/",
    status_code=201,
    response_model=EmpresaOut,
    summary="Crear nueva empresa"
)
def crear_empresa(
    empresa_data: EmpresaCreate = Body(...),
    archivo_cer: UploadFile = File(..., description="Archivo CER en formato .cer"),
    archivo_key: UploadFile = File(..., description="Archivo KEY en formato .key"),
    db: Session = Depends(get_db),
):
    """
    Crea una nueva empresa, sube los certificados (.cer/.key) y valida la contraseña
    contra los archivos cargados. 
    - **nombre**: razón social completa.  
    - **rfc**: clave RFC válida para el régimen.  
    - **contrasena**: contraseña de la llave privada.
    """
    return empresa_service.create_empresa(db, empresa_data, archivo_cer, archivo_key)

@router.put(
    "/{id}",
    response_model=EmpresaOut,
    summary="Actualizar empresa existente"
)
def actualizar_empresa(
    id: UUID = Path(..., description="ID de la empresa a actualizar"),
    empresa_data: EmpresaUpdate = Body(...),
    archivo_cer: UploadFile = File(None, description="Nuevo archivo CER (opcional)"),
    archivo_key: UploadFile = File(None, description="Nuevo archivo KEY (opcional)"),
    db: Session = Depends(get_db),
):
    """
    Actualiza los datos de la empresa indicada y vuelve a validar los certificados.
    Si se suben nuevos archivos, se reemplazarán los anteriores.
    """
    empresa = empresa_service.update_empresa(db, id, empresa_data, archivo_cer, archivo_key)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa

@router.delete(
    "/{id}",
    status_code=204,
    summary="Eliminar empresa"
)
def eliminar_empresa(
    id: UUID = Path(..., description="ID de la empresa a eliminar"),
    db=Depends(get_db)
):
    """
    Elimina la empresa y borra sus archivos de certificado del servidor.
    """
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for filename in (empresa.archivo_cer, empresa.archivo_key):
        if filename:
            path = os.path.join(CERT_DIR, filename)
            if os.path.exists(path):
                os.remove(path)
    db.delete(empresa)
    db.commit()
    return Response(status_code=204)