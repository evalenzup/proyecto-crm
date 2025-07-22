# app/validators/email.py
from pydantic import BaseModel, EmailStr, ValidationError

def validar_email(email: str) -> bool:
    """Valida el formato de un email usando Pydantic."""
    class EmailValidator(BaseModel):
        email: EmailStr
    try:
        EmailValidator(email=email)
        return True
    except ValidationError:
        return False


