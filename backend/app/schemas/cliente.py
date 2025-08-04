# app/schemas/cliente.py
from pydantic import BaseModel, Field, EmailStr, constr, conint
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from app.schemas.common import EmpresaSimpleOut

class ClienteBase(BaseModel):
    # Nombres
    nombre_comercial    : constr(max_length=255) = Field(..., title="Nombre Comercial")
    nombre_razon_social : constr(max_length=255) = Field(..., title="Nombre Fiscal")
    # Datos fiscales
    rfc                : constr(max_length=13)  = Field(..., title="RFC")
    regimen_fiscal     : constr(max_length=100) = Field(..., title="Régimen Fiscal")
    # Dirección
    calle              : Optional[constr(max_length=100)] = Field(None, title="Calle")
    numero_exterior    : Optional[constr(max_length=50)]  = Field(None, title="Número Exterior")
    numero_interior    : Optional[constr(max_length=50)]  = Field(None, title="Número Interior")
    colonia            : Optional[constr(max_length=100)] = Field(None, title="Colonia")
    codigo_postal      : constr(max_length=10)            = Field(..., title="Código Postal")
    # Contacto
    telefono           : Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email              : Optional[list[EmailStr]]        = Field(None, title="Correo Electrónico")
    # Datos para pago
    dias_credito       : Optional[conint(ge=0)] = Field(0, title="Días de Crédito")
    dias_recepcion     : Optional[conint(ge=0)] = Field(0, title="Días de Recepción")
    dias_pago          : Optional[conint(ge=0)] = Field(0, title="Días de Pago")
    # Clasificación
    tamano             : Literal['CHICO', 'MEDIANO', 'GRANDE'] = Field(None, title="Tamaño")
    actividad          : Literal['RESIDENCIAL', 'COMERCIAL', 'INDUSTRIAL']  = Field(None, title="Actividad")

class ClienteCreate(ClienteBase):
    empresa_id: UUID = Field(..., title="Empresa", description="ID de la empresa a la que pertenece el cliente")

class ClienteUpdate(BaseModel):
    # Nombres
    nombre_comercial    : Optional[constr(max_length=255)] = Field(None, title="Nombre Comercial")
    nombre_razon_social : Optional[constr(max_length=255)] = Field(None, title="Nombre o Razón Social")
    # Datos fiscales
    rfc                : Optional[constr(max_length=13)]  = Field(None,title="RFC")
    regimen_fiscal     : Optional[constr(max_length=100)] = Field(None,title="Régimen Fiscal")
    # Dirección
    calle              : Optional[constr(max_length=100)] = Field(None, title="Calle")
    numero_exterior    : Optional[constr(max_length=50)]  = Field(None, title="Número Exterior")
    numero_interior    : Optional[constr(max_length=50)]  = Field(None, title="Número Interior")
    colonia            : Optional[constr(max_length=100)] = Field(None, title="Colonia")
    codigo_postal      : Optional[constr(max_length=10)]  = Field(None, title="Código Postal")
    # Contacto
    telefono           : Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email              : Optional[List[EmailStr]] = Field(None, title="Correo Electrónico")
    # Datos para pago
    dias_credito       : Optional[conint(ge=0)] = Field(None, title="Días de Crédito")
    dias_recepcion     : Optional[conint(ge=0)] = Field(None, title="Días de Recepción")
    dias_pago          : Optional[conint(ge=0)] = Field(None, title="Días de Pago")
    # Clasificación             
    tamano             : Optional[Literal['CHICO', 'MEDIANO', 'GRANDE']] = Field(None, title="Tamaño")
    actividad          : Optional[Literal['RESIDENCIAL', 'COMERCIAL', 'INDUSTRIAL']] = Field(None, title="Actividad")

class ClienteOut(ClienteBase):
    id             : UUID                   = Field(..., title="ID")
    creado_en      : datetime               = Field(..., title="Creado en")
    actualizado_en : datetime               = Field(..., title="Actualizado en")
    empresas       : Optional[List[EmpresaSimpleOut]]   = Field(None, title="Empresas")

    class Config:
        orm_mode = True