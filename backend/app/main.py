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
from app.api.planes_servicio import router as planes_servicio_router
from app.api.ingresos_no_facturados import router as ingresos_nf_router

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter


from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler


# Una clave de advisory lock POR VENTANA, no una compartida. Las dos ventanas
# procesan conjuntos disjuntos de comprobantes, así que pueden correr a la vez sin
# pisarse; cada una conserva su candado para lo que el candado sí protege: que dos
# instancias del proceso web no procesen el mismo comprobante.
#
# Con una sola clave compartida pasaba esto: ambos jobs se registran en el mismo
# instante, sus intervalos quedan en fase, y cada 2 h el de seguimiento disparaba en
# el mismo segundo que uno de la ventana caliente. Como la caliente toma el candado
# primero, el de seguimiento se saltaba SIEMPRE — 22 de 22 veces, todas a las :49:06.
# Estuvo 45 horas sin correr ni una sola vez y nadie lo notó.
_SAT_SYNC_LOCK_KEYS = {
    True: 0x53415453,   # "SATS" — ventana caliente
    False: 0x53415454,  # "SATT" — seguimiento
}

# Frontera entre las dos ventanas de verificación (ver _sync_cancelaciones_job).
HORAS_VENTANA_CALIENTE = 4


def _reintentar_acuse(db, doc) -> None:
    """
    Vuelve a intentar la descarga del acuse sellado si aún no se tiene.

    La descarga original se hace una sola vez, segundos después de enviar la
    solicitud, cuando el PAC muchas veces todavía no lo publicó. Sin reintento,
    un acuse que aparece dos minutos más tarde no se recogía nunca: el cron
    pasaba cada 15 min junto al comprobante y lo ignoraba (caso A-2291, dos días
    EN_CANCELACION sin acuse archivado).
    """
    if getattr(doc, "cancelacion_acuse_path", None):
        return

    # Si el trámite no salió por el PAC, su storage no va a tener acuse jamás y
    # reintentarlo cada 15 minutos es ruido permanente —cuatro peticiones por
    # vuelta contra algo que por construcción no existe—, además de ensuciar el
    # log justo donde uno busca problemas de verdad. Lo delata el código:
    # vacío = nunca pasó por el PAC; SAT-PORTAL = se hizo en el portal del SAT.
    from app.services.factura_service import CODIGO_SAT_PORTAL

    code = (getattr(doc, "cancelacion_code", None) or "").strip().upper()
    if not code or code == CODIGO_SAT_PORTAL:
        return

    try:
        from app.services.factura_service import _archivar_acuse_cancelacion

        _archivar_acuse_cancelacion(db, doc)
    except Exception as exc:  # noqa: BLE001 — nunca debe tumbar la sincronización
        logger.debug("Reintento de acuse sin éxito para %s: %s", doc.id, exc)


