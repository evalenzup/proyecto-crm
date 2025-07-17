# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import clientes
from app.api.empresa import router as empresa_router 
from app.api.producto_servicio import router as producto_servicio_router
from app.api import catalogos
from app.database import engine
from app.models.base import Base
# importar modelos para crear tablas
import app.models.cliente
import app.models.empresa
import app.models.producto_servicio

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(clientes.router,
                   prefix="/api/clientes",
                   tags=["clientes"])

app.include_router(empresa_router,
                   prefix="/api/empresas",
                   tags=["empresas"]) 

app.include_router(producto_servicio_router,
                   prefix="/api/productos-servicios",
                   tags=["productos-servicios"])

# Catalogos SAT
app.include_router(catalogos.router,
                   prefix="/api/catalogos",
                   tags=["catalogos"])

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)