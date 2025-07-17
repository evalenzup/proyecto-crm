import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
from datetime import date, datetime

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaOut, EmpresaCreate
from app.catalogos_sat import validar_regimen_fiscal, obtener_todos_regimenes
from app.catalogos_sat.codigos_postales import validar_codigo_postal, obtener_todos_codigos_postales
from app.validadores import validar_rfc_por_regimen, validar_email, validar_telefono
from app.services.certificado import CertificadoService

CERT_DIR = os.getenv("CERT_DIR", "/data/cert")
# Asegurar directorio
os.makedirs(CERT_DIR, exist_ok=True)

router = APIRouter()

def validar_datos_empresa(
    email: Optional[str], regimen_fiscal: Optional[str], codigo_postal: Optional[str],
    rfc: Optional[str], ruc: Optional[str], nombre_comercial: Optional[str], telefono: Optional[str],
    db: Session, empresa_existente: Empresa = None
):
    if regimen_fiscal and not validar_regimen_fiscal(regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido.")
    if codigo_postal and not validar_codigo_postal(codigo_postal):
        raise HTTPException(status_code=400, detail="Código postal inválido.")
    if rfc:
        regimen = regimen_fiscal or getattr(empresa_existente, 'regimen_fiscal', None)
        if not validar_rfc_por_regimen(rfc, regimen):
            raise HTTPException(status_code=400, detail="RFC inválido para el régimen fiscal.")
    if ruc and (not empresa_existente or ruc != empresa_existente.ruc):
        if db.query(Empresa).filter(Empresa.ruc == ruc).first():
            raise HTTPException(status_code=400, detail="El RUC ya está registrado.")
    if nombre_comercial and (not empresa_existente or nombre_comercial != empresa_existente.nombre_comercial):
        if db.query(Empresa).filter(Empresa.nombre_comercial == nombre_comercial).first():
            raise HTTPException(status_code=400, detail="El nombre comercial ya está registrado.")
    if email and not validar_email(email):
        raise HTTPException(status_code=400, detail="Email no válido.")
    if telefono and not validar_telefono(telefono):
        raise HTTPException(status_code=400, detail="Teléfono no válido.")

@router.get("/certificados/{filename}")
def descargar_certificado(filename: str = Path(..., regex=r"^[\w\-.]+$")):
    path = os.path.join(CERT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=filename)

@router.get("/schema")
def get_form_schema():
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
    archivo_cer: UploadFile = File(...),
    archivo_key: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    validar_datos_empresa(email, regimen_fiscal, codigo_postal, rfc, ruc, nombre_comercial, telefono, db)

    # Crear instancia para obtener ID
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
    db.add(nueva)
    db.flush()  # asigna nueva.id

    # Guardar archivos con nombre por ID
    filename_cer = f"{nueva.id}.cer"
    filename_key = f"{nueva.id}.key"
    path_cer = CertificadoService.guardar(archivo_cer, filename_cer)
    path_key = CertificadoService.guardar(archivo_key, filename_key)

    # Validar certificados
    resultado = CertificadoService.validar(filename_cer, filename_key, contrasena)
    if not resultado["valido"]:
        for p in (path_cer, path_key):
            try: os.remove(p)
            except: pass
        raise HTTPException(status_code=400, detail=resultado["error"])
    if resultado.get("valido_hasta") and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today():
        for p in (path_cer, path_key):
            try: os.remove(p)
            except: pass
        raise HTTPException(status_code=400, detail="El certificado está vencido.")

    # Guardar nombres en DB
    nueva.archivo_cer = filename_cer
    nueva.archivo_key = filename_key

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
    contrasena: str = Form(...),
    archivo_cer: Optional[UploadFile] = File(None),
    archivo_key: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    validar_datos_empresa(email, regimen_fiscal, codigo_postal, rfc, ruc, nombre_comercial, telefono, db, empresa)

    # actualizar campos básicos
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


    filename_cer = f"{empresa.id}.cer"
    filename_key = f"{empresa.id}.key"

    if archivo_cer:
        filename_cer = f"{empresa.id}.cer"
        CertificadoService.guardar(archivo_cer, filename_cer)
       
    if archivo_key:
        filename_key = f"{empresa.id}.key"
        CertificadoService.guardar(archivo_key, filename_key)
        
     
    empresa.archivo_cer = filename_cer
    empresa.archivo_key = filename_key
    # validar siempre certificados
    resultado = CertificadoService.validar(empresa.archivo_cer, empresa.archivo_key, contrasena)
    if not resultado["valido"]:
        raise HTTPException(status_code=400, detail=resultado["error"])
    if resultado.get("valido_hasta") and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today():
        raise HTTPException(status_code=400, detail="El certificado está vencido.")

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
    for filename in (empresa.archivo_cer, empresa.archivo_key):
        if filename:
            path = os.path.join(CERT_DIR, filename)
            if os.path.exists(path):
                os.remove(path)
    db.delete(empresa)
    db.commit()
    return Response(status_code=204)