def _sync_cancelaciones_job(solo_recientes: bool = True):
    """
    Verifica en el SAT los comprobantes EN_CANCELACION (facturas y complementos).

    Corre en dos ventanas porque hay dos fenómenos con escalas de tiempo muy
    distintas:

      · ``solo_recientes=True``  — solicitudes de menos de HORAS_VENTANA_CALIENTE
        horas, cada 15 min. Es la ventana donde importa la frecuencia: si el PAC
        acusó recibo pero el SAT nunca registró la solicitud, el SAT lo publica
        de inmediato (EstatusCancelacion deja de estar vacío al instante), y
        detectarlo el mismo día permite reintentar o hacer el trámite desde el
        portal del SAT.

      · ``solo_recientes=False`` — todo lo demás, cada 2 h. Aquí ya sólo se
        espera la respuesta del receptor, que tiene 72 horas hábiles: consultar
        más seguido es preguntar cientos de veces por algo que cambia una vez.

    Las dos ventanas son disjuntas, así que ningún comprobante se procesa dos
    veces en la misma pasada.

    Usa pg_try_advisory_lock para evitar ejecución doble si hay más de una instancia
    del proceso web activa (blue/green deploy, reinicio sin apagado graceful, etc.).
    Si otra instancia ya tiene el lock, este invocation se omite silenciosamente.
    """
    from datetime import datetime, timedelta

    from app.database import SessionLocal
    from app.models.factura import Factura
    from app.services import cancelacion_intento_service as bitacora_svc
    from app.services import notificacion_cancelacion_service as notif_cancelacion_svc
    from app.services import sat_cfdi_service as sat_svc
    from sqlalchemy import or_, text
    from sqlalchemy.orm import joinedload

    # fecha_solicitud_cancelacion se escribe con datetime.utcnow()
    corte = datetime.utcnow() - timedelta(hours=HORAS_VENTANA_CALIENTE)
    ventana = "reciente" if solo_recientes else "seguimiento"

    db = SessionLocal()
    try:
        # ── Lock distribuido vía PostgreSQL advisory lock (transaction-level) ──
        # pg_try_advisory_xact_lock se libera automáticamente en commit/rollback,
        # sin depender del ciclo de vida de la conexión en el pool de SQLAlchemy.
        # Esto evita que el lock quede pegado a una conexión idle del pool.
        lock_acquired = db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": _SAT_SYNC_LOCK_KEYS[bool(solo_recientes)]},
        ).scalar()

        if not lock_acquired:
            # Nombrar la ventana: un salteo silencioso e indistinguible fue lo que
            # dejó pasar 45 horas sin que el seguimiento corriera nunca.
            logger.warning(
                "[SAT Sync/%s] Otra instancia ya ejecuta esta ventana — saltando.",
                ventana,
            )
            db.rollback()
            return

        # ── Cargar facturas con joinedload para evitar N+1 ────────────────────
        q_fact = (
            db.query(Factura)
            .options(
                joinedload(Factura.empresa),
                joinedload(Factura.cliente),
            )
            .filter(Factura.estatus == "EN_CANCELACION", Factura.cfdi_uuid.isnot(None))
        )
        if solo_recientes:
            # Sin fecha registrada también entra aquí: aplicar_acuse_sat la ancla
            # en la primera pasada y a partir de ahí ya cae en la ventana que toca.
            q_fact = q_fact.filter(
                or_(
                    Factura.fecha_solicitud_cancelacion.is_(None),
                    Factura.fecha_solicitud_cancelacion >= corte,
                )
            )
        else:
            q_fact = q_fact.filter(Factura.fecha_solicitud_cancelacion < corte)
        pendientes = q_fact.all()
        logger.info(
            "[SAT Sync/%s] Verificando %d facturas EN_CANCELACION",
            ventana, len(pendientes),
        )

        no_verificables = 0
        for f in pendientes:
            try:
                rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(f)
                acuse = sat_svc.consultar_cfdi(
                    rfc_emisor=rfc_emisor,
                    rfc_receptor=rfc_receptor,
                    total=total,
                    uuid=f.cfdi_uuid,
                )
                if not acuse.encontrado:
                    # El RFC del receptor o el total ya no coinciden con el XML
                    # timbrado: la factura no se puede verificar contra el SAT.
                    # aplicar_acuse_sat tampoco la tocaría; lo registramos con
                    # folio para poder darles seguimiento.
                    no_verificables += 1
                    logger.warning(
                        "[SAT Sync] Factura %s-%s NO verificable en SAT (%s) — sin cambios",
                        f.serie, f.folio, acuse.codigo_estatus,
                    )
                    continue
                _reintentar_acuse(db, f)
                estatus_previo = f.estatus
                nuevo_estatus, hubo_cambio = sat_svc.aplicar_acuse_sat(f, acuse)
                if hubo_cambio:
                    db.add(f)
                    bitacora_svc.cerrar_si_resuelto(db, f, estatus_previo, nuevo_estatus)
                    notif_cancelacion_svc.avisar_resolucion(
                        db, f, estatus_previo, nuevo_estatus, acuse
                    )
                    logger.info(
                        "[SAT Sync/%s] Factura %s-%s → %s",
                        ventana, f.serie, f.folio, nuevo_estatus,
                    )
                else:
                    logger.debug("[SAT Sync] Factura %s-%s sin cambio", f.serie, f.folio)
            except Exception as exc:
                logger.warning("[SAT Sync] Error verificando factura %s: %s", f.id, exc)

        if no_verificables:
            logger.warning(
                "[SAT Sync] %d factura(s) EN_CANCELACION no verificables en el SAT "
                "(RFC del receptor o total distintos al XML timbrado)",
                no_verificables,
            )

        # ── Complementos de pago EN_CANCELACION ───────────────────────────────
        from app.models.pago import Pago, EstatusPago

        q_pago = (
            db.query(Pago)
            .options(joinedload(Pago.empresa), joinedload(Pago.cliente))
            .filter(Pago.estatus == EstatusPago.EN_CANCELACION, Pago.uuid.isnot(None))
        )
        if solo_recientes:
            q_pago = q_pago.filter(
                or_(
                    Pago.fecha_solicitud_cancelacion.is_(None),
                    Pago.fecha_solicitud_cancelacion >= corte,
                )
            )
        else:
            q_pago = q_pago.filter(Pago.fecha_solicitud_cancelacion < corte)
        pagos_pend = q_pago.all()
        logger.info(
            "[SAT Sync/%s] Verificando %d pagos EN_CANCELACION",
            ventana, len(pagos_pend),
        )

        for p in pagos_pend:
            try:
                rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(p)
                acuse = sat_svc.consultar_cfdi(
                    rfc_emisor=rfc_emisor,
                    rfc_receptor=rfc_receptor,
                    total=total,  # los complementos de pago timbran con Total=0
                    uuid=p.uuid,
                )
                _reintentar_acuse(db, p)
                estatus_previo = getattr(p.estatus, "value", p.estatus)
                nuevo_estatus, hubo_cambio = sat_svc.aplicar_acuse_sat_pago(p, acuse)
                if hubo_cambio:
                    db.add(p)
                    bitacora_svc.cerrar_si_resuelto(db, p, estatus_previo, nuevo_estatus)
                    notif_cancelacion_svc.avisar_resolucion(
                        db, p, estatus_previo, nuevo_estatus, acuse
                    )
                    logger.info(
                        "[SAT Sync/%s] Pago %s → %s", ventana, p.uuid, nuevo_estatus
                    )
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


