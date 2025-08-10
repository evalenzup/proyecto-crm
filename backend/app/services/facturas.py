# app/services/facturas.py
from __future__ import annotations

from uuid import UUID
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from datetime import date
from sqlalchemy import func, asc, desc
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import FacturaCreate, FacturaUpdate

# ────────────────────────────────────────────────────────────────
# FOLIO: consecutivo por empresa+serie (con bloqueo)

def siguiente_folio(db: Session, empresa_id: UUID, serie: str) -> int:
    # Bloquea las filas que coinciden para evitar carreras en concurrencia
    max_folio = (
        db.query(func.max(Factura.folio))
        .filter(Factura.empresa_id == empresa_id, Factura.serie == serie)
        .with_for_update()  # requiere estar dentro de transacción
        .scalar()
    ) or 0
    return max_folio + 1

# ────────────────────────────────────────────────────────────────
# Crear factura (usa folio auto si no viene)

def crear_factura(db: Session, payload: FacturaCreate) -> Factura:
    # Asegura transacción explícita para el FOR UPDATE
    with db.begin():
        serie = (payload.serie or "A").upper()
        folio = payload.folio
        if folio is None:
            folio = siguiente_folio(db, payload.empresa_id, serie)

        factura = Factura(
            empresa_id=payload.empresa_id,
            cliente_id=payload.cliente_id,
            serie=serie,
            folio=folio,
            moneda=payload.moneda,
            tipo_cambio=payload.tipo_cambio,
            estatus="BORRADOR",
            status_pago="NO_PAGADA",
            fecha_pago=payload.fecha_pago,
            fecha_cobro=payload.fecha_cobro,
            observaciones=payload.observaciones,
        )

        # conceptos
        subtotal = 0
        for c in payload.conceptos:
            importe = (c.cantidad or 0) * c.valor_unitario
            subtotal += importe
            factura.conceptos.append(
                FacturaDetalle(
                    tipo=c.tipo,
                    clave_producto=c.clave_producto,
                    clave_unidad=c.clave_unidad,
                    descripcion=c.descripcion,
                    cantidad=c.cantidad,
                    valor_unitario=c.valor_unitario,
                    importe=importe,
                    requiere_lote=c.requiere_lote or False,
                    lote=c.lote,
                )
            )

        factura.subtotal = subtotal
        factura.total = subtotal  # ajustes/impuestos aquí si aplica

        db.add(factura)

        try:
            db.flush()  # fuerza INSERT y checa el UNIQUE
        except IntegrityError:
            # Si otro proceso ganó el mismo folio, reintenta 1 vez con nuevo folio
            db.rollback()
            with db.begin():
                nuevo_folio = siguiente_folio(db, payload.empresa_id, serie)
                factura.folio = nuevo_folio
                db.add(factura)
                db.flush()

        db.refresh(factura)
        return factura

# ────────────────────────────────────────────────────────────────

def actualizar_factura(db: Session, factura_id: UUID, payload: FacturaUpdate) -> Optional[Factura]:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        return None
    if payload.serie is not None:
        factura.serie = payload.serie.upper()
    if payload.folio is not None:
        factura.folio = payload.folio
    if payload.moneda is not None:
        factura.moneda = payload.moneda
    if payload.tipo_cambio is not None:
        factura.tipo_cambio = payload.tipo_cambio
    if payload.fecha_pago is not None:
        factura.fecha_pago = payload.fecha_pago
    if payload.fecha_cobro is not None:
        factura.fecha_cobro = payload.fecha_cobro
    if payload.status_pago is not None:
        factura.status_pago = payload.status_pago
    if payload.estatus is not None:
        factura.estatus = payload.estatus
    if payload.observaciones is not None:
        factura.observaciones = payload.observaciones

    # Reemplazo total de conceptos si vienen
    if payload.conceptos is not None:
        # borra existentes
        db.query(FacturaDetalle).where(FacturaDetalle.factura_id == factura.id).delete()
        subtotal = 0
        for c in payload.conceptos:
            importe = (c.cantidad or 0) * c.valor_unitario
            subtotal += importe
            db.add(
                FacturaDetalle(
                    factura_id=factura.id,
                    tipo=c.tipo,
                    clave_producto=c.clave_producto,
                    clave_unidad=c.clave_unidad,
                    descripcion=c.descripcion,
                    cantidad=c.cantidad,
                    valor_unitario=c.valor_unitario,
                    importe=importe,
                    requiere_lote=c.requiere_lote or False,
                    lote=c.lote,
                )
            )
        factura.subtotal = subtotal
        factura.total = subtotal

    db.commit()
    db.refresh(factura)
    return factura

