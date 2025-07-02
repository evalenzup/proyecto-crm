from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import clientes
from app.api.empresa import router as empresa_router  # ✅ Import correcto

from app.database import engine
from app.models import cliente, empresa  # Solo para registrar los modelos

from app.models.base import Base

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(clientes.router, prefix="/api/clientes", tags=["clientes"])
app.include_router(empresa_router, prefix="/api/empresas", tags=["empresas"])  # ✅ Correcto

# Crear tablas
Base.metadata.create_all(bind=engine)
