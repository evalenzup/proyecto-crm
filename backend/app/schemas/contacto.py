from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID

# Importa el Enum desde el modelo para mantenerlo consistente
from app.models.contacto import TipoContacto


class ContactoBase(BaseModel):
    nombre: str = Field(..., max_length=255)
    puesto: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=50)
    tipo: TipoContacto = Field(default=TipoContacto.PRINCIPAL)


class ContactoCreate(ContactoBase):
    pass


class ContactoUpdate(ContactoBase):
    # Todos los campos son opcionales en la actualización
    nombre: Optional[str] = Field(None, max_length=255)
    tipo: Optional[TipoContacto] = None


class ContactoOut(ContactoBase):
    id: UUID

    class Config:
        from_attributes = True
