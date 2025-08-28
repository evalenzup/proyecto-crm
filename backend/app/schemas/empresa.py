# app/schemas/empresa.py
from pydantic import BaseModel, Field, EmailStr, constr
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.schemas.common import ClienteSimpleOut

class EmpresaBase(BaseModel):
    nombre            : constr(max_length=255) = Field(..., title="Nombre")
    nombre_comercial  : constr(max_length=255) = Field(..., title="Nombre Comercial")
    rfc               : constr(max_length=13)  = Field(..., title="RFC")
    ruc               : constr(max_length=20)  = Field(..., title="RUC")
    direccion         : Optional[str]          = Field(None, title="Dirección")
    telefono          : Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email             : Optional[EmailStr]     = Field(None, title="Correo electrónico")
    regimen_fiscal    : constr(max_length=100) = Field(..., title="Régimen Fiscal")
    codigo_postal     : constr(max_length=10)  = Field(..., title="Código Postal")
    archivo_cer       : Optional[str]          = Field(None, title="Archivo CER")
    archivo_key       : Optional[str]          = Field(None, title="Archivo KEY")
    logo              : Optional[str]          = Field(None, title="Logo")

class EmpresaCreate(EmpresaBase):
    contrasena        : constr(max_length=255) = Field(..., title="Contraseña del CSD (.key)")

class EmpresaUpdate(BaseModel):
    nombre            : Optional[constr(max_length=255)] = Field(None, title="Nombre")
    nombre_comercial  : Optional[constr(max_length=255)] = Field(None, title="Nombre Comercial")
    rfc               : Optional[constr(max_length=13)]  = Field(None, title="RFC")
    ruc               : Optional[constr(max_length=20)]  = Field(None, title="RUC")
    direccion         : Optional[str]          = Field(None, title="Dirección")
    telefono          : Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email             : Optional[EmailStr]     = Field(None, title="Correo electrónico")
    regimen_fiscal    : Optional[constr(max_length=100)] = Field(None, title="Régimen Fiscal")
    codigo_postal     : Optional[constr(max_length=10)]  = Field(None, title="Código Postal")
    contrasena        : Optional[constr(max_length=255)] = Field(None, title="Contraseña del CSD (.key)")

class EmpresaOut(EmpresaBase):
    id               : UUID              = Field(..., title="ID")
    creado_en        : datetime          = Field(..., title="Creado en")
    actualizado_en   : datetime          = Field(..., title="Actualizado en")
    clientes         : Optional[List[ClienteSimpleOut]] = Field(None, title="Clientes")
    contrasena       : Optional[str]     = Field(None, title="Contraseña del CSD (.key)")


    class Config:
        orm_mode = True

class CertInfoOut(BaseModel):
    nombre_cn            : Optional[str]       = Field(None, title="Nombre (CN)")
    rfc                  : Optional[str]       = Field(None, title="RFC")
    curp                 : Optional[str]       = Field(None, title="CURP")
    numero_serie         : Optional[str]       = Field(None, title="Número de serie (hex)")
    valido_desde         : Optional[datetime]  = Field(None, title="Válido desde")
    valido_hasta         : Optional[datetime]  = Field(None, title="Válido hasta")
    issuer_cn            : Optional[str]       = Field(None, title="Emisor (CN)")
    key_usage            : Optional[List[str]] = Field(None, title="Key Usage")
    extended_key_usage   : Optional[List[str]] = Field(None, title="Extended Key Usage")
    tipo_cert            : Optional[str]       = Field(None, title="Tipo de certificado")