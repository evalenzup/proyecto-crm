# app/schemas/cliente.py

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Literal, Annotated, Any
from pydantic import StringConstraints
from uuid import UUID
from datetime import datetime
import re
from app.schemas.common import EmpresaSimpleOut
from app.schemas.contacto import ContactoOut
from app.schemas.utils import make_optional  # Importamos la utilidad


class ClienteBase(BaseModel):
    # Nombres
    nombre_comercial: Annotated[str, StringConstraints(max_length=255)] = Field(..., title="Nombre Comercial")
    nombre_razon_social: Annotated[str, StringConstraints(max_length=255)] = Field(..., title="Nombre Fiscal")
    # Datos fiscales
    rfc: Annotated[str, StringConstraints(max_length=13)] = Field(..., title="RFC")
    regimen_fiscal: Annotated[str, StringConstraints(max_length=100)] = Field(..., title="Régimen Fiscal")
    # Dirección
    calle: Optional[Annotated[str, StringConstraints(max_length=100)]] = Field(None, title="Calle")
    numero_exterior: Optional[Annotated[str, StringConstraints(max_length=50)]] = Field(
        None, title="Número Exterior"
    )
    numero_interior: Optional[Annotated[str, StringConstraints(max_length=50)]] = Field(
        None, title="Número Interior"
    )
    colonia: Optional[Annotated[str, StringConstraints(max_length=100)]] = Field(None, title="Colonia")
    codigo_postal: Annotated[str, StringConstraints(max_length=10)] = Field(..., title="Código Postal")
    # Geolocalización
    latitud: Optional[float] = Field(None, title="Latitud")
    longitud: Optional[float] = Field(None, title="Longitud")
    # Contacto (listas)
    telefono: Optional[List[Annotated[str, StringConstraints(max_length=50)]]] = Field(None, title="Teléfono")
    email: Optional[List[EmailStr]] = Field(None, title="Correo Electrónico")
    # Datos para pago
    dias_credito: Optional[int] = Field(0, ge=0, title="Días de Crédito")
    dias_recepcion: Optional[int] = Field(0, ge=0, title="Días de Recepción")
    dias_pago: Optional[int] = Field(0, ge=0, title="Días de Pago")
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


class ClienteVincular(BaseModel):
    empresa_ids: List[UUID] = Field(..., title="Empresas a Vincular")


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
    email: Optional[Any] = None

    class Config:
        from_attributes = True
