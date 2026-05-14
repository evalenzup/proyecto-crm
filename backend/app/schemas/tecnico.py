# app/schemas/tecnico.py
from __future__ import annotations

import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.datetime_utils import TijuanaDatetime
from app.schemas.servicio_operativo import ServicioOperativoSimpleOut

TipoPersonal = Literal["TECNICO", "ADMINISTRATIVO", "OPERATIVO", "SUPERVISOR", "OTRO"]
Sexo = Literal["HOMBRE", "MUJER", "OTRO"]
TipoSangre = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
NivelEstudios = Literal[
    "PRIMARIA", "SECUNDARIA", "PREPARATORIA", "TECNICO_MEDIO",
    "LICENCIATURA", "INGENIERIA", "POSGRADO", "OTRO"
]
LicenciaTipo = Literal["A", "B", "C", "D", "E"]


class TecnicoCreate(BaseModel):
    empresa_id: UUID

    # Nombre
    nombre: str = Field(..., max_length=100)
    primer_apellido: str = Field(..., max_length=100)
    segundo_apellido: Optional[str] = Field(None, max_length=100)

    # Identificación
    curp: Optional[str] = Field(None, max_length=18)
    rfc: Optional[str] = Field(None, max_length=13)
    nss: Optional[str] = Field(None, max_length=11)
    sexo: Optional[Sexo] = None
    tipo_sangre: Optional[TipoSangre] = None

    # Datos laborales
    numero_trabajador: Optional[str] = Field(None, max_length=30)
    tipo_personal: TipoPersonal = "TECNICO"
    area: Optional[str] = Field(None, max_length=100)
    puesto: Optional[str] = Field(None, max_length=100)
    nivel_estudios: Optional[NivelEstudios] = None

    # Contacto y domicilio
    telefono: Optional[str] = Field(None, max_length=50)
    celular: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    direccion: Optional[str] = None

    # Licencia de conducir
    licencia_numero: Optional[str] = Field(None, max_length=50)
    licencia_tipo: Optional[LicenciaTipo] = None
    licencia_vencimiento: Optional[datetime.date] = None

    # Operativo
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: bool = True
    notas: Optional[str] = None
    especialidades_ids: Optional[List[UUID]] = None


class TecnicoUpdate(BaseModel):
    # Nombre
    nombre: Optional[str] = Field(None, max_length=100)
    primer_apellido: Optional[str] = Field(None, max_length=100)
    segundo_apellido: Optional[str] = Field(None, max_length=100)

    # Identificación
    curp: Optional[str] = Field(None, max_length=18)
    rfc: Optional[str] = Field(None, max_length=13)
    nss: Optional[str] = Field(None, max_length=11)
    sexo: Optional[Sexo] = None
    tipo_sangre: Optional[TipoSangre] = None

    # Datos laborales
    numero_trabajador: Optional[str] = Field(None, max_length=30)
    tipo_personal: Optional[TipoPersonal] = None
    area: Optional[str] = Field(None, max_length=100)
    puesto: Optional[str] = Field(None, max_length=100)
    nivel_estudios: Optional[NivelEstudios] = None

    # Contacto y domicilio
    telefono: Optional[str] = Field(None, max_length=50)
    celular: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    direccion: Optional[str] = None

    # Licencia de conducir
    licencia_numero: Optional[str] = Field(None, max_length=50)
    licencia_tipo: Optional[LicenciaTipo] = None
    licencia_vencimiento: Optional[datetime.date] = None

    # Operativo
    max_servicios_dia: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None
    notas: Optional[str] = None
    especialidades_ids: Optional[List[UUID]] = None


class TecnicoOut(BaseModel):
    id: UUID
    empresa_id: UUID

    # Nombre
    nombre: Optional[str] = None
    primer_apellido: Optional[str] = None
    segundo_apellido: Optional[str] = None
    nombre_completo: str

    # Identificación
    curp: Optional[str] = None
    rfc: Optional[str] = None
    nss: Optional[str] = None
    sexo: Optional[str] = None
    tipo_sangre: Optional[str] = None

    # Datos laborales
    numero_trabajador: Optional[str] = None
    tipo_personal: str = "TECNICO"
    area: Optional[str] = None
    puesto: Optional[str] = None
    nivel_estudios: Optional[str] = None

    # Contacto y domicilio
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None

    # Licencia
    licencia_numero: Optional[str] = None
    licencia_tipo: Optional[str] = None
    licencia_vencimiento: Optional[datetime.date] = None

    # Foto
    foto: Optional[str] = None

    # Operativo
    max_servicios_dia: Optional[int] = None
    activo: bool
    notas: Optional[str] = None

    creado_en: TijuanaDatetime
    actualizado_en: TijuanaDatetime
    especialidades: List[ServicioOperativoSimpleOut] = []

    class Config:
        from_attributes = True


class TecnicoPageOut(BaseModel):
    items: List[TecnicoOut]
    total: int
    limit: int
    offset: int
