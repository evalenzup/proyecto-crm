from pydantic import BaseModel, Field
from typing import Optional
import uuid

# Campos base compartidos
class EmailConfigBase(BaseModel):
    smtp_server: str = Field(..., example="smtp.example.com")
    smtp_port: int = Field(..., example=587)
    smtp_user: str = Field(..., example="user@example.com")
    from_address: str = Field(..., example="noreply@example.com")
    from_name: Optional[str] = Field(None, example="My Company")
    use_tls: bool = True

# Schema para probar la configuración (requiere contraseña)
class EmailConfigTest(EmailConfigBase):
    smtp_password: str = Field(..., example="secretpassword")

# Schema para crear una configuración (requiere contraseña)
class EmailConfigCreate(EmailConfigBase):
    smtp_password: str = Field(..., example="secretpassword")

# Schema para actualizar (todos los campos son opcionales)
class EmailConfigUpdate(BaseModel):
    smtp_server: Optional[str] = Field(None, example="smtp.example.com")
    smtp_port: Optional[int] = Field(None, example=587)
    smtp_user: Optional[str] = Field(None, example="user@example.com")
    smtp_password: Optional[str] = Field(None, example="newsecretpassword")
    from_address: Optional[str] = Field(None, example="noreply@example.com")
    from_name: Optional[str] = Field(None, example="My Company")
    use_tls: Optional[bool] = None

# Schema para leer la configuración (NO incluye la contraseña)
class EmailConfig(EmailConfigBase):
    id: int
    empresa_id: uuid.UUID

    class Config:
        from_attributes = True
