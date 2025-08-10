# app/api/factura.py
from __future__ import annotations

import logging
from uuid import UUID
from typing import List, Optional, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import (
    FacturaCreate,
    FacturaUpdate,
    FacturaOut,
)
from app.services.facturas import (
    crear_factura,
    actualizar_factura,
    obtener_por_serie_folio,
    timbrar_factura,
    cancelar_factura,
    listar_facturas as listar_facturas_srv,  # <- servicio de listado (alias)
)

logger = logging.getLogger("app")

router = APIRouter()

# ────────────────────────────────────────────────────────────────
# Helpers

def _with_conceptos(q):
    """Asegura cargar conceptos para serializar FacturaOut."""
    return q.options(selectinload(Factura.conceptos))

# ────────────────────────────────────────────────────────────────
# Modelos de respuesta

class FacturasPageOut(BaseModel):
    items: List[FacturaOut]
    total: int
    limit: int
    offset: int

# ────────────────────────────────────────────────────────────────
# Endpoints
@router.get(
    "/schema",
    summary="Obtener el schema del modelo"
)
def get_form_schema_factura():
    """
    Devuelve el schema del modelo factura (basado en FacturaCreate),
    agregando x-options para selects y enums necesarias.
    """
    schema = FacturaCreate.schema()
    props = schema["properties"]
    required = schema.get("required", [])

    # Moneda
    if "moneda" in props:
        props["moneda"]["x-options"] = [
            {"value": "MXN", "label": "MXN - Peso mexicano"},
            {"value": "USD", "label": "USD - Dólar estadounidense"},
        ]
        props["moneda"]["enum"] = ["MXN", "USD"]

    # Método de pago
    if "metodo_pago" in props:
        props["metodo_pago"]["x-options"] = [
            {"value": "PUE", "label": "PUE - Pago en una sola exhibición"},
            {"value": "PPD", "label": "PPD - Pago en parcialidades o diferido"},
        ]
        props["metodo_pago"]["enum"] = ["PUE", "PPD"]

    # Forma de pago (catálogo mínimo)
    if "forma_pago" in props:
        formas = [
            ("01", "Efectivo"),
            ("03", "Transferencia electrónica"),
            ("04", "Tarjeta de crédito"),
            ("28", "Tarjeta de débito"),
        ]
        props["forma_pago"]["x-options"] = [
            {"value": c, "label": f"{c} – {d}"} for c, d in formas
        ]
        props["forma_pago"]["enum"] = [c for c, _ in formas]

    # Uso CFDI (catálogo mínimo de ejemplo)
    if "uso_cfdi" in props:
        usos = [
            ("G01", "Adquisición de mercancías"),
            ("G03", "Gastos en general"),
            ("P01", "Por definir"),
        ]
        props["uso_cfdi"]["x-options"] = [
            {"value": c, "label": f"{c} – {d}"} for c, d in usos
        ]
        props["uso_cfdi"]["enum"] = [c for c, _ in usos]

    # Conceptos.tipo (anidado)
    conceptos_props = props.get("conceptos", {}).get("items", {}).get("properties", {})
    if "tipo" in conceptos_props:
        conceptos_props["tipo"]["x-options"] = [
            {"value": "PRODUCTO", "label": "Producto"},
            {"value": "SERVICIO", "label": "Servicio"},
        ]
        conceptos_props["tipo"]["enum"] = ["PRODUCTO", "SERVICIO"]

    return {"properties": props, "required": required}
@router.post(
    "/",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    summary="Crear factura",
    description="Crea una factura en estatus BORRADOR calculando importes por concepto y totales."
)
def crear_factura_endpoint(payload: FacturaCreate, db: Session = Depends(get_db)) -> FacturaOut:
    try:
        factura = crear_factura(db, payload)
        # volver a cargar con conceptos para el response
        factura = _with_conceptos(db.query(Factura)).filter(Factura.id == factura.id).first()
        return factura
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al crear factura")
        raise HTTPException(status_code=500, detail="Error al crear la factura") from e


@router.put(
    "/{id}",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    summary="Actualizar factura",
    description="Actualiza campos de la factura. Si se envían conceptos, se reemplazan y se recalculan totales."
)
def actualizar_factura_endpoint(
    id: UUID = Path(..., description="ID de la factura"),
    payload: FacturaUpdate = ...,
    db: Session = Depends(get_db),
) -> FacturaOut:
    try:
        factura = actualizar_factura(db, id, payload)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        # cargar con conceptos
        factura = _with_conceptos(db.query(Factura)).filter(Factura.id == id).first()
        return factura
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al actualizar factura %s", id)
        raise HTTPException(status_code=500, detail="Error al actualizar la factura") from e


@router.get(
    "/{id}",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    summary="Obtener factura por ID",
    description="Devuelve la factura con sus conceptos."
)
def obtener_factura(
    id: UUID = Path(..., description="ID de la factura"),
    db: Session = Depends(get_db),
) -> FacturaOut:
    factura = _with_conceptos(db.query(Factura)).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura


