# app/services/factura_service.py
from __future__ import annotations
import uuid
import logging
from decimal import Decimal
from uuid import UUID
from typing import List, Optional, Tuple, Literal
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, asc, desc
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import date, datetime

from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import FacturaCreate, FacturaUpdate
from app.models.associations import cliente_empresa as cliente_empresa_association
from app.services.timbrado_factmoderna import FacturacionModernaPAC
from app.services.cfdi40_xml import build_cfdi40_xml_sin_timbrar
from app.services.pdf_factura import render_factura_pdf_bytes_from_model, load_factura_full

logger = logging.getLogger("app")
_pac = FacturacionModernaPAC()

# ────────────────────────────────────────────────────────────────
# FOLIO

def siguiente_folio(db: Session, empresa_id: UUID, serie: str) -> int:
    latest_invoice = (
        db.query(Factura)
        .filter(Factura.empresa_id == empresa_id, Factura.serie == serie)
        .order_by(Factura.folio.desc())
        .with_for_update()
        .first()
    )
    return latest_invoice.folio + 1 if latest_invoice else 1

# ────────────────────────────────────────────────────────────────
# CRUD

def crear_factura(db: Session, payload: FacturaCreate) -> Factura:
    association_exists = db.query(cliente_empresa_association).filter_by(
        cliente_id=payload.cliente_id,
        empresa_id=payload.empresa_id
    ).first()
    if not association_exists:
        raise HTTPException(
            status_code=422,
            detail=f"El cliente ID {payload.cliente_id} no está asociado a la empresa ID {payload.empresa_id}."
        )

    serie = (payload.serie or "A").upper()
    folio = payload.folio if payload.folio is not None else siguiente_folio(db, payload.empresa_id, serie)

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

        factura.conceptos.append(FacturaDetalle(**c.dict(), importe=importe_concepto, iva_importe=iva_importe, ret_iva_importe=ret_iva_importe, ret_isr_importe=ret_isr_importe))

    factura.subtotal = subtotal_general
    factura.impuestos_trasladados = traslados_general
    factura.impuestos_retenidos = retenciones_general
    factura.total = subtotal_general + traslados_general - retenciones_general

    db.add(factura)
    try:
        db.commit()
        db.refresh(factura)
        return factura
    except IntegrityError as e:
        db.rollback()
        if 'uq_fact_serie_folio_por_empresa' in str(e.orig):
            raise HTTPException(status_code=409, detail=f"El folio {factura.folio} para la serie '{factura.serie}' ya existe.")
        raise HTTPException(status_code=500, detail=f"Error de integridad en la base de datos: {e.orig}")

def actualizar_factura(db: Session, factura_id: UUID, payload: FacturaUpdate) -> Factura:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    update_data = payload.dict(exclude_unset=True)

    if factura.estatus in ["TIMBRADA", "CANCELADA"]:
        campos_permitidos = {"status_pago", "fecha_pago", "fecha_cobro", "observaciones"}
        campos_solicitados = set(update_data.keys())
        if 'conceptos' in campos_solicitados:
            raise HTTPException(status_code=400, detail=f"No se pueden modificar los conceptos de una factura en estado {factura.estatus}")
        campos_no_permitidos = campos_solicitados - campos_permitidos
        if campos_no_permitidos:
            raise HTTPException(status_code=400, detail=f"La factura está {factura.estatus}. Solo se pueden modificar campos de pago/observaciones.")
        
        for key, value in update_data.items():
            setattr(factura, key, value)
    else:
        if 'cliente_id' in update_data and payload.cliente_id and payload.cliente_id != factura.cliente_id:
            association_exists = db.query(cliente_empresa_association).filter_by(cliente_id=payload.cliente_id, empresa_id=factura.empresa_id).first()
            if not association_exists:
                raise HTTPException(status_code=422, detail=f"El nuevo cliente ID {payload.cliente_id} no está asociado a la empresa.")
        
        for key, value in update_data.items():
            if key != 'conceptos':
                setattr(factura, key, value)

        if payload.conceptos is not None:
            db.query(FacturaDetalle).where(FacturaDetalle.factura_id == factura.id).delete()
            # Recalculate totals
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

                factura.conceptos.append(FacturaDetalle(**c.dict(), factura_id=factura.id, importe=importe_concepto, iva_importe=iva_importe, ret_iva_importe=ret_iva_importe, ret_isr_importe=ret_isr_importe))
            
            factura.subtotal = subtotal_general
            factura.impuestos_trasladados = traslados_general
            factura.impuestos_retenidos = retenciones_general
            factura.total = subtotal_general + traslados_general - retenciones_general

    db.commit()
    db.refresh(factura)
    return factura

# ────────────────────────────────────────────────────────────────
# Acciones CFDI

def timbrar_factura(db: Session, factura_id: UUID) -> dict:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se puede timbrar una factura en BORRADOR")

    try:
        result = _pac.timbrar_factura(
            db=db,
            factura_id=factura_id,
            generar_pdf=False,
            generar_cbb=False,
            generar_txt=False,
        )
        if not result.get("timbrada"):
            detalle = result.get("detalle") or "No se pudo timbrar"
            raise HTTPException(status_code=409, detail=detalle)
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error de servicio al timbrar factura %s", factura_id)
        raise HTTPException(status_code=500, detail=f"Error interno al timbrar la factura: {e}")

