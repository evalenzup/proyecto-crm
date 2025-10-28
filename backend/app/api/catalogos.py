from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Path

# Catálogos existentes
from app.catalogos_sat.regimenes_fiscales import obtener_todos_regimenes
from app.catalogos_sat.codigos_postales import obtener_todos_codigos_postales
from app.catalogos_sat.productos import (
    obtener_todos_productos,
    buscar_claves_producto,
    descripcion_clave_producto,
)
from app.catalogos_sat.unidades import (
    obtener_todas_unidades,
    buscar_claves_unidad,
    descripcion_clave_unidad,
)

# Catálogos de facturación (CFDI 4.0)
from app.catalogos_sat.facturacion import (
    obtener_todos_tipos_comprobante,
    obtener_todas_formas_pago,
    obtener_todos_metodos_pago,
    obtener_todos_usos_cfdi,
    obtener_todas_tipos_relacion,
    obtener_todas_motivos_cancelacion,
)

from app.schemas.catalogos import CatalogoItem, CatalogoSearchItem

router = APIRouter()

# ────────────────────────────────────────────────────────────────
# CATÁLOGOS GENERALES


def _filtrar_catalogo(
    data: list[dict], q: Optional[str], limit: Optional[int]
) -> list[dict]:
    """
    Filtro simple por 'q' en clave/descripcion y recorte por 'limit'.
    Cada elemento del catálogo debe tener llaves 'clave' y 'descripcion'.
    """
    items = data
    if q:
        s = q.strip().lower()
        items = [
            it
            for it in items
            if s in it.get("clave", "").lower()
            or s in it.get("descripcion", "").lower()
        ]
    if limit and limit > 0:
        items = items[:limit]
    return items


@router.get(
    "/regimen-fiscal", response_model=List[CatalogoItem], summary="Listar regímenes fiscales"
)
def obtener_regimenes_fiscales():
    """
    Devuelve el catálogo completo de regímenes fiscales del SAT.
    Cada elemento: { "clave": str, "descripcion": str }
    """
    return obtener_todos_regimenes()


@router.get(
    "/codigos-postales", response_model=List[CatalogoItem], summary="Listar códigos postales"
)
def obtener_codigos_postales():
    """
    Devuelve todos los códigos postales válidos.
    Cada elemento: { "clave": str, "descripcion": str }
    """
    return obtener_todos_codigos_postales()


@router.get(
    "/productos", response_model=List[CatalogoSearchItem], summary="Listar claves de productos"
)
def obtener_productos():
    """
    Obtiene todas las claves de productos del catálogo SAT.
    Cada elemento: { "value": str, "label": str }
    """
    return obtener_todos_productos()


@router.get(
    "/unidades", response_model=List[CatalogoSearchItem], summary="Listar claves de unidades"
)
def obtener_unidades():
    """
    Obtiene todas las claves de unidades de medida del catálogo SAT.
    Cada elemento: { "value": str, "label": str }
    """
    return obtener_todas_unidades()


# ────────────────────────────────────────────────────────────────
# BÚSQUEDAS CON FILTRO (productos / unidades)


@router.get(
    "/busqueda/productos", response_model=List[CatalogoSearchItem], summary="Buscar claves de producto"
)
def endpoint_buscar_productos(
    q: str = Query(..., min_length=3, description="Texto para filtrar claves/descripcion"),
):
    """
    Busca claves de producto que contengan la cadena `q`.
    Retorna: lista de { "value": str, "label": str }
    """
    items = buscar_claves_producto(q)
    # Normalizar a {value,label}
    return [{"value": it.get("clave"), "label": it.get("descripcion")} for it in items]


@router.get(
    "/busqueda/unidades", response_model=List[CatalogoSearchItem], summary="Buscar claves de unidad"
)
def endpoint_buscar_unidades(
    q: str = Query(..., min_length=2, description="Texto para filtrar claves/descripcion"),
):
    """
    Busca claves de unidad que contengan la cadena `q`.
    Retorna: lista de { "value": str, "label": str }
    """
    items = buscar_claves_unidad(q)
    # Normalizar a {value,label}
    return [{"value": it.get("clave"), "label": it.get("descripcion")} for it in items]


