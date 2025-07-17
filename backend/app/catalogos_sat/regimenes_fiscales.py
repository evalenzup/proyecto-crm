# app/catalogos_sat/regimenes_fiscales.py

from typing import List, Dict
from app.catalogos_sat.datos.c_regimenfiscal import CATALOGO as REGIMENES_FISCALES_SAT

def validar_regimen_fiscal(clave: str) -> bool:
    """Valida si la clave de régimen fiscal existe en el catálogo."""
    return any(rf["clave"] == clave for rf in REGIMENES_FISCALES_SAT)


def obtener_descripcion_regimen(clave: str) -> str:
    """Obtiene la descripción del régimen fiscal dado su clave."""
    for rf in REGIMENES_FISCALES_SAT:
        if rf["clave"] == clave:
            return rf["descripcion"]
    return ""

def obtener_todos_regimenes() -> List[Dict[str,str]]:
    """
    Devuelve la lista completa de regímenes fiscales
    """
    return REGIMENES_FISCALES_SAT