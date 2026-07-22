# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar configuración de logging
from app.core.logger import logger
from app.config import settings
from app.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
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
from app.api.cobranza import router as cobranza_router
from app.api.notificaciones import router as notificaciones_router
from app.api.health import router as health_router
from app.api.auditoria import router as auditoria_router
from app.api.mapa import router as mapa_router
from app.api.reportes import router as reportes_router
from app.api.operativo import servicios_router, tecnicos_router, unidades_router
from app.api.public import router as public_router
from app.api.ordenes_servicio import router as ordenes_router
from app.api.contratos import router as contratos_router
from app.api.programacion_facturas import router as prog_facturas_router
from app.api.equipos import router as equipos_router
from app.api.certificados import router as certificados_router

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter


from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler


_SAT_SYNC_LOCK_KEY = 0x53415453  # "SATS" en hex — clave fija para pg_advisory_lock


def _sync_cancelaciones_job():
    """
    Cron 1x/día: verifica en el SAT todas las facturas EN_CANCELACION.

    Usa pg_try_advisory_lock para evitar ejecución doble si hay más de una instancia
    del proceso web activa (blue/green deploy, reinicio sin apagado graceful, etc.).
    Si otra instancia ya tiene el lock, este invocation se omite silenciosamente.
    """
    from app.database import SessionLocal
    from app.models.factura import Factura
    from app.services import sat_cfdi_service as sat_svc
    from sqlalchemy import text
    from sqlalchemy.orm import joinedload

    db = SessionLocal()
    try:
        # ── Lock distribuido vía PostgreSQL advisory lock (transaction-level) ──
        # pg_try_advisory_xact_lock se libera automáticamente en commit/rollback,
        # sin depender del ciclo de vida de la conexión en el pool de SQLAlchemy.
        # Esto evita que el lock quede pegado a una conexión idle del pool.
        lock_acquired = db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": _SAT_SYNC_LOCK_KEY}
        ).scalar()

        if not lock_acquired:
            logger.info("[SAT Sync] Otra instancia ya ejecuta el cron — saltando.")
            db.rollback()
            return

        # ── Cargar facturas con joinedload para evitar N+1 ────────────────────
        pendientes = (
            db.query(Factura)
            .options(
                joinedload(Factura.empresa),
                joinedload(Factura.cliente),
            )
            .filter(Factura.estatus == "EN_CANCELACION", Factura.cfdi_uuid.isnot(None))
            .all()
        )
        logger.info("[SAT Sync] Verificando %d facturas EN_CANCELACION", len(pendientes))

        for f in pendientes:
            rfc_emisor = getattr(f.empresa, "rfc", None) or ""
            rfc_receptor = getattr(f.cliente, "rfc", None) or ""
            try:
                acuse = sat_svc.consultar_cfdi(
                    rfc_emisor=rfc_emisor.strip().upper(),
                    rfc_receptor=rfc_receptor.strip().upper(),
                    total=float(f.total or 0),
                    uuid=f.cfdi_uuid,
                )
                nuevo_estatus, hubo_cambio = sat_svc.aplicar_acuse_sat(f, acuse)
                if hubo_cambio:
                    db.add(f)
                    logger.info(
                        "[SAT Sync] Factura %s-%s → %s",
                        f.serie, f.folio, nuevo_estatus,
                    )
                else:
                    logger.debug("[SAT Sync] Factura %s-%s sin cambio", f.serie, f.folio)
            except Exception as exc:
                logger.warning("[SAT Sync] Error verificando factura %s: %s", f.id, exc)

        # ── Complementos de pago EN_CANCELACION ───────────────────────────────
        from app.models.pago import Pago, EstatusPago

        pagos_pend = (
            db.query(Pago)
            .options(joinedload(Pago.empresa), joinedload(Pago.cliente))
            .filter(Pago.estatus == EstatusPago.EN_CANCELACION, Pago.uuid.isnot(None))
            .all()
        )
        logger.info("[SAT Sync] Verificando %d pagos EN_CANCELACION", len(pagos_pend))

        for p in pagos_pend:
            try:
                acuse = sat_svc.consultar_cfdi(
                    rfc_emisor=(getattr(p.empresa, "rfc", None) or "").strip().upper(),
                    rfc_receptor=(getattr(p.cliente, "rfc", None) or "").strip().upper(),
                    total=0.0,  # los complementos de pago timbran con Total=0
                    uuid=p.uuid,
                )
                nuevo_estatus, hubo_cambio = sat_svc.aplicar_acuse_sat_pago(p, acuse)
                if hubo_cambio:
                    db.add(p)
                    logger.info("[SAT Sync] Pago %s → %s", p.uuid, nuevo_estatus)
            except Exception as exc:
                logger.warning("[SAT Sync] Error verificando pago %s: %s", p.id, exc)

        # commit libera el xact_lock automáticamente
        db.commit()
    except Exception as exc:
        logger.error("[SAT Sync] Error general en cron: %s", exc)
        db.rollback()
    finally:
        db.close()


