# app/catalogos_sat/unidades.py
from typing import List, Dict
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