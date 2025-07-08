# -*- coding: utf-8 -*-

# app/catalogos_sat/regimenes_fiscales.py

# Catálogo SAT de Regímenes Fiscales para el CRM corporativo
# Clave = valor CFDI para XML
# Descripción = visualización en PDF y en la interfaz para el usuario

from typing import List, Dict

REGIMENES_FISCALES_SAT = [
    {"clave": "601", "descripcion": "General de Ley Personas Morales"},
    {"clave": "603", "descripcion": "Personas Morales con Fines no Lucrativos"},
    {"clave": "605", "descripcion": "Sueldos y Salarios e Ingresos Asimilados a Salarios"},
    {"clave": "606", "descripcion": "Arrendamiento"},
    {"clave": "608", "descripcion": "Demás ingresos"},
    {"clave": "609", "descripcion": "Consolidación"},
    {"clave": "610", "descripcion": "Residentes en el Extranjero sin Establecimiento Permanente en México"},
    {"clave": "611", "descripcion": "Ingresos por Dividendos (socios y accionistas)"},
    {"clave": "612", "descripcion": "Personas Físicas con Actividades Empresariales y Profesionales"},
    {"clave": "614", "descripcion": "Ingresos por intereses"},
    {"clave": "616", "descripcion": "Sin obligaciones fiscales"},
    {"clave": "620", "descripcion": "Sociedades Cooperativas de Producción que optan por diferir sus ingresos"},
    {"clave": "621", "descripcion": "Incorporación Fiscal"},
    {"clave": "622", "descripcion": "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras"},
    {"clave": "623", "descripcion": "Opcional para Grupos de Sociedades"},
    {"clave": "624", "descripcion": "Coordinados"},
    {"clave": "625", "descripcion": "Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas"},
    {"clave": "626", "descripcion": "Régimen Simplificado de Confianza"},
]

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