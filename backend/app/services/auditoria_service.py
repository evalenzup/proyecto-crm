# app/services/auditoria_service.py
"""
Servicio de auditoría: registra cada acción crítica en la tabla auditoria_log.
Uso: llamar registrar() DESPUÉS de que la operación principal haya sido exitosa.
No hace commit — el endpoint ya lo hace. Usa try/except para no afectar el flujo.
"""
import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.auditoria import AuditoriaLog

logger = logging.getLogger("app")

# Constantes de acciones
CREAR_FACTURA = "CREAR_FACTURA"
TIMBRAR_FACTURA = "TIMBRAR_FACTURA"
CANCELAR_FACTURA = "CANCELAR_FACTURA"
ELIMINAR_FACTURA = "ELIMINAR_FACTURA"

CREAR_PAGO = "CREAR_PAGO"
TIMBRAR_PAGO = "TIMBRAR_PAGO"
CANCELAR_PAGO = "CANCELAR_PAGO"

CREAR_CLIENTE = "CREAR_CLIENTE"
ACTUALIZAR_CLIENTE = "ACTUALIZAR_CLIENTE"
ELIMINAR_CLIENTE = "ELIMINAR_CLIENTE"

CREAR_EMPRESA = "CREAR_EMPRESA"
ACTUALIZAR_EMPRESA = "ACTUALIZAR_EMPRESA"

CREAR_EGRESO = "CREAR_EGRESO"
ACTUALIZAR_EGRESO = "ACTUALIZAR_EGRESO"
ELIMINAR_EGRESO = "ELIMINAR_EGRESO"

CREAR_EMPRESA = "CREAR_EMPRESA"
ACTUALIZAR_EMPRESA = "ACTUALIZAR_EMPRESA"

CREAR_PRESUPUESTO = "CREAR_PRESUPUESTO"
ACTUALIZAR_PRESUPUESTO = "ACTUALIZAR_PRESUPUESTO"
CAMBIAR_ESTADO_PRESUPUESTO = "CAMBIAR_ESTADO_PRESUPUESTO"
ELIMINAR_PRESUPUESTO = "ELIMINAR_PRESUPUESTO"
ENVIAR_PRESUPUESTO = "ENVIAR_PRESUPUESTO"

LOGIN = "LOGIN"

ENVIAR_FACTURA_EMAIL = "ENVIAR_FACTURA_EMAIL"
ENVIAR_PAGO_EMAIL = "ENVIAR_PAGO_EMAIL"

EXPORTAR_EXCEL = "EXPORTAR_EXCEL"


def registrar(
    db: Session,
    *,
    accion: str,
    entidad: str,
    usuario_id: Optional[UUID] = None,
    usuario_email: Optional[str] = None,
    empresa_id: Optional[UUID] = None,
    entidad_id: Optional[str] = None,
    detalle: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
) -> None:
    """
    Registra una entrada en auditoria_log.
    Se llama dentro del contexto de una transacción activa (sin hacer commit).
    Captura excepciones para no interrumpir el flujo principal.
    """
    try:
        log = AuditoriaLog(
            accion=accion,
            entidad=entidad,
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            empresa_id=empresa_id,
            entidad_id=str(entidad_id) if entidad_id else None,
            detalle=json.dumps(detalle, default=str) if detalle else None,
            ip=ip,
        )
        db.add(log)
        db.flush()
    except Exception as exc:
        logger.warning("⚠️ auditoria_service.registrar: no se pudo registrar — %s", exc)


def get_ip(request) -> Optional[str]:
    """Extrae la IP real del request (considera X-Forwarded-For para proxies)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return getattr(request.client, "host", None)