# ────────────────────────────────────────────────────────────────
# DESCRIPCIONES DE CLAVES (productos / unidades)


@router.get(
    "/descripcion/producto/{clave}", response_model=CatalogoItem, summary="Obtener descripción de un producto"
)
def endpoint_descripcion_producto(
    clave: str = Path(..., description="Clave de producto SAT"),
):
    """
    Devuelve la descripción de la clave de producto indicada.
    """
    result = descripcion_clave_producto(clave)
    if not result:
        raise HTTPException(status_code=404, detail="Clave de producto no encontrada")
    return result


@router.get(
    "/descripcion/unidad/{clave}", response_model=CatalogoItem, summary="Obtener descripción de una unidad"
)
def endpoint_descripcion_unidad(
    clave: str = Path(..., description="Clave de unidad SAT"),
):
    """
    Devuelve la descripción de la clave de unidad indicada.
    """
    result = descripcion_clave_unidad(clave)
    if not result:
        raise HTTPException(status_code=404, detail="Clave de unidad no encontrada")
    return result


# ────────────────────────────────────────────────────────────────
# CATÁLOGOS CFDI (facturación)


@router.get(
    "/cfdi/tipos-comprobante", response_model=List[CatalogoItem], summary="Tipos de comprobante (c_TipoDeComprobante)"
)
def catalogo_tipos_comprobante(
    q: Optional[str] = Query(None, description="Filtrar por clave/descripcion"),
    limit: Optional[int] = Query(
        200, ge=1, le=2000, description="Máximo de elementos a devolver"
    ),
):
    """
    Cada elemento: { "clave": str, "descripcion": str }
    """
    data = obtener_todos_tipos_comprobante()
    return _filtrar_catalogo(data, q, limit)


@router.get(
    "/cfdi/formas-pago", response_model=List[CatalogoItem], summary="Formas de pago (c_FormaPago)"
)
def catalogo_formas_pago(
    q: Optional[str] = Query(None, description="Filtrar por clave/descripcion"),
    limit: Optional[int] = Query(200, ge=1, le=2000),
):
    data = obtener_todas_formas_pago()
    return _filtrar_catalogo(data, q, limit)


@router.get(
    "/cfdi/metodos-pago", response_model=List[CatalogoItem], summary="Métodos de pago (c_MetodoPago)"
)
def catalogo_metodos_pago(
    q: Optional[str] = Query(None, description="Filtrar por clave/descripcion"),
    limit: Optional[int] = Query(200, ge=1, le=2000),
):
    data = obtener_todos_metodos_pago()
    return _filtrar_catalogo(data, q, limit)


@router.get(
    "/cfdi/usos-cfdi", response_model=List[CatalogoItem], summary="Usos de CFDI (c_UsoCFDI)"
)
def catalogo_usos_cfdi(
    q: Optional[str] = Query(None, description="Filtrar por clave/descripcion"),
    limit: Optional[int] = Query(200, ge=1, le=2000),
):
    data = obtener_todos_usos_cfdi()
    return _filtrar_catalogo(data, q, limit)


@router.get(
    "/cfdi/tipos-relacion", response_model=List[CatalogoItem], summary="Tipos de relación (c_TipoRelacion)"
)
def catalogo_tipos_relacion(
    q: Optional[str] = Query(None, description="Filtrar por clave/descripcion"),
    limit: Optional[int] = Query(200, ge=1, le=2000),
):
    data = obtener_todas_tipos_relacion()
    return _filtrar_catalogo(data, q, limit)


@router.get(
    "/cfdi/motivos-cancelacion", response_model=List[CatalogoItem], summary="Motivos de cancelación (c_MotivoCancelacion)"
)
def catalogo_motivos_cancelacion(
    q: Optional[str] = Query(None, description="Filtrar por clave/descripcion"),
    limit: Optional[int] = Query(200, ge=1, le=2000),
):
    data = obtener_todas_motivos_cancelacion()
    return _filtrar_catalogo(data, q, limit)