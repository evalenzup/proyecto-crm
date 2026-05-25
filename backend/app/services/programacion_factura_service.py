# app/services/programacion_factura_service.py
"""
Servicio de programación de facturas.

Responsabilidades:
  - CRUD de ProgramacionFactura
  - Cálculo de la próxima fecha de ejecución
  - Ejecución del cron: crear → timbrar (opt.) → enviar (opt.)
"""
from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.programacion_factura import ProgramacionFactura
from app.schemas.programacion_factura import (
    ProgramacionFacturaCreate,
    ProgramacionFacturaUpdate,
)

logger = logging.getLogger(__name__)


# ─── Helpers de fecha ─────────────────────────────────────────────────────────

def _add_months(d: date, months: int) -> date:
    """Suma N meses a una fecha sin depender de dateutil."""
    month = d.month - 1 + months
    year  = d.year + month // 12
    month = month % 12 + 1
    day   = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calcular_proxima(periodicidad: str, desde: date) -> Optional[date]:
    """
    Devuelve la siguiente fecha de ejecución a partir de `desde`.
    Retorna None para periodicidad 'unica' (no se repite).
    """
    if periodicidad == "unica":
        return None
    elif periodicidad == "semanal":
        return desde + timedelta(weeks=1)
    elif periodicidad == "quincenal":
        return desde + timedelta(days=15)
    elif periodicidad == "mensual":
        return _add_months(desde, 1)
    elif periodicidad == "bimestral":
        return _add_months(desde, 2)
    elif periodicidad == "trimestral":
        return _add_months(desde, 3)
    elif periodicidad == "semestral":
        return _add_months(desde, 6)
    elif periodicidad == "anual":
        return _add_months(desde, 12)
    return None


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def crear_programacion(db: Session, payload: ProgramacionFacturaCreate) -> ProgramacionFactura:
    prog = ProgramacionFactura(
        empresa_id          = payload.empresa_id,
        cliente_id          = payload.cliente_id,
        nombre              = payload.nombre,
        serie               = payload.serie or "A",
        tipo_comprobante    = payload.tipo_comprobante,
        forma_pago          = payload.forma_pago,
        metodo_pago         = payload.metodo_pago,
        uso_cfdi            = payload.uso_cfdi,
        moneda              = payload.moneda,
        lugar_expedicion    = payload.lugar_expedicion,
        condiciones_pago    = payload.condiciones_pago,
        observaciones       = payload.observaciones,
        retencion_local_desc = payload.retencion_local_desc,
        retencion_local_tasa = payload.retencion_local_tasa,
        conceptos           = [c.model_dump(mode="json") for c in payload.conceptos],
        periodicidad        = payload.periodicidad,
        proxima_ejecucion   = payload.proxima_ejecucion,
        fecha_fin           = payload.fecha_fin,
        auto_timbrar        = payload.auto_timbrar,
        auto_enviar         = payload.auto_enviar,
        emails_destino      = payload.emails_destino or [],
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


def obtener_programacion(db: Session, prog_id: UUID) -> ProgramacionFactura:
    prog = db.query(ProgramacionFactura).filter(ProgramacionFactura.id == prog_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    return prog


def listar_programaciones(
    db: Session,
    empresa_id: Optional[UUID] = None,
    activo: Optional[bool] = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list, int]:
    q = db.query(ProgramacionFactura)
    if empresa_id:
        q = q.filter(ProgramacionFactura.empresa_id == empresa_id)
    if activo is not None:
        q = q.filter(ProgramacionFactura.activo == activo)
    total = q.count()
    items = q.order_by(ProgramacionFactura.proxima_ejecucion).offset(offset).limit(limit).all()
    return items, total


def actualizar_programacion(
    db: Session, prog_id: UUID, payload: ProgramacionFacturaUpdate
) -> ProgramacionFactura:
    prog = obtener_programacion(db, prog_id)
    data = payload.model_dump(exclude_unset=True)

    if "conceptos" in data and data["conceptos"] is not None:
        data["conceptos"] = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else c
            for c in payload.conceptos
        ]

    for field, value in data.items():
        setattr(prog, field, value)

    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


def eliminar_programacion(db: Session, prog_id: UUID) -> None:
    prog = obtener_programacion(db, prog_id)
    db.delete(prog)
    db.commit()


# ─── Ejecución del cron ───────────────────────────────────────────────────────

def _construir_factura_create(prog: ProgramacionFactura, hoy: date):
    """Arma un FacturaCreate a partir de la plantilla."""
    from app.schemas.factura import FacturaCreate, FacturaDetalleIn

    conceptos_in = []
    for c in (prog.conceptos or []):
        conceptos_in.append(FacturaDetalleIn(
            tipo                = c.get("tipo"),
            producto_servicio_id = c.get("producto_servicio_id"),
            clave_producto      = c["clave_producto"],
            clave_unidad        = c["clave_unidad"],
            descripcion         = c["descripcion"],
            cantidad            = Decimal(str(c.get("cantidad", "1"))),
            valor_unitario      = Decimal(str(c.get("valor_unitario", "0"))),
            descuento           = Decimal(str(c.get("descuento", "0"))),
            iva_tasa            = Decimal(str(c["iva_tasa"])) if c.get("iva_tasa") else None,
            ret_iva_tasa        = Decimal(str(c["ret_iva_tasa"])) if c.get("ret_iva_tasa") else None,
            ret_isr_tasa        = Decimal(str(c["ret_isr_tasa"])) if c.get("ret_isr_tasa") else None,
        ))

    from datetime import datetime as dt
    fecha_emision = dt.combine(hoy, dt.min.time())

    return FacturaCreate(
        empresa_id          = prog.empresa_id,
        cliente_id          = prog.cliente_id,
        serie               = prog.serie or "A",
        tipo_comprobante    = prog.tipo_comprobante or "I",
        forma_pago          = prog.forma_pago,
        metodo_pago         = prog.metodo_pago,
        uso_cfdi            = prog.uso_cfdi,
        moneda              = prog.moneda or "MXN",
        lugar_expedicion    = prog.lugar_expedicion,
        condiciones_pago    = prog.condiciones_pago,
        observaciones       = prog.observaciones,
        retencion_local_desc = prog.retencion_local_desc,
        retencion_local_tasa = (
            Decimal(prog.retencion_local_tasa) if prog.retencion_local_tasa else None
        ),
        fecha_emision       = fecha_emision,
        conceptos           = conceptos_in,
    )


def ejecutar_programaciones_pendientes(db: Session) -> dict:
    """
    Busca todas las programaciones activas cuya proxima_ejecucion <= hoy
    y las ejecuta: crea la factura, timbra y envía según configuración.
    Llamado por el cron diario en main.py.
    """
    from app.services.factura_service import crear_factura, timbrar_factura
    from app.services import email_sender

    hoy = date.today()
    pendientes = (
        db.query(ProgramacionFactura)
        .filter(
            ProgramacionFactura.activo == True,
            ProgramacionFactura.proxima_ejecucion <= hoy,
            or_(
                ProgramacionFactura.fecha_fin.is_(None),
                ProgramacionFactura.fecha_fin >= hoy,
            ),
        )
        .all()
    )

    stats = {"procesadas": 0, "timbradas": 0, "enviadas": 0, "errores": 0}
    logger.info("[ProgFacturas] %d programaciones pendientes para %s", len(pendientes), hoy)

    for prog in pendientes:
        try:
            # 1 — Crear factura BORRADOR
            payload = _construir_factura_create(prog, hoy)
            factura = crear_factura(db, payload)
            db.flush()
            logger.info("[ProgFacturas] Factura creada: %s-%s (prog %s)", factura.serie, factura.folio, prog.id)

            # 2 — Timbrar si corresponde
            timbrado_ok = False
            if prog.auto_timbrar:
                try:
                    timbrar_factura(db, factura.id)
                    timbrado_ok = True
                    stats["timbradas"] += 1
                    logger.info("[ProgFacturas] Timbrada: %s-%s", factura.serie, factura.folio)
                except Exception as e:
                    logger.error("[ProgFacturas] Error timbrando %s-%s: %s", factura.serie, factura.folio, e)

            # 3 — Enviar por correo si corresponde (solo si timbró OK)
            if prog.auto_enviar and timbrado_ok and prog.emails_destino:
                for email in prog.emails_destino:
                    try:
                        email_sender.send_invoice_email(
                            db=db,
                            empresa_id=prog.empresa_id,
                            factura_id=factura.id,
                            recipient_email=email,
                        )
                        stats["enviadas"] += 1
                        logger.info("[ProgFacturas] Email enviado a %s (factura %s-%s)", email, factura.serie, factura.folio)
                    except Exception as e:
                        logger.warning("[ProgFacturas] Error enviando email a %s: %s", email, e)

            # 4 — Actualizar programación
            prog.ultima_ejecucion   = datetime.utcnow()
            prog.facturas_generadas += 1
            proxima = calcular_proxima(prog.periodicidad, hoy)

            if proxima is None or (prog.fecha_fin and proxima > prog.fecha_fin):
                prog.activo           = False
                prog.proxima_ejecucion = hoy   # dejar la última fecha ejecutada
            else:
                prog.proxima_ejecucion = proxima

            db.add(prog)
            db.commit()
            stats["procesadas"] += 1

        except Exception as e:
            db.rollback()
            logger.error("[ProgFacturas] Error procesando programacion %s: %s", prog.id, e)
            stats["errores"] += 1

    logger.info("[ProgFacturas] Resumen: %s", stats)
    return stats
