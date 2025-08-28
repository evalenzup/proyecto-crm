# app/services/empresa_service.py
import os
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import Optional
from datetime import date, datetime

from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate
from app.catalogos_sat import validar_regimen_fiscal
from app.catalogos_sat.codigos_postales import validar_codigo_postal
from app.services.certificado import CertificadoService
from app.validators.rfc import validar_rfc_por_regimen
from app.validators.email import validar_email
from app.validators.telefono import validar_telefono
from app.config import settings
from app.core.logger import logger

def validar_datos_empresa(
    db: Session,
    email: Optional[str] = None,
    regimen_fiscal: Optional[str] = None,
    codigo_postal: Optional[str] = None,
    rfc: Optional[str] = None,
    ruc: Optional[str] = None,
    nombre_comercial: Optional[str] = None,
    telefono: Optional[str] = None,
    empresa_existente: Optional[Empresa] = None
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

def _bytes_from_upload(f: UploadFile) -> bytes:
    f.file.seek(0)
    data = f.file.read()
    f.file.seek(0)
    return data

def create_empresa(
    db: Session,
    empresa_data: EmpresaCreate,
    archivo_cer: UploadFile,
    archivo_key: UploadFile,
    logo: Optional[UploadFile] = None
) -> Empresa:
    logger.info("➡️ create_empresa: iniciando")
    validar_datos_empresa(
        db=db,
        email=empresa_data.email,
        regimen_fiscal=empresa_data.regimen_fiscal,
        codigo_postal=empresa_data.codigo_postal,
        rfc=empresa_data.rfc,
        ruc=empresa_data.ruc,
        nombre_comercial=empresa_data.nombre_comercial,
        telefono=empresa_data.telefono
    )

    # Validar EN MEMORIA (no tocar disco) con la contraseña en texto plano
    cer_bytes = _bytes_from_upload(archivo_cer)
    key_bytes = _bytes_from_upload(archivo_key)
    resultado = CertificadoService.validar_bytes(cer_bytes, key_bytes, empresa_data.contrasena)
    if not resultado["valido"]:
        logger.info("❌ create_empresa: validación falló → %s", resultado["error"])
        raise HTTPException(status_code=400, detail=resultado["error"] or "Certificado inválido")
    if resultado.get("valido_hasta") and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today():
        raise HTTPException(status_code=400, detail="El certificado está vencido.")

    nueva = Empresa(
        **empresa_data.dict(),
        # contrasena se guarda TAL CUAL (texto plano)
    )
    db.add(nueva); db.flush()

    # Guardar a disco
    filename_cer = f"{nueva.id}.cer"
    filename_key = f"{nueva.id}.key"
    CertificadoService.guardar(archivo_cer, filename_cer)
    CertificadoService.guardar(archivo_key, filename_key)
    nueva.archivo_cer = filename_cer
    nueva.archivo_key = filename_key

    # Logo opcional
    if logo:
        logos_dir = os.path.join(settings.DATA_DIR, "logos")
        os.makedirs(logos_dir, exist_ok=True)
        logo_filename = f"{nueva.id}.png"
        with open(os.path.join(logos_dir, logo_filename), "wb") as buf:
            buf.write(logo.file.read())
        nueva.logo = os.path.join("logos", logo_filename)

    try:
        db.commit(); db.refresh(nueva)
        logger.info("✅ create_empresa: OK")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="RUC duplicado o error de integridad.")
    return nueva

