from pydantic import BaseModel
from uuid import UUID


class ClienteEmpresaCreate(BaseModel):
    cliente_id: UUID
    empresa_id: UUID
