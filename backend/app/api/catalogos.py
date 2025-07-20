# app/api/catalogos.py

from fastapi import APIRouter, HTTPException, Query
from app.catalogos_sat.regimenes_fiscales import obtener_todos_regimenes
from app.catalogos_sat.codigos_postales import obtener_todos_codigos_postales
from app.catalogos_sat.productos import (
    obtener_todos_productos,
    buscar_claves_producto,
    descripcion_clave_producto
)
from app.catalogos_sat.unidades import (
    obtener_todas_unidades,
    buscar_claves_unidad,
    descripcion_clave_unidad
)

router = APIRouter()

# ────────────────────────────────────────────────────────────────
# CATÁLOGOS

@router.get("/regimen-fiscal")
def obtener_regimenes_fiscales():
    return obtener_todos_regimenes()

@router.get("/codigos-postales")
def obtener_codigos_postales():
    return obtener_todos_codigos_postales()

@router.get("/productos")
def obtener_productos():
    return obtener_todos_productos()

@router.get("/unidades")
def obtener_unidades():
    return obtener_todas_unidades()

# ────────────────────────────────────────────────────────────────
# BUSQUEDAS

@router.get("/busqueda/productos")
def endpoint_buscar_productos(q: str = Query(..., min_length=3)):
    return buscar_claves_producto(q)

@router.get("/busqueda/unidades")
def endpoint_buscar_unidades(q: str = Query(..., min_length=3)):
    return buscar_claves_unidad(q)

# ────────────────────────────────────────────────────────────────
# DESCRIPCIONES

@router.get("/descripcion/producto/{clave}")
def endpoint_descripcion_producto(clave: str):
    result = descripcion_clave_producto(clave)
    if not result:
        raise HTTPException(status_code=404, detail="Clave no encontrada")
    return result

@router.get("/descripcion/unidad/{clave}")
def endpoint_descripcion_unidad(clave: str):
    result = descripcion_clave_unidad(clave)
    if not result:
        raise HTTPException(status_code=404, detail="Clave no encontrada")
    return result