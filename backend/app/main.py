# Importa FastAPI para crear la aplicación
from fastapi import FastAPI
# Importa el enrutador de clientes desde la carpeta api
from app.api import clientes
# Importa el middleware para habilitar CORS
from fastapi.middleware.cors import CORSMiddleware
# Importa el motor de base de datos
from app.database import engine
# Importa la clase Base para crear las tablas definidas en los modelos
from app.models.models import Base

# Instancia principal de la aplicación FastAPI
app = FastAPI()

# Configuración del middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Permite que el frontend acceda al backend
    allow_credentials=True,                   # Permite el uso de cookies/autenticación
    allow_methods=["*"],                      # Permite todos los métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],                      # Permite todos los encabezados
)

# Incluye el enrutador de clientes con el prefijo "/api/clientes" para sus endpoints
app.include_router(clientes.router, prefix="/api/clientes", tags=["clientes"])

# Crea automáticamente las tablas en la base de datos, si no existen
Base.metadata.create_all(bind=engine)
