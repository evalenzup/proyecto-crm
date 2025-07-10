from pydantic import BaseModel, EmailStr, constr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre: constr(max_length=255)
    nombre_comercial: constr(max_length=255)
    ruc: constr(max_length=20)
    direccion: Optional[str] = None
    telefono: Optional[constr(max_length=50)] = None
    email: Optional[EmailStr] = None
    rfc: constr(max_length=13)
    regimen_fiscal: constr(max_length=100)
    codigo_postal: constr(max_length=10)
    contrasena: constr(max_length=50)
    # Sólo guardamos la ruta (o URL) al archivo
    archivo_cer: Optional[str] = None
    archivo_key: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    # Para creación, los archivos vendrán como UploadFile en el endpoint
    pass

class EmpresaOut(EmpresaBase):
    id: UUID
    creado_en: datetime
    actualizado_en: datetime
    # Si quisieras exponer la relación:
    clientes: Optional[List[UUID]] = None

    class Config:
        orm_mode = True
