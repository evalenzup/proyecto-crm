# app/catalogos_sat/unidades.py
from typing import List, Dict, Optional
from app.catalogos_sat.datos.c_claveunidad import CATALOGO as UNIDADES_MEDIDA_SAT

def obtener_todas_unidades() -> list[dict]:
    """
    Devuelve la lista de unidades de medida del SAT.
    Cada elemento es {"clave": str, "descripcion": str}.
    """
    return UNIDADES_MEDIDA_SAT

def validar_clave_unidad(clave: str) -> bool:
    """ Comprueba que la unidad exista en el catálogo. """
    return any(item["clave"] == clave for item in UNIDADES_MEDIDA_SAT)

def buscar_claves_unidad(q: str) -> List[Dict[str, str]]:
    q_lower = q.lower()
    return [
        item for item in UNIDADES_MEDIDA_SAT
        if q_lower in item["clave"].lower() or q_lower in item["descripcion"].lower()
    ][:25]

def descripcion_clave_unidad(clave: str) -> Optional[Dict[str, str]]:
    return next((item for item in UNIDADES_MEDIDA_SAT if item["clave"] == clave), None)