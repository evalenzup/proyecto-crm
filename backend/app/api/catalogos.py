# app/api/catalogos.py
from fastapi import APIRouter, HTTPException, Query, Path

from app.catalogos_sat.regimenes_fiscales import (
    obtener_todos_regimenes
)
from app.catalogos_sat.codigos_postales import (
    obtener_todos_codigos_postales
)
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
# CATÁLOGOS GENERALES

@router.get(
    "/regimen-fiscal",
    summary="Listar regímenes fiscales"
)
def obtener_regimenes_fiscales():
    """
    Devuelve el catálogo completo de regímenes fiscales del SAT.
    Cada elemento incluye:
    - **clave**: código de régimen
    - **descripcion**: descripción oficial del régimen
    """
    return obtener_todos_regimenes()


@router.get(
    "/codigos-postales",
    summary="Listar códigos postales"
)
def obtener_codigos_postales():
    """
    Devuelve todos los códigos postales válidos.
    Cada elemento incluye:
    - **clave**: código postal
    - **descripcion**: descripción o municipio asociado
    """
    return obtener_todos_codigos_postales()


@router.get(
    "/productos",
    summary="Listar claves de productos"
)
def obtener_productos():
    """
    Obtiene todas las claves de productos del catálogo SAT.
    Cada elemento incluye:
    - **value**: clave de producto
    - **label**: descripción del producto
    """
    return obtener_todos_productos()


@router.get(
    "/unidades",
    summary="Listar claves de unidades"
)
def obtener_unidades():
    """
    Obtiene todas las claves de unidades de medida del catálogo SAT.
    Cada elemento incluye:
    - **value**: clave de unidad
    - **label**: descripción de la unidad
    """
    return obtener_todas_unidades()


# ────────────────────────────────────────────────────────────────
# BÚSQUEDAS CON FILTRO

@router.get(
    "/busqueda/productos",
    summary="Buscar claves de producto",
)
def endpoint_buscar_productos(
    q: str = Query(
        ..., min_length=3,
        description="Texto de búsqueda para filtrar claves de producto"
    )
):
    """
    Busca claves de producto que contengan la cadena `q`.
    Parámetro:
    - **q**: mínimo 3 caracteres

    Retorna una lista de objetos con **value** y **label**.
    """
    return buscar_claves_producto(q)


@router.get(
    "/busqueda/unidades",
    summary="Buscar claves de unidad",
)
def endpoint_buscar_unidades(
    q: str = Query(
        ..., min_length=3,
        description="Texto de búsqueda para filtrar claves de unidad"
    )
):
    """
    Busca claves de unidad que contengan la cadena `q`.
    Parámetro:
    - **q**: mínimo 3 caracteres

    Retorna una lista de objetos con **value** y **label**.
    """
    return buscar_claves_unidad(q)


# ────────────────────────────────────────────────────────────────
# DESCRIPCIONES DE CLAVES

@router.get(
    "/descripcion/producto/{clave}",
    summary="Obtener descripción de un producto"
)
def endpoint_descripcion_producto(
    clave: str = Path(
        ...,
        description="Clave de producto SAT a consultar"
    )
):
    """
    Devuelve la descripción detallada de la clave de producto indicada.
    Parámetro:
    - **clave**: clave exacta del catálogo SAT
    """
    result = descripcion_clave_producto(clave)
    if not result:
        raise HTTPException(status_code=404, detail="Clave de producto no encontrada")
    return result


@router.get(
    "/descripcion/unidad/{clave}",
    summary="Obtener descripción de una unidad"
)
def endpoint_descripcion_unidad(
    clave: str = Path(
        ...,
        description="Clave de unidad SAT a consultar"
    )
):
    """
    Devuelve la descripción detallada de la clave de unidad indicada.
    Parámetro:
    - **clave**: clave exacta del catálogo SAT
    """
    result = descripcion_clave_unidad(clave)
    if not result:
        raise HTTPException(status_code=404, detail="Clave de unidad no encontrada")
    return result