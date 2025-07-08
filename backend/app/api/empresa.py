from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
import shutil
import os

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaOut, EmpresaCreate
from app.catalogos_sat import validar_regimen_fiscal
from app.catalogos_sat import obtener_todos_regimenes

# Router para endpoints de Empresas
router = APIRouter()

@router.get("/schema")
def get_form_schema():
    """Devuelve JSON-Schema + opciones para los selects y marca archivos."""
    schema = EmpresaCreate.schema()  
    props = schema["properties"]
    required = schema.get("required", [])

    # 1) Inyectar las opciones para el dropdown
    regimenes = obtener_todos_regimenes()
    props["regimen_fiscal"]["x-options"] = [
      {"value": r["clave"], "label": f'{r["clave"]} – {r["descripcion"]}'}
      for r in regimenes
    ]
    props["regimen_fiscal"]["enum"] = regimenes and [r["clave"] for r in regimenes]

    # 2) Señalar que los archivos son “binarios”
    #    FastAPI/OpenAPI ya marca UploadFile como format=binary,
    #    pero lo aseguramos:
    props["archivo_cer"] = {"type": "string", "format": "binary", "title": "Archivo CER"}
    props["archivo_key"] = {"type": "string", "format": "binary", "title": "Archivo KEY"}

    return {"properties": props, "required": required}


@router.get("/", response_model=List[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    """
    Lista todas las empresas.
    """
    return db.query(Empresa).all()

@router.get("/{id}", response_model=EmpresaOut)
def obtener_empresa(id: UUID, db: Session = Depends(get_db)):
    """
    Obtiene una empresa por su ID.
    """
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa

@router.post("/", response_model=EmpresaOut, status_code=201)
async def crear_empresa(
    nombre: str                       = Form(...),
    nombre_comercial: str             = Form(...),
    ruc: str                          = Form(...),
    direccion: Optional[str]          = Form(None),
    telefono: Optional[str]           = Form(None),
    email: Optional[str]              = Form(None),
    rfc: str                          = Form(...),
    regimen_fiscal: str               = Form(...),
    codigo_postal: str                = Form(...),
    contrasena: str                   = Form(...),
    archivo_cer: UploadFile           = File(...),
    archivo_key: UploadFile           = File(...),
    db: Session                       = Depends(get_db),
):
    # Validación de régimen fiscal
    if not validar_regimen_fiscal(regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")

    # Unicidad de RUC
    if db.query(Empresa).filter(Empresa.ruc == ruc).first():
        raise HTTPException(status_code=400, detail="El RUC ya está registrado.")

    # Preparar directorio de certificados
    cert_dir = "certificados"
    os.makedirs(cert_dir, exist_ok=True)
    cer_path, key_path = None, None

    # Guardar archivos si vienen
    if archivo_cer:
        cer_path = os.path.join(cert_dir, archivo_cer.filename)
        with open(cer_path, "wb") as f:
            shutil.copyfileobj(archivo_cer.file, f)
    if archivo_key:
        key_path = os.path.join(cert_dir, archivo_key.filename)
        with open(key_path, "wb") as f:
            shutil.copyfileobj(archivo_key.file, f)

    # Crear entidad
    nueva = Empresa(
        nombre=nombre,
        nombre_comercial=nombre_comercial,
        ruc=ruc,
        direccion=direccion,
        telefono=telefono,
        email=email,
        rfc=rfc,
        regimen_fiscal=regimen_fiscal,
        codigo_postal=codigo_postal,
        contrasena=contrasena,
        archivo_cer=cer_path,
        archivo_key=key_path,
    )
    db.add(nueva)
    try:
        db.commit()
        db.refresh(nueva)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="RUC duplicado o error de integridad.")
    return nueva

@router.put("/{id}", response_model=EmpresaOut)
async def actualizar_empresa(
    id: UUID,
    nombre: Optional[str]             = Form(None),
    nombre_comercial: Optional[str]   = Form(None),
    ruc: Optional[str]                = Form(None),
    direccion: Optional[str]          = Form(None),
    telefono: Optional[str]           = Form(None),
    email: Optional[str]              = Form(None),
    rfc: Optional[str]                = Form(None),
    regimen_fiscal: Optional[str]     = Form(None),
    codigo_postal: Optional[str]      = Form(None),
    contrasena: Optional[str]         = Form(None),
    archivo_cer: Optional[UploadFile] = File(None),
    archivo_key: Optional[UploadFile] = File(None),
    db: Session                       = Depends(get_db),
):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Validar régimen si fue enviado
    if regimen_fiscal and not validar_regimen_fiscal(regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")
    # Verificar nuevo RUC único
    if ruc and ruc != empresa.ruc and db.query(Empresa).filter(Empresa.ruc == ruc).first():
        raise HTTPException(status_code=400, detail="El RUC ya está registrado en otra empresa.")

    # Actualizar campos
    for attr, val in {
        "nombre": nombre,
        "nombre_comercial": nombre_comercial,
        "ruc": ruc,
        "direccion": direccion,
        "telefono": telefono,
        "email": email,
        "rfc": rfc,
        "regimen_fiscal": regimen_fiscal,
        "codigo_postal": codigo_postal,
        "contrasena": contrasena,
    }.items():
        if val is not None:
            setattr(empresa, attr, val)

    # Guardar nuevos archivos si vienen
    cert_dir = "certificados"
    os.makedirs(cert_dir, exist_ok=True)
    if archivo_cer:
        cer_path = os.path.join(cert_dir, archivo_cer.filename)
        with open(cer_path, "wb") as f:
            shutil.copyfileobj(archivo_cer.file, f)
        empresa.archivo_cer = cer_path
    if archivo_key:
        key_path = os.path.join(cert_dir, archivo_key.filename)
        with open(key_path, "wb") as f:
            shutil.copyfileobj(archivo_key.file, f)
        empresa.archivo_key = key_path

    try:
        db.commit()
        db.refresh(empresa)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="RUC duplicado o error de integridad.")
    return empresa

@router.delete("/{id}", status_code=204)
def eliminar_empresa(id: UUID, db: Session = Depends(get_db)):
    """
    Elimina una empresa.
    """
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(empresa)
    db.commit()
    return Response(status_code=204)