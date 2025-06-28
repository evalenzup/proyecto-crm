from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Esquema base con todos los campos CFDI 4.0 y básicos
class ClienteBase(BaseModel):
    nombre_razon_social: str
    tipo_identificacion: str
    numero_identificacion: str
    direccion: Optional[str]
    telefono: Optional[str]
    email: Optional[EmailStr]
    rfc: str
    regimen_fiscal: str
    uso_cfdi: str
    residencia_fiscal: Optional[str]
    num_reg_id_trib: Optional[str]
    codigo_postal_domicilio: Optional[str]

# Esquema para creación
class ClienteCreate(ClienteBase):
    pass

# Esquema para actualización (todos los campos opcionales)
class ClienteUpdate(BaseModel):
    nombre_razon_social: Optional[str]
    tipo_identificacion: Optional[str]
    numero_identificacion: Optional[str]
    direccion: Optional[str]
    telefono: Optional[str]
    email: Optional[EmailStr]
    rfc: Optional[str]
    regimen_fiscal_receptor: Optional[str]
    uso_cfdi: Optional[str]
    residencia_fiscal: Optional[str]
    num_reg_id_trib: Optional[str]
    codigo_postal_domicilio: Optional[str]

# Esquema de salida al frontend
class EmpresaOut(BaseModel):
    id: UUID
    nombre: str
    rfc: str

    class Config:
        orm_mode = True

class ClienteOut(ClienteBase):
    id: UUID
    creado_en: datetime
    actualizado_en: datetime
    empresas: List[EmpresaOut]

    class Config:
        orm_mode = True

'''
Resumen de cada clase:
ClienteBase: base para crear o mostrar clientes.
ClienteCreate: se usa en POST para crear.
ClienteUpdate: se usa en PUT o PATCH para actualizar (todos los campos son opcionales).
ClienteOut: se usa para enviar datos completos al cliente, incluyendo campos gestionados por la base de datos como id y fechas.

'''