# app/services/facturas.py
from __future__ import annotations
import uuid
from decimal import Decimal
from uuid import UUID
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from datetime import date
from sqlalchemy import func, asc, desc
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import FacturaCreate, FacturaUpdate

# ────────────────────────────────────────────────────────────────
# FOLIO: consecutivo por empresa+serie (con bloqueo)

def siguiente_folio(db: Session, empresa_id: UUID, serie: str) -> int:
    # Bloquea la última factura de la serie para evitar race conditions
    latest_invoice = (
        db.query(Factura)
        .filter(Factura.empresa_id == empresa_id, Factura.serie == serie)
        .order_by(Factura.folio.desc())
        .with_for_update()
        .first()
    )

    if latest_invoice:
        return latest_invoice.folio + 1
    else:
        return 1

# ────────────────────────────────────────────────────────────────
# Crear factura (usa folio auto si no viene)

def crear_factura(db: Session, payload: FacturaCreate) -> Factura:
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
        tipo_comprobante=payload.tipo_comprobante,
        forma_pago=payload.forma_pago,
        metodo_pago=payload.metodo_pago,
        uso_cfdi=payload.uso_cfdi,
        fecha_emision=payload.fecha_emision,
        lugar_expedicion=payload.lugar_expedicion,
        condiciones_pago=payload.condiciones_pago,
        rfc_proveedor_sat=payload.rfc_proveedor_sat,
    )

    # Recalcular totales
    subtotal_general = Decimal("0")
    traslados_general = Decimal("0")
    retenciones_general = Decimal("0")

    for c in payload.conceptos:
        base_calculo = (c.cantidad or Decimal("0")) * c.valor_unitario - (c.descuento or Decimal("0"))
        
        iva_importe = base_calculo * (c.iva_tasa or Decimal("0"))
        ret_iva_importe = base_calculo * (c.ret_iva_tasa or Decimal("0"))
        ret_isr_importe = base_calculo * (c.ret_isr_tasa or Decimal("0"))
        
        importe_concepto = base_calculo + iva_importe - ret_iva_importe - ret_isr_importe

        subtotal_general += base_calculo
        traslados_general += iva_importe
        retenciones_general += ret_iva_importe + ret_isr_importe

        factura.conceptos.append(
            FacturaDetalle(
                tipo=c.tipo,
                clave_producto=c.clave_producto,
                clave_unidad=c.clave_unidad,
                descripcion=c.descripcion,
                cantidad=c.cantidad,
                valor_unitario=c.valor_unitario,
                descuento=c.descuento,
                importe=importe_concepto,
                iva_tasa=c.iva_tasa,
                iva_importe=iva_importe,
                ret_iva_tasa=c.ret_iva_tasa,
                ret_iva_importe=ret_iva_importe,
                ret_isr_tasa=c.ret_isr_tasa,
                ret_isr_importe=ret_isr_importe,
                requiere_lote=c.requiere_lote or False,
                lote=c.lote,
            )
        )

    factura.subtotal = subtotal_general
    factura.impuestos_trasladados = traslados_general
    factura.impuestos_retenidos = retenciones_general
    factura.total = subtotal_general + traslados_general - retenciones_general

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

    db.commit()
    db.refresh(factura)
    return factura

# ────────────────────────────────────────────────────────────────

def actualizar_factura(db: Session, factura_id: UUID, payload: FacturaUpdate) -> Optional[Factura]:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        return None

    update_data = payload.dict(exclude_unset=True)

    if factura.estatus in ["TIMBRADA", "CANCELADA"]:
        # Modo restringido: solo se permiten ciertos campos
        campos_permitidos = {"status_pago", "fecha_pago", "observaciones"}
        
        campos_solicitados = set(update_data.keys())
        
        # El único campo complejo permitido es 'conceptos', que aquí está prohibido.
        if 'conceptos' in campos_solicitados:
            raise HTTPException(
                status_code=400,
                detail=f"No se pueden modificar los conceptos de una factura en estado {factura.estatus}"
            )

        campos_no_permitidos = campos_solicitados - campos_permitidos
        if campos_no_permitidos:
            raise HTTPException(
                status_code=400,
                detail=f"La factura está {factura.estatus}. Solo se puede modificar 'status_pago', 'fecha_pago' y 'observaciones'. Campos no permitidos: {list(campos_no_permitidos)}"
            )
        
        # Aplicar los cambios permitidos
        for key, value in update_data.items():
            setattr(factura, key, value)

    else:  # Estado es BORRADOR, se permite todo
        # Actualizar campos escalares
        for key, value in update_data.items():
            if key != 'conceptos':
                setattr(factura, key, value)

        # Reemplazo total de conceptos si vienen en el payload
        if payload.conceptos is not None:
            # Borra existentes
            db.query(FacturaDetalle).where(FacturaDetalle.factura_id == factura.id).delete()
            
            # Recalcular totales desde cero
            subtotal_general = Decimal("0")
            traslados_general = Decimal("0")
            retenciones_general = Decimal("0")

            for c in payload.conceptos:
                base_calculo = (c.cantidad or Decimal("0")) * c.valor_unitario - (c.descuento or Decimal("0"))
                iva_importe = base_calculo * (c.iva_tasa or Decimal("0"))
                ret_iva_importe = base_calculo * (c.ret_iva_tasa or Decimal("0"))
                ret_isr_importe = base_calculo * (c.ret_isr_tasa or Decimal("0"))
                importe_concepto = base_calculo + iva_importe - ret_iva_importe - ret_isr_importe

                subtotal_general += base_calculo
                traslados_general += iva_importe
                retenciones_general += ret_iva_importe + ret_isr_importe

                db.add(
                    FacturaDetalle(
                        factura_id=factura.id,
                        tipo=c.tipo,
                        clave_producto=c.clave_producto,
                        clave_unidad=c.clave_unidad,
                        descripcion=c.descripcion,
                        cantidad=c.cantidad,
                        valor_unitario=c.valor_unitario,
                        descuento=c.descuento,
                        importe=importe_concepto,
                        iva_tasa=c.iva_tasa,
                        iva_importe=iva_importe,
                        ret_iva_tasa=c.ret_iva_tasa,
                        ret_iva_importe=ret_iva_importe,
                        ret_isr_tasa=c.ret_isr_tasa,
                        ret_isr_importe=ret_isr_importe,
                        requiere_lote=c.requiere_lote or False,
                        lote=c.lote,
                    )
                )
            
            factura.subtotal = subtotal_general
            factura.impuestos_trasladados = traslados_general
            factura.impuestos_retenidos = retenciones_general
            factura.total = subtotal_general + traslados_general - retenciones_general

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
    fac.cfdi_uuid = str(uuid.uuid4())
    fac.fecha_timbrado = date.today()
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
        .options(
            selectinload(Factura.conceptos),
            selectinload(Factura.cliente)
        )
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
