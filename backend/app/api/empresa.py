import os
import json
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Response,
    Path,
    Form,
    Query,
)
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.empresa import EmpresaOut, EmpresaCreate, EmpresaUpdate, CertInfoOut
from app.catalogos_sat import obtener_todos_regimenes
from app.services.empresa_service import empresa_repo  # Importamos el nuevo repositorio
from app.services.certificado import CertificadoService
from app.config import settings
from app.core.logger import logger
from pydantic import BaseModel


class EmpresaPageOut(BaseModel):
    items: List[EmpresaOut]
    total: int
    limit: int
    offset: int


# Estas variables y la creación de directorios se mantienen aquí, ya que son configuraciones de la API
CERT_DIR = settings.CERT_DIR
LOGO_DIR = os.path.join(settings.DATA_DIR, "logos")
os.makedirs(CERT_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)

router = APIRouter()


# Esta función se mantiene, ya que es una utilidad para parsear el JSON de los formularios multipart
def _parse_json_form(data_str: Optional[str], model_cls):
    if data_str is None or data_str == "":
        try:
            return model_cls()
        except TypeError:
            raise HTTPException(status_code=422, detail="empresa_data es requerido")
    try:
        raw = json.loads(data_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="empresa_data no es JSON válido")
    try:
        return model_cls(**raw)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


@router.get("/form-schema", summary="Schema del formulario de empresa")
@router.get("/schema", summary="Schema del formulario de empresa (alias)")
def get_form_schema():
    try:
        schema = EmpresaCreate.model_json_schema()
    except Exception:
        schema = EmpresaCreate.schema()

    props = schema.get("properties", {})
    required = schema.get("required", [])

    regimenes = obtener_todos_regimenes()
    props.setdefault("regimen_fiscal", {})
    props["regimen_fiscal"]["x-options"] = [
        {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"}
        for r in regimenes
    ]
    props["regimen_fiscal"]["enum"] = [r["clave"] for r in regimenes]

    props["archivo_cer"] = {
        "type": "string",
        "format": "binary",
        "title": "Archivo CER",
    }
    props["archivo_key"] = {
        "type": "string",
        "format": "binary",
        "title": "Archivo KEY",
    }
    props["logo"] = {"type": "string", "format": "binary", "title": "Logo"}

    return {"properties": props, "required": required}


@router.get("/logos/{empresa_id}.png", summary="Descargar logo de la empresa")
def descargar_logo(empresa_id: UUID):
    filename = f"{empresa_id}.png"

    # --- Path sanitization ---
    logo_dir_real = os.path.realpath(LOGO_DIR)
    unsafe_path = os.path.join(logo_dir_real, filename)
    safe_path = os.path.realpath(unsafe_path)

    if not safe_path.startswith(logo_dir_real):
        raise HTTPException(status_code=403, detail="Acceso prohibido.")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Logo no encontrado")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(safe_path, filename=filename, headers=headers)


@router.get("/certificados/{filename}", summary="Descargar .cer/.key")
def descargar_certificado(filename: str = Path(..., regex=r"^[\w.\-]+$")):
    # --- Path sanitization ---
    cert_dir_real = os.path.realpath(CERT_DIR)
    unsafe_path = os.path.join(cert_dir_real, filename)
    safe_path = os.path.realpath(unsafe_path)

    if not safe_path.startswith(cert_dir_real):
        raise HTTPException(status_code=403, detail="Acceso prohibido.")

    if not os.path.exists(safe_path):
        logger.warning("GET cert: no existe %s", safe_path)
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(safe_path, filename=filename, headers=headers)


@router.get(
    "/{id}/cert-info",
    response_model=CertInfoOut,
    summary="Info del certificado de la empresa",
)
def obtener_cert_info(id: UUID, db: Session = Depends(get_db)):
    # Se obtiene la empresa a través del repo
    empresa = empresa_repo.get(db, id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if not empresa.archivo_cer:
        raise HTTPException(
            status_code=404, detail="La empresa no tiene .cer registrado"
        )

    info = CertificadoService.extraer_info(empresa.archivo_cer)
    return CertInfoOut(
        nombre_cn=info.get("nombre_cn"),
        rfc=info.get("rfc"),
        curp=info.get("curp"),
        numero_serie=info.get("numero_serie"),
        valido_desde=info.get("valido_desde"),
        valido_hasta=info.get("valido_hasta"),
        issuer_cn=info.get("issuer_cn"),
        key_usage=info.get("key_usage"),
        extended_key_usage=info.get("extended_key_usage"),
        tipo_cert=info.get("tipo_cert"),
    )


@router.get("/", response_model=EmpresaPageOut, summary="Listar empresas")
def listar_empresas(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    rfc: Optional[str] = Query(None),
    nombre_comercial: Optional[str] = Query(None),
):
    items, total = empresa_repo.get_multi(
        db,
        skip=offset,
        limit=limit,
        rfc=rfc,
        nombre_comercial=nombre_comercial,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{id}", response_model=EmpresaOut, summary="Obtener empresa por ID")
def obtener_empresa(id: UUID, db: Session = Depends(get_db)):
    empresa = empresa_repo.get(db, id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa


@router.post("/", status_code=201, response_model=EmpresaOut, summary="Crear empresa")
def crear_empresa(
    empresa_data: str = Form(..., description="JSON de EmpresaCreate"),
    archivo_cer: UploadFile = File(...),
    archivo_key: UploadFile = File(...),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    data = _parse_json_form(empresa_data, EmpresaCreate)
    return empresa_repo.create(
        db, obj_in=data, archivo_cer=archivo_cer, archivo_key=archivo_key, logo=logo
    )


@router.put("/{id}", response_model=EmpresaOut, summary="Actualizar empresa")
def actualizar_empresa(
    id: UUID,
    empresa_data: str | None = Form(None, description="JSON de EmpresaUpdate"),
    archivo_cer: UploadFile | None = File(None),
    archivo_key: UploadFile | None = File(None),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    data = _parse_json_form(empresa_data, EmpresaUpdate)
    empresa = empresa_repo.get(db, id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa_repo.update(
        db,
        db_obj=empresa,
        obj_in=data,
        archivo_cer=archivo_cer,
        archivo_key=archivo_key,
        logo=logo,
    )


@router.delete("/{id}", status_code=204, summary="Eliminar empresa")
def eliminar_empresa(id: UUID, db: Session = Depends(get_db)):
    empresa = empresa_repo.remove(db, id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return
