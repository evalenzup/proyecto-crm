# app/validadores.py
from pydantic import BaseModel, EmailStr, ValidationError
import re

# Listas de claves SAT para tipo de contribuyente
REGIMENES_PERSONA_MORAL = {"601", "603", "609", "620", "622", "623", "624"}
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

# Expresiones regulares SAT
RFC_PERSONA_MORAL_REGEX = re.compile(r"^[A-Z&Ñ]{3}\d{6}[A-Z\d]{3}$")
RFC_PERSONA_FISICA_REGEX = re.compile(r"^[A-Z&Ñ]{4}\d{6}[A-Z\d]{3}$")
TEL_REGEX = re.compile(r"^[\d\s()\-+\.#*]*$")


def validar_rfc_por_regimen(rfc: str, regimen: str) -> bool:
    """
    Valida el RFC de acuerdo al tipo de contribuyente:
    - Persona Moral: 12 caracteres (3 letras)
    - Persona Física: 13 caracteres (4 letras)
    """
    rfc = rfc.upper()
    if regimen in REGIMENES_PERSONA_MORAL:
        return bool(RFC_PERSONA_MORAL_REGEX.fullmatch(rfc))
    elif regimen in REGIMENES_PERSONA_FISICA:
        return bool(RFC_PERSONA_FISICA_REGEX.fullmatch(rfc))
    else:
        # Si el régimen no está clasificado, consideramos inválido
        return False


def validar_email(email: str) -> bool:
    """Valida si un email tiene el formato correcto según Pydantic."""

    class EmailValidator(BaseModel):
        email: EmailStr

    try:
        EmailValidator(email=email)
        return True
    except ValidationError:
        return False


def validar_telefono(telefono: str) -> bool:
    """Valida que el teléfono tenga un formato válido y contenga 10 dígitos."""
    # Permitir caracteres de formato y luego contar dígitos
    if not telefono:
        return False
    # Verificar caracteres permitidos
    if not TEL_REGEX.fullmatch(telefono):
        return False
    # Contar sólo dígitos
    digitos = re.sub(r"\D", "", telefono)
    return len(digitos) == 10