def solicitar_cancelacion_cfdi(db: Session, factura_id: UUID, motivo: str, folio_sustitucion: Optional[str] = None) -> dict:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "TIMBRADA":
        raise HTTPException(status_code=400, detail="Solo se puede cancelar una factura que está TIMBRADA")
    if not factura.cfdi_uuid:
        raise HTTPException(status_code=400, detail="La factura no tiene un UUID fiscal para cancelar.")

    try:
        out = _pac.solicitar_cancelacion_cfdi(
            db=db,
            factura_id=factura_id,
            motivo=motivo,
            folio_sustitucion=folio_sustitucion,
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Error de servicio al cancelar factura %s", factura_id)
        raise HTTPException(status_code=500, detail=f"Error inesperado al solicitar cancelación: {e}")

# ────────────────────────────────────────────────────────────────
# Generación de Archivos

def generar_xml_preview_bytes(db: Session, factura_id: UUID) -> bytes:
    try:
        return build_cfdi40_xml_sin_timbrar(db, factura_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e) or "Factura no encontrada")
    except Exception as e:
        logger.exception("Error de servicio al generar XML preview para %s", factura_id)
        raise HTTPException(status_code=500, detail=f"Error interno al generar XML: {e}")

def generar_pdf_bytes(db: Session, factura_id: UUID, preview: bool) -> bytes:
    factura = load_factura_full(db, factura_id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada para generar PDF")
    if not preview and factura.estatus == "BORRADOR":
        raise HTTPException(status_code=409, detail="Debe estar TIMBRADA o CANCELADA para PDF final")
    try:
        return render_factura_pdf_bytes_from_model(db, factura_id, preview=preview, logo_path=None)
    except Exception as e:
        logger.exception("Error de servicio al generar PDF para %s", factura_id)
        raise HTTPException(status_code=500, detail=f"Error interno al generar PDF: {e}")

def obtener_ruta_xml_timbrado(db: Session, factura_id: UUID) -> Tuple[str, str, str]:
    factura = db.query(Factura).options(selectinload(Factura.empresa)).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "TIMBRADA":
        raise HTTPException(status_code=409, detail="La factura debe estar TIMBRADA para descargar el XML")
    if not factura.xml_path:
        raise HTTPException(status_code=404, detail="No hay ruta de XML registrada para esta factura")
    
    emisor_rfc = (getattr(factura.empresa, "rfc", "") or "EMISOR").upper()
    filename = f"{emisor_rfc}-{factura.serie}-{factura.folio}.xml" if factura.serie and factura.folio else f"{emisor_rfc}-{factura.id}.xml"

    return factura.xml_path, filename

# ────────────────────────────────────────────────────────────────
# Otras Acciones

def marcar_pago_factura(db: Session, factura_id: UUID, status: Literal["PAGADA", "NO_PAGADA"], fecha_pago: Optional[date] = None, fecha_cobro: Optional[date] = None) -> Factura:
    factura = db.query(Factura).options(selectinload(Factura.conceptos)).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if status == "PAGADA" and not fecha_cobro:
        raise HTTPException(status_code=422, detail="Para marcar PAGADA, envía fecha_cobro")

    if fecha_pago is not None:
        factura.fecha_pago = datetime.combine(fecha_pago, datetime.min.time())
    
    if fecha_cobro is not None:
        factura.fecha_cobro = datetime.combine(fecha_cobro, datetime.min.time())
    elif status == "NO_PAGADA":
        factura.fecha_cobro = None

    factura.status_pago = status
    db.commit()
    db.refresh(factura)
    return factura

# ────────────────────────────────────────────────────────────────
# Consultas

def obtener_por_serie_folio(db: Session, empresa_id: UUID, serie: str, folio: int) -> Optional[Factura]:
    return (
        db.query(Factura)
        .options(selectinload(Factura.conceptos))
        .filter(Factura.empresa_id == empresa_id, Factura.serie == serie.upper(), Factura.folio == folio)
        .first()
    )

def listar_facturas(db: Session, *, empresa_id: Optional[UUID] = None, cliente_id: Optional[UUID] = None, serie: Optional[str] = None, folio_min: Optional[int] = None, folio_max: Optional[int] = None, estatus: Optional[str] = None, status_pago: Optional[str] = None, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None, order_by: str = "serie_folio", order_dir: str = "asc", limit: int = 50, offset: int = 0) -> Tuple[List[Factura], int]:
    q = db.query(Factura).options(selectinload(Factura.conceptos), selectinload(Factura.cliente))

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
        q = q.filter(Factura.creado_en <= fecha_hasta)

    total = q.with_entities(func.count(Factura.id)).scalar() or 0

    dir_fn = asc if order_dir.lower() == "asc" else desc
    if order_by == "fecha":
        q = q.order_by(dir_fn(Factura.creado_en))
    elif order_by == "total":
        q = q.order_by(dir_fn(Factura.total))
    else:
        q = q.order_by(dir_fn(Factura.serie), dir_fn(Factura.folio))

    items = q.offset(offset).limit(limit).all()
    return items, total
