# app/validators/rfc.py
import re

# Listas de claves SAT para tipo de contribuyente
# Listas de claves SAT para tipo de contribuyente
# 626 (RESICO) aplica tanto a Físicas como a Morales
REGIMENES_PERSONA_MORAL = {"601", "603", "609", "620", "622", "623", "624", "626"}
REGIMENES_PERSONA_FISICA = {
    "605",
    "606",
    "608",
    "610",
    "611",
    "612",
    "614",
    "616",
    "621",
    "625",
    "626",
}

RFC_PERSONA_MORAL_REGEX = re.compile(r"^[A-Z&Ñ]{3}\d{6}[A-Z\d]{3}$")
RFC_PERSONA_FISICA_REGEX = re.compile(r"^[A-Z&Ñ]{4}\d{6}[A-Z\d]{3}$")


def validar_rfc_por_regimen(rfc: str, regimen: str) -> bool:
    """
    Valida el RFC según el régimen SAT.
    Soporta regímenes compartidos (como 626) probando ambas longitudes.
    """
    rfc = rfc.upper()
    
    # Check Moral
    if regimen in REGIMENES_PERSONA_MORAL:
        if RFC_PERSONA_MORAL_REGEX.fullmatch(rfc):
            return True

    # Check Physical
    if regimen in REGIMENES_PERSONA_FISICA:
        if RFC_PERSONA_FISICA_REGEX.fullmatch(rfc):
            return True
            
    return False
