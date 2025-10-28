# Dependencias de FastAPI para inyectar funciones en rutas
# BaseModel para estructurar los datos del "usuario"
from pydantic import BaseModel

# UUID para manejar identificadores únicos
from uuid import UUID, uuid4


# Simulación de un usuario autenticado para pruebas
class User(BaseModel):
    id: UUID = uuid4()
    empresa_id: UUID = uuid4()  # cualquier ID para simular
    username: str = "demo"


# Función para obtener el usuario actual autenticado
def get_current_user():
    return User()
