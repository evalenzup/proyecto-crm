# app/catalogos_sat/codigos_postales.py
from typing import List, Dict
from app.catalogos_sat.datos.c_codigopostal import CATALOGO as CODIGOS_POSTALES_SAT


def validar_codigo_postal(clave: str) -> bool:
    return any(cp["clave"] == clave for cp in CODIGOS_POSTALES_SAT)


def obtener_todos_codigos_postales() -> List[Dict[str, str]]:
    return CODIGOS_POSTALES_SAT
