# app/schemas/empresa.py

from pydantic import BaseModel, Field, EmailStr, constr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre             : constr(max_length=255) = Field(..., title="Nombre")
    nombre_comercial   : constr(max_length=255) = Field(..., title="Nombre Comercial")
    rfc                : constr(max_length=13)  = Field(..., title="RFC")
    ruc                : constr(max_length=20)  = Field(..., title="RUC")
    direccion          : Optional[str]          = Field(None, title="Dirección")
    telefono           : Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email              : Optional[EmailStr]     = Field(None, title="Correo electrónico")
    regimen_fiscal     : constr(max_length=100) = Field(..., title="Régimen Fiscal")
    codigo_postal      : constr(max_length=10)  = Field(..., title="Código Postal")
    contrasena         : constr(max_length=50)  = Field(..., title="Contraseña")
    archivo_cer        : Optional[str]          = Field(None, title="Archivo CER")
    archivo_key        : Optional[str]          = Field(None, title="Archivo KEY")

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nombre             : Optional[constr(max_length=255)] = Field(None, title="Nombre")
    nombre_comercial   : Optional[constr(max_length=255)] = Field(None, title="Nombre Comercial")
    rfc                : Optional[constr(max_length=13)]  = Field(None, title="RFC")
    ruc                : Optional[constr(max_length=20)]  = Field(None, title="RUC")
    direccion          : Optional[str]          = Field(None, title="Dirección")
    telefono           : Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email              : Optional[EmailStr]     = Field(None, title="Correo electrónico")
    regimen_fiscal     : Optional[constr(max_length=100)] = Field(None, title="Régimen Fiscal")
    codigo_postal      : Optional[constr(max_length=10)]  = Field(None, title="Código Postal")
    contrasena         : Optional[constr(max_length=50)]  = Field(None, title="Contraseña")

from app.schemas.common import ClienteSimpleOut

class EmpresaOut(EmpresaBase):
    id             : UUID              = Field(..., title="ID")
    creado_en      : datetime          = Field(..., title="Creado en")
    actualizado_en : datetime          = Field(..., title="Actualizado en")
    clientes       : Optional[List[ClienteSimpleOut]] = Field(None, title="Clientes")

    class Config:
        orm_mode = True
