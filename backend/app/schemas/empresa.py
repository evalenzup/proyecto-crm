from pydantic import BaseModel, EmailStr, constr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre: constr(max_length=255) = Field(..., title="Nombre")
    nombre_comercial: constr(max_length=255) = Field(..., title="Nombre Comercial")
    rfc: constr(max_length=13) = Field(..., title="RFC")
    ruc: constr(max_length=20) = Field(..., title="RUC")
    direccion: Optional[str] = Field(None, title="Dirección")
    telefono: Optional[constr(max_length=50)] = Field(None, title="Teléfono")
    email: Optional[EmailStr] = Field(None, title="Correo electrónico")
    regimen_fiscal: constr(max_length=100) = Field(..., title="Régimen Fiscal")
    codigo_postal: constr(max_length=10) = Field(..., title="Código Postal")
    contrasena: constr(max_length=50) = Field(..., title="Contraseña")
    archivo_cer: Optional[str] = Field(None, title="Archivo CER")
    archivo_key: Optional[str] = Field(None, title="Archivo KEY")

class EmpresaCreate(EmpresaBase):
    """
    Para creación, los archivos vendrán como UploadFile en el endpoint.
    """
    pass

class EmpresaOut(EmpresaBase):
    id: UUID = Field(..., title="ID")
    creado_en: datetime = Field(..., title="Creado en")
    actualizado_en: datetime = Field(..., title="Actualizado en")
    clientes: Optional[List[UUID]] = Field(None, title="Clientes")

    class Config:
        orm_mode = True
