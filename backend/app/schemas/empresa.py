# app/schemas/empresa.py

from pydantic import BaseModel, Field, EmailStr, constr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre             : constr(max_length=255) = Field(..., title="Nombre") # type: ignore
    nombre_comercial   : constr(max_length=255) = Field(..., title="Nombre Comercial") # type: ignore
    rfc                : constr(max_length=13)  = Field(..., title="RFC") # type: ignore
    ruc                : constr(max_length=20)  = Field(..., title="RUC") # type: ignore
    direccion          : Optional[str]          = Field(None, title="Dirección")
    telefono           : Optional[constr(max_length=50)] = Field(None, title="Teléfono") # type: ignore
    email              : Optional[EmailStr]     = Field(None, title="Correo electrónico")
    regimen_fiscal     : constr(max_length=100) = Field(..., title="Régimen Fiscal") # type: ignore
    codigo_postal      : constr(max_length=10)  = Field(..., title="Código Postal") # type: ignore
    contrasena         : constr(max_length=50)  = Field(..., title="Contraseña") # type: ignore
    archivo_cer        : Optional[str]          = Field(None, title="Archivo CER")
    archivo_key        : Optional[str]          = Field(None, title="Archivo KEY")

class EmpresaCreate(EmpresaBase):
    """Modelo para crear una nueva empresa.
    Los campos de archivos son opcionales y pueden ser enviados como base64 en el cuerpo.
    En creación real, los archivos se reciben como UploadFile en el endpoint.
    """
    pass

class EmpresaUpdate(BaseModel):
    nombre             : Optional[constr(max_length=255)] = Field(None, title="Nombre") # type: ignore
    nombre_comercial   : Optional[constr(max_length=255)] = Field(None, title="Nombre Comercial") # type: ignore
    rfc                : Optional[constr(max_length=13)]  = Field(None, title="RFC") # type: ignore
    ruc                : Optional[constr(max_length=20)]  = Field(None, title="RUC") # type: ignore
    direccion          : Optional[str]          = Field(None, title="Dirección")
    telefono           : Optional[constr(max_length=50)] = Field(None, title="Teléfono") # type: ignore
    email              : Optional[EmailStr]     = Field(None, title="Correo electrónico")
    regimen_fiscal     : Optional[constr(max_length=100)] = Field(None, title="Régimen Fiscal") # type: ignore
    codigo_postal      : Optional[constr(max_length=10)]  = Field(None, title="Código Postal") # type: ignore
    contrasena         : Optional[constr(max_length=50)]  = Field(None, title="Contraseña") # type: ignore

class EmpresaOut(EmpresaBase):
    id             : UUID              = Field(..., title="ID")
    creado_en      : datetime          = Field(..., title="Creado en")
    actualizado_en : datetime          = Field(..., title="Actualizado en")
    clientes       : Optional[List[UUID]] = Field(None, title="Clientes")

    class Config:
        orm_mode = True