def _avisos_planes_servicio_job():
    """
    Cron 1x/día (3:10 AM): avisa los servicios de contrato que caen en 3 días
    y aún no tienen orden programada. Una notificación por periodo.
    """
    from datetime import date, timedelta
    from app.database import SessionLocal
    from app.models.plan_servicio import PlanServicio
    from app.models.orden_servicio import OrdenServicio
    from app.services import plan_servicio_service as plan_svc
    from app.services import notificacion_service as notif_svc

    db = SessionLocal()
    try:
        objetivo = date.today() + timedelta(days=3)
        planes = (
            db.query(PlanServicio)
            .filter(PlanServicio.activo.is_(True), PlanServicio.vigencia_desde <= objetivo)
            .all()
        )
        avisos = 0
        for plan in planes:
            if plan.vigencia_hasta and plan.vigencia_hasta < objetivo:
                continue
            fechas = plan_svc.periodos_del_mes(plan, objetivo.year, objetivo.month)
            if objetivo not in fechas:
                continue
            # ¿Ya hay orden del plan cerca de esa fecha (±3 días)?
            ya = (
                db.query(OrdenServicio)
                .filter(
                    OrdenServicio.plan_id == plan.id,
                    OrdenServicio.fecha_programada >= objetivo - timedelta(days=3),
                    OrdenServicio.fecha_programada <= objetivo + timedelta(days=3),
                )
                .first()
            )
            if ya:
                continue
            cliente = getattr(plan.cliente, "nombre_comercial", None) or "cliente"
            try:
                notif_svc.crear_notificacion(
                    db=db,
                    empresa_id=plan.empresa_id,
                    tipo=notif_svc.ADVERTENCIA,
                    titulo="Servicio de contrato por programar",
                    mensaje=f"El plan de {cliente} tiene un servicio el {objetivo:%d/%m/%Y} y aún no está programado.",
                    metadata={"plan_id": str(plan.id), "fecha": str(objetivo)},
                )
                avisos += 1
            except Exception:
                pass
        db.commit()
        logger.info("[Planes] Avisos de servicios por programar: %d", avisos)
    except Exception as exc:
        logger.error("[Planes] Error en cron de avisos: %s", exc)
        db.rollback()
    finally:
        db.close()


_scheduler = BackgroundScheduler(timezone="America/Mexico_City")
# Ventana caliente: solicitudes de menos de HORAS_VENTANA_CALIENTE horas.
_scheduler.add_job(
    _sync_cancelaciones_job,
    trigger="interval",
    minutes=15,
    kwargs={"solo_recientes": True},
    id="sync_cancelaciones_sat",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
)
# Seguimiento: el resto, que sólo espera la respuesta del receptor (72 h hábiles).
_scheduler.add_job(
    _sync_cancelaciones_job,
    trigger="interval",
    hours=2,
    kwargs={"solo_recientes": False},
    id="sync_cancelaciones_sat_seguimiento",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
)
_scheduler.add_job(
    _ejecutar_programaciones_job,
    trigger="cron",
    hour=3,        # 3:05 AM hora México
    minute=5,
    id="ejecutar_programaciones_facturas",
    replace_existing=True,
)
_scheduler.add_job(
    _avisos_planes_servicio_job,
    trigger="cron",
    hour=3,        # 3:10 AM hora México
    minute=10,
    id="avisos_planes_servicio",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    _scheduler.start()
    logger.info(
        "[SAT Sync] Scheduler iniciado — cancelaciones recientes cada 15 min, "
        "seguimiento cada 2 h; demás cron 03:00 AM MX"
    )
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
    # Sin esto el navegador no deja al front leer X-Restriccion y no podría
    # distinguir un 403 por restricción de cuenta de uno por permisos.
    expose_headers=["X-Restriccion"],
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

app.include_router(
    planes_servicio_router,
    prefix="/api/planes-servicio",
    tags=["planes-servicio"],
    responses={404: {"description": "No encontrado"}},
)

app.include_router(
    ingresos_nf_router,
    prefix="/api/ingresos-no-facturados",
    tags=["ingresos-no-facturados"],
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
