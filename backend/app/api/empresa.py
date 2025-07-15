from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
import shutil, os
from datetime import date, datetime
from cryptography import x509
from cryptography.hazmat.primitives.serialization import load_der_private_key
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaOut, EmpresaCreate
from app.catalogos_sat import validar_regimen_fiscal, obtener_todos_regimenes
from app.catalogos_sat.codigos_postales import validar_codigo_postal, obtener_todos_codigos_postales
from app.validadores import validar_rfc_por_regimen, validar_email

CERT_DIR = os.getenv("CERT_DIR", "/data/cert")
os.makedirs(CERT_DIR, exist_ok=True)

router = APIRouter()

def guardar_archivo(upload_file: UploadFile, path_destino: str):
    try:
        with open(path_destino, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        print(f"✅ Archivo guardado: {path_destino}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar archivo {path_destino}: {e}")
        return False

def validar_certificados_sat(cer_path: str, key_path: str, password: str) -> dict:
    try:
        # Cargar certificado
        with open(cer_path, "rb") as f:
            cert_data = f.read()
        cert = x509.load_der_x509_certificate(cert_data, backend=default_backend())

        # Verificar vigencia
        if cert.not_valid_after < datetime.utcnow():
            return {"valido": False, "error": "El certificado está vencido"}

        # Cargar llave privada
        with open(key_path, "rb") as f:
            key_data = f.read()
        private_key = load_der_private_key(key_data, password.encode(), backend=default_backend())

        # Comparar clave pública
        cert_public_key = cert.public_key()
        if isinstance(cert_public_key, rsa.RSAPublicKey) and isinstance(private_key, rsa.RSAPrivateKey):
            if cert_public_key.public_numbers() != private_key.public_key().public_numbers():
                return {"valido": False, "error": "La llave privada no corresponde al certificado"}
        else:
            return {"valido": False, "error": "Tipo de clave no compatible"}

        return {
            "valido": True,
            "valido_hasta": cert.not_valid_after.isoformat(),
            "emisor": cert.issuer.rfc4514_string()
        }
    except Exception as e:
        if "could not decrypt key" in str(e):
            return {"valido": False, "error": "Contraseña incorrecta para el archivo .key"}
        return {"valido": False, "error": str(e)}

    except ValueError as e:
        if "could not decrypt key" in str(e):
            return {"valido": False, "error": "Contraseña incorrecta para la llave privada (.key)"}
        return {"valido": False, "error": str(e)}
    except InvalidKey:
        return {"valido": False, "error": "Llave privada inválida o incompatible"}
    except Exception as e:
        return {"valido": False, "error": str(e)}


def validar_datos_empresa(email, regimen_fiscal, codigo_postal, rfc, ruc, nombre_comercial, db, empresa_existente=None):
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
    archivo_cer: Optional[UploadFile] = File(None),
    archivo_key: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    validar_datos_empresa(email, regimen_fiscal, codigo_postal, rfc, ruc, nombre_comercial, db)

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

    if archivo_cer:
        path_cer = os.path.join(CERT_DIR, f"{nueva.id}.cer")
        if guardar_archivo(archivo_cer, path_cer):
            nueva.cer_filename = archivo_cer.filename
            nueva.cer_path = path_cer

    if archivo_key:
        path_key = os.path.join(CERT_DIR, f"{nueva.id}.key")
        if guardar_archivo(archivo_key, path_key):
            nueva.key_filename = archivo_key.filename
            nueva.key_path = path_key
        # Validación SAT
    if archivo_cer and archivo_key and contrasena:
        resultado = validar_certificados_sat(nueva.cer_path, nueva.key_path, contrasena)
        if not resultado.get("valido"):
            raise HTTPException(status_code=400, detail=f"Certificado inválido: {resultado.get('error')}")
        if resultado.get("valido_hasta") and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today():
            raise HTTPException(status_code=400, detail="El certificado está vencido.")

    db.add(nueva)
    db.flush()
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

    validar_datos_empresa(email, regimen_fiscal, codigo_postal, rfc, ruc, nombre_comercial, db, empresa_existente=empresa)

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

    if archivo_cer:
        path_cer = os.path.join(CERT_DIR, f"{empresa.id}.cer")
        if guardar_archivo(archivo_cer, path_cer):
            empresa.cer_filename = archivo_cer.filename
            empresa.cer_path = path_cer

    if archivo_key:
        path_key = os.path.join(CERT_DIR, f"{empresa.id}.key")
        if guardar_archivo(archivo_key, path_key):
            empresa.key_filename = archivo_key.filename
            empresa.key_path = path_key
    
    if archivo_cer and archivo_key and contrasena:
        resultado = validar_certificados_sat(empresa.cer_path, empresa.key_path, contrasena)
        if not resultado.get("valido"):
            raise HTTPException(status_code=400, detail=f"Certificado inválido: {resultado.get('error')}")
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

    if empresa.cer_path and os.path.exists(empresa.cer_path):
        os.remove(empresa.cer_path)
    if empresa.key_path and os.path.exists(empresa.key_path):
        os.remove(empresa.key_path)

    db.delete(empresa)
    db.commit()
    return Response(status_code=204)
