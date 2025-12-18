# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
from app.api.factura import router as factura_router
from app.api import catalogos
from app.api import pagos
from app.api import egresos
from app.api import dashboard
from app.api.email_config import router as email_config_router
from app.api.utils import router as utils_router
from app.api.contactos import router as contactos_router
from app.api.presupuestos import router as presupuestos_router
from app.api.login import router as login_router
from app.api.users import router as users_router

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


app = FastAPI(
    title="ERP/CRM Desarrollo NORTON",
    description="Un ERP/CRM para fumigaciones, jardinería y extintores.",
    version="1.0.0",
)

# Montar el directorio de datos como archivos estáticos
app.mount("/data", StaticFiles(directory="data"), name="data")

# Gzip Compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
    factura_router,
    prefix="/api/facturas",
    tags=["facturas"],
    responses={404: {"description": "No encontrado"}},
)
app.include_router(
    catalogos.router,
    prefix="/api/catalogos",
    tags=["catalogos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    pagos.router,
    prefix="/api/pagos",
    tags=["pagos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    egresos.router,
    prefix="/api/egresos",
    tags=["egresos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    email_config_router,
    prefix="/api/empresas/{empresa_id}/email-config",
    tags=["email-config"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    utils_router,
    prefix="/api/utils",
    tags=["utilidades"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    contactos_router,
    prefix="/api",
    tags=["contactos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    presupuestos_router,
    prefix="/api/presupuestos",
    tags=["presupuestos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    login_router,
    prefix="/api",
    tags=["login"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    users_router,
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "No encontrado"}},
)

# Registrar manejadores globales de excepción

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info("Arrancando aplicación FastAPI")

# Ya no usamos Base.metadata.create_all() aquí;
# las migraciones de Alembic se encargarán del esquema.