def _ejecutar_programaciones_job():
    """Cron 1x/día (3:05 AM): genera las facturas programadas para hoy."""
    from app.database import SessionLocal
    from app.services.programacion_factura_service import ejecutar_programaciones_pendientes

    db = SessionLocal()
    try:
        stats = ejecutar_programaciones_pendientes(db)
        logger.info("[ProgFacturas] Cron finalizado: %s", stats)
    except Exception as exc:
        logger.error("[ProgFacturas] Error en cron: %s", exc)
    finally:
        db.close()


_scheduler = BackgroundScheduler(timezone="America/Mexico_City")
_scheduler.add_job(
    _sync_cancelaciones_job,
    trigger="cron",
    hour=3,        # 3:00 AM hora México
    minute=0,
    id="sync_cancelaciones_sat",
    replace_existing=True,
)
_scheduler.add_job(
    _ejecutar_programaciones_job,
    trigger="cron",
    hour=3,        # 3:05 AM hora México
    minute=5,
    id="ejecutar_programaciones_facturas",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    _scheduler.start()
    logger.info("[SAT Sync] Scheduler iniciado — cron diario 03:00 AM MX")
    yield
    _scheduler.shutdown(wait=False)
    logger.info("[SAT Sync] Scheduler detenido")


app = FastAPI(
    title="ERP/CRM Desarrollo NORTON",
    description="Un ERP/CRM para fumigaciones, jardinería y extintores.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

app.include_router(
    cobranza_router,
    prefix="/api/cobranza",
    tags=["cobranza"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    notificaciones_router,
    prefix="/api/notificaciones",
    tags=["notificaciones"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(health_router, prefix="/health", tags=["health"])

app.include_router(
    auditoria_router,
    prefix="/api/auditoria",
    tags=["auditoria"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    mapa_router,
    prefix="/api/mapa",
    tags=["mapa"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    reportes_router,
    prefix="/api/reportes",
    tags=["reportes"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    servicios_router,
    prefix="/api/servicios-operativos",
    tags=["servicios-operativos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    tecnicos_router,
    prefix="/api/tecnicos",
    tags=["tecnicos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    unidades_router,
    prefix="/api/unidades",
    tags=["unidades"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    public_router,
    prefix="/api/public",
    tags=["public"],
)

app.include_router(
    ordenes_router,
    prefix="/api/ordenes-servicio",
    tags=["ordenes-servicio"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    contratos_router,
    prefix="/api/contratos",
    tags=["contratos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    prog_facturas_router,
    prefix="/api/programacion-facturas",
    tags=["programacion-facturas"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    equipos_router,
    prefix="/api/equipos",
    tags=["equipos"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    certificados_router,
    prefix="/api/certificados",
    tags=["certificados"],
    responses={404: {"description": "No encontrado"}},
)

# Registrar manejadores globales de excepción
# Orden importa: los más específicos primero
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info("Arrancando aplicación FastAPI")

# Ya no usamos Base.metadata.create_all() aquí;
# las migraciones de Alembic se encargarán del esquema.
