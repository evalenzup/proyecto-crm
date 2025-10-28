# app/schemas/cliente.py

from pydantic import BaseModel, Field, EmailStr, constr, conint, field_validator
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
import re
from app.schemas.common import EmpresaSimpleOut
from app.schemas.contacto import ContactoOut
from app.schemas.utils import make_optional  # Importamos la utilidad


class ClienteBase(BaseModel):
    # Nombres
    nombre_comercial: constr(max_length=255) = Field(..., title="Nombre Comercial")  # type: ignore
    nombre_razon_social: constr(max_length=255) = Field(..., title="Nombre Fiscal")  # type: ignore
    # Datos fiscales
    rfc: constr(max_length=13) = Field(..., title="RFC")  # type: ignore
    regimen_fiscal: constr(max_length=100) = Field(..., title="Régimen Fiscal")  # type: ignore
    # Dirección
    calle: Optional[constr(max_length=100)] = Field(None, title="Calle")  # type: ignore
    numero_exterior: Optional[constr(max_length=50)] = Field(
        None, title="Número Exterior"
    )  # type: ignore
    numero_interior: Optional[constr(max_length=50)] = Field(
        None, title="Número Interior"
    )  # type: ignore
    colonia: Optional[constr(max_length=100)] = Field(None, title="Colonia")  # type: ignore
    codigo_postal: constr(max_length=10) = Field(..., title="Código Postal")  # type: ignore
    # Geolocalización
    latitud: Optional[float] = Field(None, title="Latitud")
    longitud: Optional[float] = Field(None, title="Longitud")
    # Contacto (listas)
    telefono: Optional[List[constr(max_length=50)]] = Field(None, title="Teléfono")  # type: ignore
    email: Optional[List[EmailStr]] = Field(None, title="Correo Electrónico")
    # Datos para pago
    dias_credito: Optional[conint(ge=0)] = Field(0, title="Días de Crédito")  # type: ignore
    dias_recepcion: Optional[conint(ge=0)] = Field(0, title="Días de Recepción")  # type: ignore
    dias_pago: Optional[conint(ge=0)] = Field(0, title="Días de Pago")  # type: ignore
    # Clasificación
    tamano: Optional[Literal["CHICO", "MEDIANO", "GRANDE"]] = Field(
        None, title="Tamaño"
    )
    actividad: Optional[Literal["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL"]] = Field(
        None, title="Actividad"
    )

    @field_validator("email", mode="before")
    @classmethod
    def split_email(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            parts = re.split(r"[,;\s]+", v)
            cleaned = []
            for e in parts:
                e2 = e.strip().strip("{}[]\"'")
                if e2:
                    cleaned.append(e2)
            return cleaned
        if isinstance(v, list):
            return v
        raise ValueError("email debe ser cadena separada por comas o lista")

    @field_validator("telefono", mode="before")
    @classmethod
    def split_telefono(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            parts = re.split(r"[,;\s]+", v)
            cleaned = [p.strip().strip("{}[]\"'") for p in parts if p.strip()]
            return cleaned
        if isinstance(v, list):
            return v
        raise ValueError("telefono debe ser cadena separada por comas o lista")


class ClienteCreate(ClienteBase):
    empresa_id: List[UUID] = Field(
        ...,
        title="Empresas",
        description="Lista de IDs de empresas a las que pertenece el cliente",
    )


# Generamos ClienteUpdate automáticamente
ClienteUpdate = make_optional(ClienteCreate)


class ClienteOut(ClienteBase):
    id: UUID = Field(..., title="ID")
    creado_en: datetime = Field(..., title="Creado en")
    actualizado_en: datetime = Field(..., title="Actualizado en")
    empresas: Optional[List[EmpresaSimpleOut]] = Field(None, title="Empresas")
    contactos: List[ContactoOut] = Field([], title="Contactos")

    class Config:
        from_attributes = True


class ClienteSimpleOut(BaseModel):
    id: UUID
    nombre_comercial: str

    class Config:
        from_attributes = True
