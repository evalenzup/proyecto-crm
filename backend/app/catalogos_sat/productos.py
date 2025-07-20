# app/catalogos_sat/productos.py
from typing import List, Dict, Optional
from app.catalogos_sat.datos.c_claveprodserv import CATALOGO as PRODUCTOS_SERVICIOS_SAT


def obtener_todos_productos() -> list[dict]:
    """
    Devuelve la lista de productos/servicios disponibles en CFDI 4.0.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return PRODUCTOS_SERVICIOS_SAT

def validar_clave_producto(clave: str) -> bool:
    """ Comprueba que la clave exista en el catálogo. """
    return any(item["clave"] == clave for item in PRODUCTOS_SERVICIOS_SAT)


def buscar_claves_producto(q: str) -> List[Dict[str, str]]:
    q_lower = q.lower()
    return [
        item for item in PRODUCTOS_SERVICIOS_SAT
        if q_lower in item["clave"].lower() or q_lower in item["descripcion"].lower()
    ][:25]

def descripcion_clave_producto(clave: str) -> Optional[Dict[str, str]]:
    return next((item for item in PRODUCTOS_SERVICIOS_SAT if item["clave"] == clave), None)