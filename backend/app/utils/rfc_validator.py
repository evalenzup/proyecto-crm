# app/utils/rfc_validator.py
"""
Validación de RFC según las reglas del SAT (México).

Formatos válidos:
  - Persona Moral  : 3 letras + 6 dígitos (AAMMDD) + 3 alfanuméricos = 12 chars
  - Persona Física : 4 letras + 6 dígitos (AAMMDD) + 3 alfanuméricos = 13 chars
  - RFC genérico   : XAXX010101000 (público en general)
  - RFC extranjero : XEXX010101000 (persona extranjera)

Letras permitidas: A-Z, Ñ, &
"""

import re

# Regex principal:
# - Personas morales:  3 letras  + fecha YYMMDD + 3 alfanuméricos
# - Personas físicas:  4 letras  + fecha YYMMDD + 3 alfanuméricos
# - RFCs genéricos del SAT
_RFC_RE = re.compile(
    r"^("
    r"XAXX010101000"            # RFC público en general
    r"|XEXX010101000"           # RFC extranjero
    r"|[A-ZÑ&]{3,4}"           # 3–4 letras (nombre/razón social)
    r"[0-9]{2}"                 # año (YY)
    r"(0[1-9]|1[0-2])"         # mes  01-12
    r"(0[1-9]|[12][0-9]|3[01])" # día 01-31
    r"[A-Z0-9]{3}"              # homoclave (3 alfanuméricos)
    r")$"
)


def validate_rfc(rfc: str) -> str:
    """
    Valida y normaliza un RFC.

    - Convierte a mayúsculas y elimina espacios.
    - Lanza ValueError si el formato no es válido según el SAT.
    - Devuelve el RFC normalizado.
    """
    if not rfc:
        raise ValueError("El RFC es requerido.")

    rfc = rfc.strip().upper()

    if not _RFC_RE.match(rfc):
        raise ValueError(
            f"El RFC '{rfc}' no tiene un formato válido. "
            "Debe tener 12 caracteres (persona moral) o 13 (persona física), "
            "con la estructura: letras + fecha (AAMMDD) + homoclave."
        )

    return rfc
