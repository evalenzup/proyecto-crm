# app/api/catalogos.py

from fastapi import APIRouter
from app.catalogos_sat.regimenes_fiscales import obtener_todos_regimenes
from app.catalogos_sat.codigos_postales import obtener_todos_codigos_postales
from app.catalogos_sat.productos import obtener_todos_productos
from app.catalogos_sat.unidades import obtener_todas_unidades

router = APIRouter()

@router.get("/regimen-fiscal", summary="Obtener catálogo de régimen fiscal SAT")
def obtener_regimenes_fiscales():
    """
    Devuelve el catálogo de regímenes fiscales del SAT con clave y descripción
    para ser utilizado en formularios del CRM y validaciones CFDI.
    """
    return obtener_todos_regimenes()

@router.get("/codigos-postales", summary="Obtener catálogo de códigos postales")
def obtener_codigos_postales():
    """
    Devuelve el catálogo de códigos postales del SAT con clave y descripción
    para ser utilizado en formularios del CRM y validaciones CFDI.
    """
    return obtener_todos_codigos_postales()

@router.get("/productos", summary="Obtener catálogo de productos")
def obtener_productos():
    """
    Devuelve el catálogo de productos del SAT con clave y descripción
    para ser utilizado en formularios del CRM y validaciones CFDI.
    """
    return obtener_todos_productos()

@router.get("/unidades", summary="Obtener catálogo de unidades")
def obtener_unidades():
    """
    Devuelve el catálogo de unidades del SAT con clave y descripción
    para ser utilizado en formularios del CRM y validaciones CFDI.
    """
    return obtener_todos_unidades()
