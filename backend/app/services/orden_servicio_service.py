# app/services/orden_servicio_service.py
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from datetime import date

from fastapi import HTTPException
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.models.orden_servicio import OrdenServicio, HistorialEstadoOS
from app.schemas.orden_servicio import (
    OrdenServicioCreate,
    OrdenServicioUpdate,
    CambioEstadoOS,
)


# ── Folio ────────────────────────────────────────────────────────────────────

def _generar_folio(db: Session, empresa_id: UUID) -> str:
    """Genera folio correlativo por empresa: OS-0001, OS-0002, ..."""
    count = (
        db.query(OrdenServicio)
        .filter(OrdenServicio.empresa_id == empresa_id)
        .count()
    )
    return f"OS-{count + 1:04d}"


# ── CRUD ─────────────────────────────────────────────────────────────────────

def list_ordenes(
    db: Session,
    empresa_id: UUID,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    tecnico_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    factura_id: Optional[UUID] = None,
    q: Optional[str] = None,
    activo: Optional[bool] = True,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[OrdenServicio], int]:
    query = db.query(OrdenServicio).filter(OrdenServicio.empresa_id == empresa_id)

    if activo is not None:
        query = query.filter(OrdenServicio.activo == activo)
    if fecha_desde:
        query = query.filter(OrdenServicio.fecha_programada >= fecha_desde)
    if fecha_hasta:
        query = query.filter(OrdenServicio.fecha_programada <= fecha_hasta)
    if estado:
        query = query.filter(OrdenServicio.estado == estado)
    if prioridad:
        query = query.filter(OrdenServicio.prioridad == prioridad)
    if tecnico_id:
        query = query.filter(OrdenServicio.tecnico_id == tecnico_id)
    if cliente_id:
        query = query.filter(OrdenServicio.cliente_id == cliente_id)
    if factura_id:
        query = query.filter(OrdenServicio.factura_id == factura_id)
    if q:
        # Buscar por folio de la orden O por nombre del cliente (comercial / fiscal)
        from app.models.cliente import Cliente
        like = f"%{q}%"
        query = query.join(Cliente, OrdenServicio.cliente_id == Cliente.id).filter(
            or_(
                OrdenServicio.folio_os.ilike(like),
                Cliente.nombre_comercial.ilike(like),
                Cliente.nombre_razon_social.ilike(like),
            )
        )

    total = query.count()
    items = (
        query.order_by(OrdenServicio.fecha_programada, OrdenServicio.hora_inicio)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_orden(db: Session, orden_id: UUID) -> OrdenServicio:
    obj = db.query(OrdenServicio).filter(OrdenServicio.id == orden_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")
    return obj


def create_orden(
    db: Session,
    empresa_id: UUID,
    data: OrdenServicioCreate,
    usuario_id: Optional[UUID] = None,
) -> OrdenServicio:
    # Verificar conflicto de técnico (mismo día, misma hora)
    if data.tecnico_id and data.hora_inicio and data.hora_fin:
        _verificar_conflicto_tecnico(
            db, data.tecnico_id, data.fecha_programada,
            data.hora_inicio, data.hora_fin, exclude_id=None
        )

    folio = _generar_folio(db, empresa_id)
    obj = OrdenServicio(
        id=uuid4(),
        empresa_id=empresa_id,
        folio_os=folio,
        **data.model_dump(),
    )
    db.add(obj)
    db.flush()  # obtener id sin commit

    # Registrar en historial
    _registrar_historial(db, obj.id, None, obj.estado, usuario_id, notas="Orden creada")

    db.commit()
    db.refresh(obj)
    return obj


def update_orden(
    db: Session,
    orden_id: UUID,
    data: OrdenServicioUpdate,
    usuario_id: Optional[UUID] = None,
) -> OrdenServicio:
    obj = get_orden(db, orden_id)
    update_data = data.model_dump(exclude_unset=True)

    estado_anterior = obj.estado

    # Verificar conflicto si cambia técnico o fechas/horas
    tecnico_id = update_data.get("tecnico_id", obj.tecnico_id)
    fecha = update_data.get("fecha_programada", obj.fecha_programada)
    hora_inicio = update_data.get("hora_inicio", obj.hora_inicio)
    hora_fin = update_data.get("hora_fin", obj.hora_fin)

    if tecnico_id and hora_inicio and hora_fin:
        _verificar_conflicto_tecnico(db, tecnico_id, fecha, hora_inicio, hora_fin, exclude_id=orden_id)

    for field, value in update_data.items():
        setattr(obj, field, value)

    # Si el estado cambió, registrar en historial
    if "estado" in update_data and update_data["estado"] != estado_anterior:
        _registrar_historial(db, obj.id, estado_anterior, obj.estado, usuario_id)

    db.commit()
    db.refresh(obj)
    return obj


def cambiar_estado(
    db: Session,
    orden_id: UUID,
    payload: CambioEstadoOS,
    usuario_id: Optional[UUID] = None,
) -> OrdenServicio:
    obj = get_orden(db, orden_id)
    estado_anterior = obj.estado

    if estado_anterior == payload.estado:
        return obj  # sin cambio

    obj.estado = payload.estado
    _registrar_historial(db, obj.id, estado_anterior, payload.estado, usuario_id, notas=payload.notas)

    db.commit()
    db.refresh(obj)
    return obj


def delete_orden(db: Session, orden_id: UUID) -> None:
    """Soft delete."""
    obj = get_orden(db, orden_id)
    obj.activo = False
    db.commit()


# ── Helpers internos ──────────────────────────────────────────────────────────

def _registrar_historial(
    db: Session,
    orden_id: UUID,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    usuario_id: Optional[UUID],
    notas: Optional[str] = None,
) -> None:
    entrada = HistorialEstadoOS(
        id=uuid4(),
        orden_id=orden_id,
        usuario_id=usuario_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        notas=notas,
    )
    db.add(entrada)


def _verificar_conflicto_tecnico(
    db: Session,
    tecnico_id: UUID,
    fecha: date,
    hora_inicio,
    hora_fin,
    exclude_id: Optional[UUID],
) -> None:
    """
    Detecta si el técnico ya tiene una OS en el mismo día que se solape con el
    rango hora_inicio–hora_fin propuesto.
    Lanza HTTPException 409 si hay conflicto.
    """
    query = db.query(OrdenServicio).filter(
        OrdenServicio.tecnico_id == tecnico_id,
        OrdenServicio.fecha_programada == fecha,
        OrdenServicio.activo == True,
        OrdenServicio.estado.notin_(["CANCELADO", "COMPLETADO"]),
        OrdenServicio.hora_inicio.isnot(None),
        OrdenServicio.hora_fin.isnot(None),
        # Solapamiento: A.inicio < B.fin AND A.fin > B.inicio
        OrdenServicio.hora_inicio < hora_fin,
        OrdenServicio.hora_fin > hora_inicio,
    )
    if exclude_id:
        query = query.filter(OrdenServicio.id != exclude_id)

    conflicto = query.first()
    if conflicto:
        raise HTTPException(
            status_code=409,
            detail=f"El técnico ya tiene la orden {conflicto.folio_os} programada en ese horario.",
        )


# ── Vínculo con factura ───────────────────────────────────────────────────────

def crear_factura_desde_orden(db: Session, orden_id: UUID):
    """Crea una factura BORRADOR ligada a la orden. Si el servicio de la orden
    tiene un Producto/Servicio fiscal vinculado, prellena el concepto con sus
    claves SAT y el precio acordado de la orden. Devuelve la factura."""
    from decimal import Decimal, ROUND_HALF_UP
    from app.models.factura import Factura
    from app.models.factura_detalle import FacturaDetalle
    from app.services import factura_service

    orden = get_orden(db, orden_id)
    if orden.factura_id:
        raise HTTPException(status_code=409, detail="La orden ya tiene una factura vinculada")

    # Candado: la orden debe tener servicio y éste un producto/concepto fiscal vinculado
    if not orden.servicio_id or not orden.servicio:
        raise HTTPException(
            status_code=422,
            detail="Esta orden no tiene tipo de servicio asignado. Edita la orden y asígnalo antes de facturar.",
        )
    if not orden.servicio.producto_servicio_id:
        raise HTTPException(
            status_code=422,
            detail=(
                f"El servicio '{orden.servicio.nombre}' no tiene un producto/servicio fiscal vinculado. "
                "Vincúlalo en el catálogo de Servicios para poder facturar."
            ),
        )

    serie = "A"
    factura = Factura(
        empresa_id=orden.empresa_id,
        cliente_id=orden.cliente_id,
        serie=serie,
        folio=factura_service.siguiente_folio(db, orden.empresa_id, serie),
        estatus="BORRADOR",
        status_pago="NO_PAGADA",
        observaciones=f"Generada desde la orden {orden.folio_os}",
    )

    # Prellenar concepto desde el Producto/Servicio fiscal vinculado al servicio operativo
    prod = orden.servicio.producto_servicio if (orden.servicio and orden.servicio.producto_servicio_id) else None
    if prod:
        cantidad = Decimal("1")
        # Precio: el acordado en la orden; si no hay, el del catálogo fiscal
        valor = Decimal(str(orden.precio_acordado if orden.precio_acordado is not None else (prod.valor_unitario or 0)))
        iva_tasa = Decimal("0.16")  # tasa por defecto; se ajusta en el form si aplica (p.ej. 0.08)
        base = (cantidad * valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        iva_importe = (base * iva_tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        importe = base + iva_importe

        factura.conceptos.append(
            FacturaDetalle(
                producto_servicio_id=prod.id,
                clave_producto=prod.clave_producto,
                clave_unidad=prod.clave_unidad,
                unidad=getattr(prod, "unidad_inventario", None),
                descripcion=prod.descripcion or (orden.servicio.nombre if orden.servicio else ""),
                cantidad=cantidad,
                valor_unitario=valor,
                descuento=Decimal("0"),
                importe=importe,
                objeto_imp="02",
                iva_tipo_factor="Tasa",
                iva_tasa=iva_tasa,
                iva_importe=iva_importe,
            )
        )
        factura.subtotal = base
        factura.impuestos_trasladados = iva_importe
        factura.impuestos_retenidos = Decimal("0")
        factura.total = base + iva_importe

    db.add(factura)
    db.flush()  # obtener factura.id

    orden.factura_id = factura.id
    db.commit()
    db.refresh(factura)
    db.refresh(orden)
    return factura


# RFC genéricos (público en general nacional / extranjero): no se agrupan por RFC
RFC_GENERICOS = {"XAXX010101000", "XEXX010101000"}


def _rfc_normalizado(cliente) -> Optional[str]:
    rfc = (getattr(cliente, "rfc", None) or "").strip().upper()
    return rfc or None


def facturas_vinculables(db: Session, orden_id: UUID) -> list:
    """Facturas candidatas para vincular: misma empresa y mismo cliente, o
    cualquier cliente con el MISMO RFC (sucursales). Para RFC genérico
    (público en general) solo el cliente exacto."""
    from app.models.factura import Factura
    from app.models.cliente import Cliente

    orden = get_orden(db, orden_id)
    rfc = _rfc_normalizado(orden.cliente)

    q = db.query(Factura).filter(Factura.empresa_id == orden.empresa_id)
    if rfc and rfc not in RFC_GENERICOS:
        q = q.join(Cliente, Factura.cliente_id == Cliente.id).filter(
            func.upper(Cliente.rfc) == rfc
        )
    else:
        q = q.filter(Factura.cliente_id == orden.cliente_id)

    rows = q.order_by(Factura.serie, Factura.folio.desc()).limit(100).all()
    return [
        {
            "id": str(f.id),
            "serie": f.serie,
            "folio": f.folio,
            "estatus": f.estatus,
            "status_pago": f.status_pago,
            "total": float(f.total or 0),
            "cliente_nombre": f.cliente.nombre_comercial if f.cliente else None,
        }
        for f in rows
    ]


def vincular_factura(db: Session, orden_id: UUID, factura_id: UUID) -> OrdenServicio:
    """Liga una factura existente a la orden. Permite mismo cliente o cualquier
    cliente con el mismo RFC (sucursales); RFC genérico exige cliente exacto."""
    from app.models.factura import Factura

    orden = get_orden(db, orden_id)
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.empresa_id != orden.empresa_id:
        raise HTTPException(status_code=422, detail="La factura debe ser de la misma empresa que la orden")

    rfc_orden = _rfc_normalizado(orden.cliente)
    rfc_factura = _rfc_normalizado(factura.cliente)
    mismo_cliente = factura.cliente_id == orden.cliente_id
    mismo_rfc = bool(rfc_orden and rfc_orden not in RFC_GENERICOS and rfc_orden == rfc_factura)
    if not (mismo_cliente or mismo_rfc):
        raise HTTPException(
            status_code=422,
            detail="La factura debe ser del mismo cliente o de un cliente con el mismo RFC.",
        )
    orden.factura_id = factura_id
    db.commit()
    db.refresh(orden)
    return orden


def desvincular_factura(db: Session, orden_id: UUID) -> OrdenServicio:
    orden = get_orden(db, orden_id)
    orden.factura_id = None
    db.commit()
    db.refresh(orden)
    return orden
