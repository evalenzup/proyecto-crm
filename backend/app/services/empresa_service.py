# app/services/empresa_service.py
import os
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
from datetime import date, datetime

from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate
from app.catalogos_sat import validar_regimen_fiscal
from app.catalogos_sat.codigos_postales import validar_codigo_postal
from app.services.certificado import CertificadoService
from app.validators.rfc import validar_rfc_por_regimen
from app.validators.email import validar_email
from app.validators.telefono import validar_telefono
from app.auth.password import get_password_hash, verify_password

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

def create_empresa(db: Session, empresa_data: EmpresaCreate, archivo_cer: UploadFile, archivo_key: UploadFile) -> Empresa:
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

    nueva_empresa = Empresa(
        **empresa_data.dict(exclude={"contrasena"}),
        contrasena=get_password_hash(empresa_data.contrasena)
    )
    db.add(nueva_empresa)
    db.flush()

    filename_cer = f"{nueva_empresa.id}.cer"
    filename_key = f"{nueva_empresa.id}.key"
    path_cer = CertificadoService.guardar(archivo_cer, filename_cer)
    path_key = CertificadoService.guardar(archivo_key, filename_key)

    resultado = CertificadoService.validar(filename_cer, filename_key, empresa_data.contrasena)
    if not resultado["valido"]:
        for p in (path_cer, path_key):
            try:
                os.remove(p)
            except:
                pass
        raise HTTPException(status_code=400, detail=resultado["error"])
    if resultado.get("valido_hasta") and datetime.fromisoformat(resultado["valido_hasta"]).date() < date.today():
        for p in (path_cer, path_key):
            try:
                os.remove(p)
            except:
                pass
        raise HTTPException(status_code=400, detail="El certificado está vencido.")

    nueva_empresa.archivo_cer = filename_cer
    nueva_empresa.archivo_key = filename_key

    try:
        db.commit()
        db.refresh(nueva_empresa)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="RUC duplicado o error de integridad.")
    
    return nueva_empresa

def update_empresa(db: Session, empresa_id: UUID, empresa_data: EmpresaUpdate, archivo_cer: Optional[UploadFile], archivo_key: Optional[UploadFile]) -> Optional[Empresa]:
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
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
        empresa_existente=empresa
    )

    for field, value in update_data.items():
        if field == "contrasena":
            if value:
                setattr(empresa, field, get_password_hash(value))
        else:
            setattr(empresa, field, value)

    if archivo_cer:
        filename_cer = f"{empresa.id}.cer"
        CertificadoService.guardar(archivo_cer, filename_cer)
        empresa.archivo_cer = filename_cer

    if archivo_key:
        filename_key = f"{empresa.id}.key"
        CertificadoService.guardar(archivo_key, filename_key)
        empresa.archivo_key = filename_key

    password_to_verify = empresa_data.contrasena if empresa_data.contrasena else ""
    if empresa_data.contrasena and not verify_password(empresa_data.contrasena, empresa.contrasena):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta")

    resultado = CertificadoService.validar(empresa.archivo_cer, empresa.archivo_key, password_to_verify)
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