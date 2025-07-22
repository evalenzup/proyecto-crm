# tests/test_validadores.py
import pytest

from app.validators.rfc import validar_rfc_por_regimen
from app.validators.email import validar_email
from app.validators.telefono import validar_telefono

@ pytest.mark.parametrize("rfc,regimen,expected", [
    ("ABC123456H78", "601", True),    # persona moral válido
    ("ABCD123456H78", "605", True),   # persona física válido
    ("XYZ999999XXX", "999", False),   # régimen no reconocido
    ("XXX", "601", False),            # RFC demasiado corto
])
def test_validar_rfc(rfc, regimen, expected):
    assert validar_rfc_por_regimen(rfc, regimen) is expected

@ pytest.mark.parametrize("email,expected", [
    ("user@example.com", True),
    ("usuario@mail.mx", True),
    ("bad_email@", False),
    ("@dominio.com", False),
    ("sin-arroba.com", False),
])
def test_validar_email(email, expected):
    assert validar_email(email) is expected

@ pytest.mark.parametrize("telefono,expected", [
    ("5551234567", True),      # 10 dígitos
    ("1234567", True),         # 7 dígitos mínimo
    ("123456789012345", True), # 15 dígitos máximo
    ("12345", False),          # menos de 7
    ("1234567890123456", False), # más de 15
    ("+521234567890", False),  # símbolos no permitidos
    ("abcd1234", False),       # letras
])
def test_validar_telefono(telefono, expected):
    assert validar_telefono(telefono) is expected