# app/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    # exc.errors() es una lista de dicts con location, msg, type
    logger.warning("Validation error %s %s → %s", request.method, request.url, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": {"type": "ValidationError", "detail": exc.errors()}},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception %s %s → %s", request.method, request.url, str(exc), exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"type": "ServerError", "detail": "Internal server error"}},
    )