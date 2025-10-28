# app/schemas/catalogos.py
from pydantic import BaseModel


class CatalogoItem(BaseModel):
    clave: str
    descripcion: str


class CatalogoSearchItem(BaseModel):
    value: str
    label: str
