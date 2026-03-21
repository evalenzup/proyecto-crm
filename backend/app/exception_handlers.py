# app/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, OperationalError, DataError, SQLAlchemyError

from app.core.logger import logger


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.warning("HTTP %s %s → %s", request.method, request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"type": "HTTPException", "detail": exc.detail}},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Validation error %s %s → %s", request.method, request.url, exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"error": {"type": "ValidationError", "detail": exc.errors()}},
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    orig_msg = str(getattr(exc, "orig", exc)).lower()

    if isinstance(exc, IntegrityError):
        if "unique" in orig_msg or "duplicate" in orig_msg:
            status_code = 409
            detail = "Ya existe un registro con esos datos."
        elif "foreign key" in orig_msg or "violates foreign" in orig_msg:
            status_code = 409
            detail = "La operación hace referencia a un registro que no existe."
        elif "not null" in orig_msg or "null value" in orig_msg:
            status_code = 400
            detail = "Faltan datos obligatorios en la solicitud."
        else:
            status_code = 409
            detail = "La operación viola una restricción de integridad."
    elif isinstance(exc, OperationalError):
        status_code = 503
        detail = "La base de datos no está disponible. Intente más tarde."
    elif isinstance(exc, DataError):
        status_code = 400
        detail = "Los datos enviados no son válidos para la base de datos."
    else:
        status_code = 500
        detail = "Error interno del servidor."

    logger.error(
        "Database error %s %s → %s", request.method, request.url, exc, exc_info=exc
    )
    return JSONResponse(
        status_code=status_code,
        content={"error": {"type": "DatabaseError", "detail": detail}},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception %s %s → %s",
        request.method,
        request.url,
        str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"type": "ServerError", "detail": "Internal server error"}},
    )
