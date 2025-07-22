# app/validators/rfc.py
import re

# Listas de claves SAT para tipo de contribuyente
REGIMENES_PERSONA_MORAL = {
    "601", "603", "609", "620", "622", "623", "624"
}
REGIMENES_PERSONA_FISICA = {
    "605", "606", "608", "610", "611", "612", "614", "616", "621", "625", "626"
}

RFC_PERSONA_MORAL_REGEX = re.compile(r"^[A-Z&Ñ]{3}\d{6}[A-Z\d]{3}$")
RFC_PERSONA_FISICA_REGEX = re.compile(r"^[A-Z&Ñ]{4}\d{6}[A-Z\d]{3}$")

def validar_rfc_por_regimen(rfc: str, regimen: str) -> bool:
    """
    Valida el RFC según el régimen SAT:
    - Persona Moral (3 letras + 6 dígitos + 3 alfanuméricos)
    - Persona Física (4 letras + 6 dígitos + 3 alfanuméricos)
    Para regímenes no reconocidos devuelve False.
    """
    rfc = rfc.upper()
    if regimen in REGIMENES_PERSONA_MORAL:
        return bool(RFC_PERSONA_MORAL_REGEX.fullmatch(rfc))
    if regimen in REGIMENES_PERSONA_FISICA:
        return bool(RFC_PERSONA_FISICA_REGEX.fullmatch(rfc))
    return False
