# app/api/factura.py
from __future__ import annotations
import logging
import os
from uuid import UUID
from typing import List, Optional, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import FacturaCreate, FacturaUpdate, FacturaOut

# Catálogos (se mantienen aquí por ser data de solo lectura para el schema del UI)
from app.catalogos_sat.facturacion import (
    obtener_todas_formas_pago,
    obtener_todos_metodos_pago,
    obtener_todos_usos_cfdi,
)

# Importaciones del nuevo servicio refactorizado
from app.services import factura_service as srv

logger = logging.getLogger("app")
router = APIRouter()

# ────────────────────────────────────────────────────────────────
# Modelos de Respuesta/Entrada específicos de la API

class FacturasPageOut(BaseModel):
    items: List[FacturaOut]
    total: int
    limit: int
    offset: int

class CancelarIn(BaseModel):
    motivo_cancelacion: str = "02"
    folio_fiscal_sustituto: str | None = None

    @field_validator("motivo_cancelacion")
    @classmethod
    def check_motivo(cls, v: str):
        v = (v or "").strip()
        if v not in {"01", "02", "03", "04"}:
            raise ValueError("Motivo inválido. Valores permitidos: 01, 02, 03, 04.")
        return v

# ────────────────────────────────────────────────────────────────
# Endpoints

@router.get("/schema", summary="Obtener el schema del modelo para UI")
def get_form_schema_factura():
    schema = FacturaCreate.schema()
    # ... (la lógica para enriquecer el schema se mantiene, es específica de la UI)
    return schema

@router.post("/", response_model=FacturaOut, status_code=status.HTTP_201_CREATED)
def crear_factura_endpoint(payload: FacturaCreate, db: Session = Depends(get_db)) -> Factura:
    return srv.crear_factura(db, payload)

@router.put("/{id}", response_model=FacturaOut)
def actualizar_factura_endpoint(id: UUID, payload: FacturaUpdate, db: Session = Depends(get_db)) -> Factura:
    return srv.actualizar_factura(db, id, payload)

@router.get("/{id}", response_model=FacturaOut)
def obtener_factura(id: UUID, db: Session = Depends(get_db)) -> Factura:
    factura = db.query(Factura).options(selectinload(Factura.conceptos)).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura

@router.get("/", response_model=FacturasPageOut)
def listar_facturas_endpoint(db: Session = Depends(get_db), empresa_id: Optional[UUID] = Query(None), cliente_id: Optional[UUID] = Query(None), serie: Optional[str] = Query(None), folio_min: Optional[int] = Query(None), folio_max: Optional[int] = Query(None), estatus: Optional[Literal["BORRADOR", "TIMBRADA", "CANCELADA"]] = Query(None), status_pago: Optional[Literal["PAGADA", "NO_PAGADA"]] = Query(None), fecha_desde: Optional[date] = Query(None), fecha_hasta: Optional[date] = Query(None), order_by: Literal["serie_folio", "fecha", "total"] = Query("serie_folio"), order_dir: Literal["asc", "desc"] = Query("asc"), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    items, total = srv.listar_facturas(db, empresa_id=empresa_id, cliente_id=cliente_id, serie=serie, folio_min=folio_min, folio_max=folio_max, estatus=estatus, status_pago=status_pago, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, order_by=order_by, order_dir=order_dir, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_factura(id: UUID, db: Session = Depends(get_db)):
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "BORRADOR":
        raise HTTPException(status_code=409, detail="Solo se pueden eliminar facturas en BORRADOR")
    db.delete(factura)
    db.commit()
    return

@router.patch("/{id}/pago", response_model=FacturaOut)
def marcar_pago(id: UUID, status: Literal["PAGADA", "NO_PAGADA"], fecha_pago: Optional[date] = Query(None), fecha_cobro: Optional[date] = Query(None), db: Session = Depends(get_db)) -> Factura:
    return srv.marcar_pago_factura(db, id, status, fecha_pago, fecha_cobro)

@router.get("/por-folio", response_model=FacturaOut)
def obtener_por_folio_endpoint(empresa_id: UUID, serie: str, folio: int, db: Session = Depends(get_db)) -> Factura:
    factura = srv.obtener_por_serie_folio(db, empresa_id, serie, folio)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura

# --- Endpoints de Acciones CFDI ---

@router.post("/{id}/timbrar", summary="Timbrar factura con PAC")
def timbrar_endpoint(id: UUID, db: Session = Depends(get_db)):
    return srv.timbrar_factura(db, id)

@router.post("/{id}/cancelar")
def solicitar_cancelacion_endpoint(id: UUID, payload: CancelarIn, db: Session = Depends(get_db)):
    return srv.solicitar_cancelacion_cfdi(db, id, payload.motivo_cancelacion, payload.folio_fiscal_sustituto)

# --- Endpoints de Archivos ---

@router.post("/{id}/xml-preview", summary="Genera XML CFDI 4.0 sin timbrar")
def generar_xml_preview(id: UUID, db: Session = Depends(get_db)):
    xml_bytes = srv.generar_xml_preview_bytes(db, id)
    return Response(content=xml_bytes, media_type="application/xml")

@router.get("/{id}/preview-pdf", summary="PDF de vista previa (marca BORRADOR)")
def preview_pdf(id: UUID, db: Session = Depends(get_db)):
    pdf_bytes = srv.generar_pdf_bytes(db, id, preview=True)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="preview-{id}.pdf"'})

@router.get("/{id}/pdf", summary="PDF final (TIMBRADA o CANCELADA)")
def factura_pdf(id: UUID, db: Session = Depends(get_db)):
    pdf_bytes = srv.generar_pdf_bytes(db, id, preview=False)
    # El nombre del archivo se podría obtener del servicio también si se quisiera.
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="factura-{id}.pdf"'})

@router.get("/{id}/xml", summary="Descargar XML timbrado")
def descargar_xml_timbrado(id: UUID, db: Session = Depends(get_db)):
    xml_path, filename = srv.obtener_ruta_xml_timbrado(db, id)
    
    if not os.path.isabs(xml_path):
        base_dir = getattr(settings, "DATA_DIR", "/data")
        xml_path = os.path.join(base_dir, xml_path.lstrip("/"))

    if not os.path.exists(xml_path):
        raise HTTPException(status_code=404, detail="El archivo XML no se encuentra en el servidor")

    return FileResponse(path=xml_path, media_type="application/xml", filename=filename)