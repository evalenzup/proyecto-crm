from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
import shutil, os, uuid

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaOut, EmpresaCreate
from app.catalogos_sat import validar_regimen_fiscal, obtener_todos_regimenes

# Definimos el router para endpoints de Empresa
router = APIRouter()

# Directorio de carga (desde env CERT_DIR o por defecto 'certificados')
UPLOAD_DIR = os.getenv("CERT_DIR", "certificados")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/schema")
def get_form_schema():
    """Devuelve JSON-Schema con opciones para selects y marca archivos"""
    schema = EmpresaCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])

    # Inyectar opciones del catálogo SAT
    regimenes = obtener_todos_regimenes()
    props["regimen_fiscal"]["x-options"] = [
        {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"}
        for r in regimenes
    ]
    props["regimen_fiscal"]["enum"] = [r["clave"] for r in regimenes]

    # Marcar campos de archivo como "binary"
    props["archivo_cer"] = {"type": "string", "format": "binary", "title": "Archivo CER"}
    props["archivo_key"] = {"type": "string", "format": "binary", "title": "Archivo KEY"}

    return {"properties": props, "required": required}

@router.get("/", response_model=List[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()

@router.get("/{id}", response_model=EmpresaOut)
def obtener_empresa(id: UUID, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa

@router.post("/", response_model=EmpresaOut, status_code=201)
async def crear_empresa(
    nombre: str = Form(...),
    nombre_comercial: Optional[str] = Form(None),
    ruc: str = Form(...),
    direccion: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    rfc: str = Form(...),
    regimen_fiscal: str = Form(...),
    codigo_postal: str = Form(...),
    contrasena: str = Form(...),
    archivo_cer: Optional[UploadFile] = File(None),
    archivo_key: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # Validaciones básicas
    if not validar_regimen_fiscal(regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")
    if db.query(Empresa).filter(Empresa.ruc == ruc).first():
        raise HTTPException(status_code=400, detail="El RUC ya está registrado.")

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
    )

    # Guardar archivos en disco y asignar metadatos
    if archivo_cer:
        filename = f"{uuid.uuid4()}.cer"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(archivo_cer.file, f)
        nueva.cer_filename = archivo_cer.filename
        nueva.cer_path = path

    if archivo_key:
        filename = f"{uuid.uuid4()}.key"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(archivo_key.file, f)
        nueva.key_filename = archivo_key.filename
        nueva.key_path = path

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
    nombre: Optional[str] = Form(None),
    nombre_comercial: Optional[str] = Form(None),
    ruc: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    rfc: Optional[str] = Form(None),
    regimen_fiscal: Optional[str] = Form(None),
    codigo_postal: Optional[str] = Form(None),
    contrasena: Optional[str] = Form(None),
    archivo_cer: Optional[UploadFile] = File(None),
    archivo_key: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if regimen_fiscal and not validar_regimen_fiscal(regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")
    if ruc and ruc != empresa.ruc and db.query(Empresa).filter(Empresa.ruc == ruc).first():
        raise HTTPException(status_code=400, detail="El RUC ya está registrado en otra empresa.")

    # Actualizar campos básicos
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

    # Reemplazar archivos si vienen nuevos
    if archivo_cer:
        filename = f"{uuid.uuid4()}.cer"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(archivo_cer.file, f)
        empresa.cer_filename = archivo_cer.filename
        empresa.cer_path = path

    if archivo_key:
        filename = f"{uuid.uuid4()}.key"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(archivo_key.file, f)
        empresa.key_filename = archivo_key.filename
        empresa.key_path = path

    try:
        db.commit()
        db.refresh(empresa)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="RUC duplicado o error de integridad.")
    return empresa

@router.delete("/{id}", status_code=204)
def eliminar_empresa(id: UUID, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(empresa)
    db.commit()
    return Response(status_code=204)
