# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar configuración de logging
from app.core.logger import logger
from app.config import settings
from app.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.api import clientes
from app.api.empresa import router as empresa_router
from app.api.producto_servicio import router as producto_servicio_router
from app.api import catalogos

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


app = FastAPI(
     title="ERP/CRM Desarrollo NORTON",
     description="Un ERP/CRM para fumigaciones, jardinería y extintores.",
     version="1.0.0",
)

# CORS usando orígenes definidos en settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(
    clientes.router,
    prefix="/api/clientes",
    tags=["clientes"],
    responses={404: {"description": "No encontrado"}},
)
app.include_router(
    empresa_router,
    prefix="/api/empresas",
    tags=["empresas"],
    responses={404: {"description": "No encontrado"}},
)
app.include_router(
    producto_servicio_router,
    prefix="/api/productos-servicios",
    tags=["productos-servicios"],
    responses={404: {"description": "No encontrado"}},
)
app.include_router(
    catalogos.router,
    prefix="/api/catalogos",
    tags=["catalogos"],
    responses={404: {"description": "No encontrado"}},
)

# Registrar manejadores globales de excepción

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info("Arrancando aplicación FastAPI")

# Ya no usamos Base.metadata.create_all() aquí;
# las migraciones de Alembic se encargarán del esquema.