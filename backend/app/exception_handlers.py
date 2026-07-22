# app/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
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
    # En Pydantic v2, exc.errors() puede traer en `ctx` el objeto de excepción
    # original (ej. ValueError de un validador), que NO es serializable a JSON.
    # Lo convertimos a string para no romper la respuesta (antes esto provocaba
    # un 500 "Object of type ValueError is not JSON serializable" y el usuario
    # nunca veía el mensaje real de validación, p. ej. el de RFC inválido).
    errores = []
    primer_mensaje = None
    for err in exc.errors():
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict):
            err["ctx"] = {k: (str(v) if isinstance(v, Exception) else v) for k, v in ctx.items()}
        if primer_mensaje is None and err.get("msg"):
            primer_mensaje = err["msg"]
        errores.append(err)

    logger.warning(
        "Validation error %s %s → %s", request.method, request.url, errores
    )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "error": {
                    "type": "ValidationError",
                    # mensaje legible (el del primer campo inválido) + detalle completo
                    "detail": primer_mensaje or "Datos inválidos.",
                    "errors": errores,
                }
            }
        ),
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
    import uuid as _uuid

    # Código corto de referencia para que el usuario lo reporte y soporte lo cruce
    # con este log (en vez de un "error de red" engañoso y sin pistas).
    ref = _uuid.uuid4().hex[:8]
    logger.error(
        "Unhandled exception [ref=%s] %s %s → %s",
        ref,
        request.method,
        request.url,
        str(exc),
        exc_info=exc,
    )
    response = JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "ServerError",
                "detail": (
                    "Ocurrió un error inesperado en el servidor. "
                    f"Vuelve a intentarlo; si continúa, reporta este código a soporte: {ref}."
                ),
                "ref": ref,
            }
        },
    )
    _aplicar_cors(request, response)
    return response


def _aplicar_cors(request: Request, response: JSONResponse) -> None:
    """
    Agrega manualmente los headers CORS a la respuesta.

    Necesario SOLO para el handler de `Exception`: Starlette lo ejecuta en
    ServerErrorMiddleware, que está POR ENCIMA de CORSMiddleware, así que su
    respuesta no pasa por el middleware de CORS. Sin estos headers el navegador
    bloquea la respuesta, axios no ve ninguna y el usuario recibe
    "No se pudo contactar al servidor" en lugar del mensaje real con el código
    de referencia. (Los demás handlers corren dentro de CORSMiddleware y no
    necesitan esto.)
    """
    try:
        from app.config import settings

        origin = request.headers.get("origin")
        if not origin:
            return
        permitidos = settings.ALLOWED_ORIGINS or []
        if "*" in permitidos:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin in permitidos:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            return
        response.headers["Vary"] = "Origin"
    except Exception:  # nunca romper la respuesta de error por esto
        pass
