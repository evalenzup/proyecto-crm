# app/validators/telefono.py
import re

# Entre 7 y 15 dígitos, solo números
PHONE_REGEX = re.compile(r"^\d{7,15}$")


def validar_telefono(telefono: str) -> bool:
    """
    Valida que el teléfono contenga solo dígitos y tenga longitud entre 7 y 15.
    """
    return bool(PHONE_REGEX.fullmatch(telefono))