# ────────────────────────────────────────────────────────────────
# Búsqueda por empresa+serie+folio

def obtener_por_serie_folio(
    db: Session, empresa_id: UUID, serie: str, folio: int
) -> Optional[Factura]:
    return (
        db.query(Factura)
        .options(selectinload(Factura.conceptos))
        .filter(
            Factura.empresa_id == empresa_id,
            Factura.serie == serie.upper(),
            Factura.folio == folio,
        )
        .first()
    )

# ────────────────────────────────────────────────────────────────
# Timbrar / Cancelar (simulado)

def timbrar_factura(db: Session, factura_id: UUID) -> Optional[Factura]:
    fac = db.query(Factura).filter(Factura.id == factura_id).first()
    if not fac:
        return None
    if fac.estatus != "BORRADOR":
        raise ValueError("Solo se puede timbrar una factura en BORRADOR")
    fac.estatus = "TIMBRADA"
    db.commit()
    db.refresh(fac)
    return fac


def cancelar_factura(db: Session, factura_id: UUID) -> Optional[Factura]:
    fac = db.query(Factura).filter(Factura.id == factura_id).first()
    if not fac:
        return None
    if fac.estatus != "TIMBRADA":
        raise ValueError("Solo se puede cancelar una factura TIMBRADA")
    fac.estatus = "CANCELADA"
    db.commit()
    db.refresh(fac)
    return fac

def listar_facturas(
    db: Session,
    *,
    empresa_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    serie: Optional[str] = None,
    folio_min: Optional[int] = None,
    folio_max: Optional[int] = None,
    estatus: Optional[str] = None,       # BORRADOR | TIMBRADA | CANCELADA
    status_pago: Optional[str] = None,   # PAGADA | NO_PAGADA
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    order_by: str = "serie_folio",       # serie_folio | fecha | total
    order_dir: str = "asc",              # asc | desc
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Factura], int]:
    q = (
        db.query(Factura)
        .options(selectinload(Factura.conceptos))
    )

    # ── Filtros
    if empresa_id:
        q = q.filter(Factura.empresa_id == empresa_id)
    if cliente_id:
        q = q.filter(Factura.cliente_id == cliente_id)
    if serie:
        q = q.filter(Factura.serie == serie.upper())
    if folio_min is not None:
        q = q.filter(Factura.folio >= folio_min)
    if folio_max is not None:
        q = q.filter(Factura.folio <= folio_max)
    if estatus:
        q = q.filter(Factura.estatus == estatus.upper())
    if status_pago:
        q = q.filter(Factura.status_pago == status_pago.upper())
    if fecha_desde:
        q = q.filter(Factura.creado_en >= fecha_desde)
    if fecha_hasta:
        # +1 día si quieres inclusivo por fecha
        q = q.filter(Factura.creado_en <= fecha_hasta)

    # Total antes de paginar
    total = q.with_entities(func.count(Factura.id)).scalar() or 0

    # ── Orden
    dir_fn = asc if order_dir.lower() == "asc" else desc
    if order_by == "fecha":
        q = q.order_by(dir_fn(Factura.creado_en))
    elif order_by == "total":
        q = q.order_by(dir_fn(Factura.total))
    else:  # serie_folio
        q = q.order_by(dir_fn(Factura.serie), dir_fn(Factura.folio))

    # Paginación
    items = q.offset(offset).limit(limit).all()
    return items, total