@router.get(
    "/",
    response_model=FacturasPageOut,
    response_model_exclude_none=True,
    summary="Listar facturas (con filtros, orden y paginación)",
    description="Permite filtrar por empresa, cliente, serie/folio, estatus, rango de fechas y ordenar por serie+folio, fecha o total."
)
def listar_facturas_endpoint(
    db: Session = Depends(get_db),
    # filtros
    empresa_id: Optional[UUID] = Query(None, description="Filtrar por empresa"),
    cliente_id: Optional[UUID] = Query(None, description="Filtrar por cliente"),
    serie: Optional[str] = Query(None, max_length=10, description="Serie exacta"),
    folio_min: Optional[int] = Query(None, ge=1, description="Mínimo folio"),
    folio_max: Optional[int] = Query(None, ge=1, description="Máximo folio"),
    estatus: Optional[Literal["BORRADOR", "TIMBRADA", "CANCELADA"]] = Query(None, description="Estatus CFDI"),
    status_pago: Optional[Literal["PAGADA", "NO_PAGADA"]] = Query(None, description="Estatus de pago"),
    fecha_desde: Optional[date] = Query(None, description="Fecha inicial (creado_en)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha final (creado_en)"),
    # orden
    order_by: Literal["serie_folio", "fecha", "total"] = Query("serie_folio"),
    order_dir: Literal["asc", "desc"] = Query("asc"),
    # paginación
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FacturasPageOut:
    items, total = listar_facturas_srv(
        db,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        serie=serie,
        folio_min=folio_min,
        folio_max=folio_max,
        estatus=estatus,
        status_pago=status_pago,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar factura (borrador)",
    description="Elimina una factura en estatus BORRADOR. Si está TIMBRADA/CANCELADA, responde 409."
)
def eliminar_factura(
    id: UUID = Path(..., description="ID de la factura"),
    db: Session = Depends(get_db),
):
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "BORRADOR":
        raise HTTPException(status_code=409, detail="Solo se pueden eliminar facturas en BORRADOR")

    # Borra conceptos primero por FK, luego factura
    db.query(FacturaDetalle).where(FacturaDetalle.factura_id == factura.id).delete()
    db.delete(factura)
    db.commit()
    return


@router.patch(
    "/{id}/pago",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    summary="Marcar pago/cobro",
    description="Actualiza `fecha_pago`, `fecha_cobro` y `status_pago`."
)
def marcar_pago(
    id: UUID,
    status: Literal["PAGADA", "NO_PAGADA"] = Query(..., description="Nuevo status de pago"),
    fecha_pago: Optional[date] = Query(None, description="Fecha programada de pago"),
    fecha_cobro: Optional[date] = Query(None, description="Fecha real de cobro"),
    db: Session = Depends(get_db),
) -> FacturaOut:
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Reglas simples
    if status == "PAGADA" and not fecha_cobro:
        raise HTTPException(status_code=422, detail="Para marcar PAGADA, envía fecha_cobro")

    if fecha_pago is not None:
        from datetime import datetime
        factura.fecha_pago = datetime.combine(fecha_pago, datetime.min.time())
    if fecha_cobro is not None:
        from datetime import datetime
        factura.fecha_cobro = datetime.combine(fecha_cobro, datetime.min.time())

    factura.status_pago = status
    db.commit()
    db.refresh(factura)

    # devolver con conceptos
    factura = _with_conceptos(db.query(Factura)).filter(Factura.id == id).first()
    return factura


@router.get(
    "/por-folio",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    summary="Obtener por empresa+serie+folio"
)
def obtener_por_folio_endpoint(
    empresa_id: UUID = Query(..., description="Empresa de la factura"),
    serie: str = Query(..., min_length=1, max_length=10),
    folio: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    fac = obtener_por_serie_folio(db, empresa_id, serie, folio)
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return fac


@router.post(
    "/{id}/timbrar",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    summary="Timbrar (simulado)"
)
def timbrar_endpoint(
    id: UUID,
    db: Session = Depends(get_db),
):
    try:
        fac = timbrar_factura(db, id)
        if not fac:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        # recargar con conceptos
        fac = _with_conceptos(db.query(Factura)).filter(Factura.id == id).first()
        return fac
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve)) from ve
    except Exception as e:
        logger.exception("Error al timbrar %s", id)
        raise HTTPException(status_code=500, detail="Error al timbrar la factura") from e


@router.post(
    "/{id}/cancelar",
    response_model=FacturaOut,
    response_model_exclude_none=True,
    summary="Cancelar (simulado)"
)
def cancelar_endpoint(
    id: UUID,
    db: Session = Depends(get_db),
):
    try:
        fac = cancelar_factura(db, id)
        if not fac:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        fac = _with_conceptos(db.query(Factura)).filter(Factura.id == id).first()
        return fac
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve)) from ve
    except Exception as e:
        logger.exception("Error al cancelar %s", id)
        raise HTTPException(status_code=500, detail="Error al cancelar la factura") from e