def update_empresa(
    db: Session,
    empresa_id: UUID,
    empresa_data: EmpresaUpdate,
    archivo_cer: Optional[UploadFile],
    archivo_key: Optional[UploadFile],
    logo: Optional[UploadFile] = None
) -> Optional[Empresa]:
    logger.info("➡️ update_empresa: iniciando update %s", empresa_id)
    from os.path import join, basename, exists

    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        return None

    update_data = empresa_data.dict(exclude_unset=True)
    validar_datos_empresa(
        db=db,
        email=update_data.get("email"),
        regimen_fiscal=update_data.get("regimen_fiscal"),
        codigo_postal=update_data.get("codigo_postal"),
        rfc=update_data.get("rfc"),
        ruc=update_data.get("ruc"),
        nombre_comercial=update_data.get("nombre_comercial"),
        telefono=update_data.get("telefono"),
        empresa_existente=emp
    )

    # Campos simples (excepto contrasena; se maneja después)
    for k, v in update_data.items():
        if k == "contrasena":
            continue
        setattr(emp, k, v)

    # Detectar archivos realmente subidos
    cer_new = bool(archivo_cer and getattr(archivo_cer, "filename", ""))
    key_new = bool(archivo_key and getattr(archivo_key, "filename", ""))

    if cer_new ^ key_new:
        raise HTTPException(status_code=400, detail="Si actualizas certificados, debes subir ambos archivos: CER y KEY.")

    cer_abs = join(settings.CERT_DIR, basename(emp.archivo_cer)) if emp.archivo_cer else None
    key_abs = join(settings.CERT_DIR, basename(emp.archivo_key)) if emp.archivo_key else None
    missing_files = (not cer_abs or not exists(cer_abs)) or (not key_abs or not exists(key_abs))

    if missing_files and not (cer_new and key_new):
        raise HTTPException(status_code=400, detail="No se encontraron ambos archivos en el servidor. Sube CER y KEY para continuar.")

    if cer_new and key_new:
        if not empresa_data.contrasena:
            raise HTTPException(status_code=400, detail="Debes proporcionar la contraseña para validar los certificados.")

        # Validación EN MEMORIA con la nueva contraseña
        cer_bytes = _bytes_from_upload(archivo_cer)
        key_bytes = _bytes_from_upload(archivo_key)
        resultado = CertificadoService.validar_bytes(cer_bytes, key_bytes, empresa_data.contrasena)
        if not resultado["valido"]:
            logger.info("❌ update_empresa: validación falló → %s", resultado["error"])
            raise HTTPException(status_code=400, detail=resultado["error"] or "Certificado inválido")
        if resultado.get("valido_hasta") and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today():
            raise HTTPException(status_code=400, detail="El certificado está vencido.")

        # Reemplazar en disco
        try:
            if cer_abs and os.path.exists(cer_abs): os.remove(cer_abs)
        except Exception:
            pass
        try:
            if key_abs and os.path.exists(key_abs): os.remove(key_abs)
        except Exception:
            pass

        filename_cer = f"{emp.id}.cer"
        filename_key = f"{emp.id}.key"
        CertificadoService.guardar(archivo_cer, filename_cer)
        CertificadoService.guardar(archivo_key, filename_key)
        emp.archivo_cer = filename_cer
        emp.archivo_key = filename_key

        # Actualizar contraseña (texto plano)
        emp.contrasena = empresa_data.contrasena
        logger.info("✅ update_empresa: certificados reemplazados y contraseña actualizada")
    else:
        # No cambiaron certificados; si mandan solo la contraseña, se actualiza en claro
        if "contrasena" in update_data and update_data["contrasena"]:
            emp.contrasena = update_data["contrasena"]
            logger.info("ℹ️ update_empresa: contraseña actualizada (sin cambiar certificados)")

    # Logo
    if logo:
        try:
            if emp.logo and os.path.exists(os.path.join(settings.DATA_DIR, emp.logo)):
                os.remove(os.path.join(settings.DATA_DIR, emp.logo))
        except Exception:
            pass
        logos_dir = os.path.join(settings.DATA_DIR, "logos")
        os.makedirs(logos_dir, exist_ok=True)
        logo_filename = f"{emp.id}.png"
        with open(os.path.join(logos_dir, logo_filename), "wb") as buf:
            buf.write(logo.file.read())
        emp.logo = os.path.join("logos", logo_filename)

    try:
        db.commit(); db.refresh(emp)
        logger.info("✅ update_empresa: commit OK")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="RUC duplicado o error de integridad.")
    return emp