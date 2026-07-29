# app/services/ingresos_no_facturados_service.py
"""
Ingresos no facturados: órdenes de servicio COMPLETADAS o EN_PROGRESO que aún
no tienen factura, con su estado de cobro y los totales del periodo.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.orden_servicio import OrdenServicio

# Estados que representan trabajo real (ingreso devengado), excluye canceladas.
_ESTADOS_INGRESO = ("COMPLETADO", "EN_PROGRESO")


def _nombre_cliente(orden: OrdenServicio) -> str:
    c = getattr(orden, "cliente", None)
    return (
        getattr(c, "nombre_comercial", None)
        or getattr(c, "nombre_razon_social", None)
        or getattr(c, "razon_social", None)
        or ""
    )


def listar(
    db: Session,
    *,
    empresa_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    cobrado: Optional[bool] = None,
) -> dict:
    q = (
        db.query(OrdenServicio)
        .filter(
            OrdenServicio.factura_id.is_(None),
            OrdenServicio.estado.in_(_ESTADOS_INGRESO),
            OrdenServicio.activo.is_(True),
        )
    )
    if empresa_id:
        q = q.filter(OrdenServicio.empresa_id == empresa_id)
    if cliente_id:
        q = q.filter(OrdenServicio.cliente_id == cliente_id)
    if anio and mes:
        ultimo = calendar.monthrange(anio, mes)[1]
        q = q.filter(
            OrdenServicio.fecha_programada >= date(anio, mes, 1),
            OrdenServicio.fecha_programada <= date(anio, mes, ultimo),
        )
    if cobrado is not None:
        q = q.filter(OrdenServicio.cobrado.is_(cobrado))

    ordenes = q.order_by(OrdenServicio.fecha_programada.desc()).all()

    items = []
    total_nf = Decimal("0")
    total_cob = Decimal("0")
    num_cob = 0
    for o in ordenes:
        precio = o.precio_acordado or Decimal("0")
        total_nf += precio
        if o.cobrado:
            total_cob += precio
            num_cob += 1
        items.append({
            "orden_id": o.id,
            "folio_os": o.folio_os,
            "fecha_programada": o.fecha_programada,
            "cliente_id": o.cliente_id,
            "cliente_nombre": _nombre_cliente(o),
            "estado": o.estado,
            "precio_acordado": o.precio_acordado,
            "cobrado": o.cobrado,
            "fecha_cobro": o.fecha_cobro,
            "forma_cobro": o.forma_cobro,
        })

    return {
        "resumen": {
            "total_no_facturado": total_nf,
            "total_cobrado": total_cob,
            "total_pendiente": total_nf - total_cob,
            "num_ordenes": len(ordenes),
            "num_cobradas": num_cob,
        },
        "items": items,
    }


def marcar_cobro(
    db: Session,
    orden_id: UUID,
    *,
    cobrado: bool,
    fecha_cobro: Optional[date] = None,
    forma_cobro: Optional[str] = None,
) -> OrdenServicio:
    from fastapi import HTTPException

    orden = db.query(OrdenServicio).filter(OrdenServicio.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    orden.cobrado = cobrado
    if cobrado:
        orden.fecha_cobro = fecha_cobro or date.today()
        orden.forma_cobro = forma_cobro
    else:
        orden.fecha_cobro = None
        orden.forma_cobro = None
    db.add(orden)
    return orden
