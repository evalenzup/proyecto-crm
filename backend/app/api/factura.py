# app/api/factura.py
from __future__ import annotations

import logging
import os, re
import hashlib
from uuid import UUID
from typing import List, Optional, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, selectinload

from cryptography.hazmat.primitives.serialization import load_der_private_key, load_pem_private_key
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates

from app.config import settings
from app.database import get_db
from app.services.cfdi40_xml import build_cfdi40_xml_sin_timbrar
from app.services.timbrado_factmoderna import FacturacionModernaPAC

from app.catalogos_sat.facturacion import (
    obtener_todas_formas_pago,
    obtener_todos_metodos_pago,
    obtener_todos_usos_cfdi,
)

from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import (
    FacturaCreate,
    FacturaUpdate,
    FacturaOut,
)

from app.services.factura_service import (
    crear_factura,
    actualizar_factura,
    obtener_por_serie_folio,
    timbrar_factura,
    cancelar_factura,
    listar_facturas as listar_facturas_srv,  # <- servicio de listado (alias)
)

from app.services.pdf_factura import load_factura_full, render_factura_pdf_bytes_from_model

_pac = FacturacionModernaPAC()


logger = logging.getLogger("app")
router = APIRouter()


# ────────────────────────────────────────────────────────────────
# Helpers

def _with_conceptos(q):
    """Asegura cargar conceptos para serializar FacturaOut."""
    return q.options(selectinload(Factura.conceptos))


def _empresa_key_path_local(emp) -> str:
    """
    Ruta efectiva de la .key del CSD:
      - Si empresa.archivo_key trae un nombre/relativo → usar en settings.CERT_DIR
      - Si no, fallback: <empresa.id>.key en settings.CERT_DIR
    """
    base = settings.CERT_DIR
    if getattr(emp, "archivo_key", None):
        name = os.path.basename(emp.archivo_key)
        return os.path.join(base, name)
    return os.path.join(base, f"{emp.id}.key")


def _empresa_cer_path_local(emp) -> str:
    """
    Ruta efectiva del .cer del CSD (mismo criterio que key).
    """
    base = settings.CERT_DIR
    if getattr(emp, "archivo_cer", None):
        name = os.path.basename(emp.archivo_cer)
        return os.path.join(base, name)
    return os.path.join(base, f"{emp.id}.cer")


def _empresa_pwd_bytes_local(emp) -> Optional[bytes]:
    """
    Password de la .key directamente desde la DB (opción A).
    Debe estar en texto plano en empresa.contrasena.
    """
    pw = getattr(emp, "contrasena", None)
    if not pw:
        return None
    return pw.encode("utf-8")


# ────────────────────────────────────────────────────────────────
# Modelos de respuesta

class FacturasPageOut(BaseModel):
    items: List[FacturaOut]
    total: int
    limit: int
    offset: int


# ────────────────────────────────────────────────────────────────
# Endpoints

@router.get("/schema", summary="Obtener el schema del modelo")
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
    metodos_de_pago = obtener_todos_metodos_pago()
    props["metodo_pago"]["x-options"] = [
        {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"} for r in metodos_de_pago
    ]
    props["metodo_pago"]["enum"] = [r["clave"] for r in metodos_de_pago]

    # Forma de pago
    formas_pago = obtener_todas_formas_pago()
    props["forma_pago"]["x-options"] = [
         {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"} for r in formas_pago
    ]
    props["forma_pago"]["enum"] = [r["clave"] for r in formas_pago]

    # Uso CFDI
    catalogos_usos = obtener_todos_usos_cfdi()
    props["uso_cfdi"]["x-options"] = [
        {"value": r["clave"], "label": f"{r['clave']} – {r['descripcion']}"} for r in catalogos_usos
    ]
    props["uso_cfdi"]["enum"] = [r["clave"] for r in catalogos_usos]

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
    except Exception:
        logger.exception("Error al crear factura")
        raise HTTPException(status_code=500, detail="Error al crear la factura")


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
    except Exception:
        logger.exception("Error al actualizar factura %s", id)
        raise HTTPException(status_code=500, detail="Error al actualizar la factura")


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





@router.get("/{id}/preview-pdf", summary="PDF de vista previa (marca BORRADOR)", response_class=Response)
def preview_pdf(id: UUID, db: Session = Depends(get_db)):
    try:
        pdf_bytes = render_factura_pdf_bytes_from_model(db, id, preview=True, logo_path=None)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="preview-{id}.pdf"'}
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Factura no encontrada")


@router.get("/{id}/pdf", summary="PDF final (TIMBRADA sin marca; CANCELADA con marca)", response_class=Response)
def factura_pdf(id: UUID, db: Session = Depends(get_db)):
    f = load_factura_full(db, id)
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if f.estatus == "BORRADOR":
        raise HTTPException(status_code=409, detail="Debe estar TIMBRADA o CANCELADA para PDF final")
    pdf_bytes = render_factura_pdf_bytes_from_model(db, id, preview=False, logo_path=None)
    filename = f"factura-{f.serie}-{f.folio}.pdf" if f.serie and f.folio else f"factura-{id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename=\"{filename}\"'}
    )


def _safe_ascii(s: str) -> str:
    """
    Convierte a ASCII simple y elimina caracteres no seguros para nombre de archivo.
    """
    try:
        import unicodedata
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        s = re.sub(r"[^A-Za-z0-9._-]+", "", s or "")
    s = re.sub(r"[^A-Za-z0-9._-]+", "", s or "")
    return s.strip() or "archivo"

def _factura_pdf_filename(f: Factura) -> str:
    rfc = (getattr(getattr(f, "empresa", None), "rfc", None) or "RFC").upper()
    rfc = _safe_ascii(rfc)
    folio = str(getattr(f, "folio", "") or "").strip()
    serie = (getattr(f, "serie", None) or "").strip()
    if serie:
        serie = _safe_ascii(serie)
        return f"{rfc}-factura-{serie}-{folio}.pdf"
    return f"{rfc}-factura-{folio}.pdf"

@router.get("/{id}/pdf-download")
def descargar_factura_pdf(id: UUID, db: Session = Depends(get_db)) -> Response:
    f: Factura | None = (
        db.query(Factura)
        .filter(Factura.id == id)
        .options()  # si quieres, carga perezosa está ok porque el render vuelve a cargar
        .first()
    )
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Solo permitir PDF definitivo para timbradas
    if (f.estatus or "").upper() != "TIMBRADA":
        raise HTTPException(status_code=400, detail="Solo se puede descargar el PDF cuando la factura está TIMBRADA")

    pdf_bytes = render_factura_pdf_bytes_from_model(db, id, preview=False)

    filename = _factura_pdf_filename(f)
    #print("FacturaNombre:", filename)
    headers = {
        # Forzar descarga y pasar nombre de archivo (ASCII + fallback RFC 5987)
        "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}',
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/{id}/xml-preview", summary="Genera XML CFDI 4.0 sin timbrar")
def generar_xml_preview(id: UUID, db: Session = Depends(get_db)):
    try:
        xml_bytes = build_cfdi40_xml_sin_timbrar(db, id)
        return Response(content=xml_bytes, media_type="application/xml")
    except ValueError:
        raise HTTPException(404, "Factura no encontrada")
    except Exception as e:
        raise HTTPException(400, f"Error generando XML: {e}")



@router.post(
    "/{id}/timbrar",
    summary="Timbrar factura con Facturación Moderna"
)
def timbrar_endpoint(
    id: UUID = Path(...),
    db: Session = Depends(get_db),
):
    # Validación rápida para evitar llamar al PAC si no procede
    f = db.query(Factura).filter(Factura.id == id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if f.estatus != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se puede timbrar una factura en BORRADOR")

    try:
        result = _pac.timbrar_factura(
            db=db,
            factura_id=id,
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
        logger.exception("Error al timbrar %s", id)
        raise HTTPException(status_code=400, detail=f"Error al timbrar la factura: {e}")

class CancelarIn(BaseModel):
    motivo_cancelacion: str = "02"                 # 01,02,03,04
    folio_fiscal_sustituto: str | None = None

    @field_validator("motivo_cancelacion")
    @classmethod
    def check_motivo(cls, v: str):
        v = (v or "").strip()
        if v not in {"01", "02", "03", "04"}:
            raise ValueError("Motivo inválido. Valores permitidos: 01, 02, 03, 04.")
        return v

@router.post("/facturas/{factura_id}/cancelar")
def solicitar_cancelacion_cfdi(
    factura_id: UUID,
    payload: CancelarIn,
    db: Session = Depends(get_db),
):
    svc = FacturacionModernaPAC(timeout=60.0)
    try:
        out = svc.solicitar_cancelacion_cfdi(
            db=db,
            factura_id=factura_id,
            motivo=payload.motivo_cancelacion,
            folio_sustitucion=payload.folio_fiscal_sustituto,
        )
        # out = {"estatus": "...", "uuid": "...", "code": "...", "message": "..."}
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error inesperado al solicitar cancelación")

@router.get("/{id}/diag-csd")
def diag_csd(id: UUID, db: Session = Depends(get_db)):
    """
    Diagnóstico de CSD/contraseña exactamente como los usaría el builder.
    NO firma ni genera XML: sólo intenta abrir la .key con la pass de la DB.
    """
    f = (
        db.query(Factura)
        .options(selectinload(Factura.empresa))
        .filter(Factura.id == id)
        .first()
    )
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    emp = f.empresa

    key_path = _empresa_key_path_local(emp)
    cer_path = _empresa_cer_path_local(emp)
    pwd = _empresa_pwd_bytes_local(emp)

    can_open = False
    method = None
    error = None

    try:
        data = open(key_path, "rb").read()
        # DER (PKCS#8 o PKCS#1 con envoltura DER)
        try:
            load_der_private_key(data, password=pwd)
            can_open, method = True, "DER"
        except Exception as e1:
            # PEM
            try:
                load_pem_private_key(data, password=pwd)
                can_open, method = True, "PEM"
            except Exception as e2:
                # PKCS#12
                try:
                    priv, _, _ = load_key_and_certificates(data, pwd)
                    can_open, method = (priv is not None), "PKCS12" if priv else None
                    if not can_open:
                        error = str(e2)
                except Exception as e3:
                    error = f"DER:{e1} | PEM:{e2} | P12:{e3}"
    except Exception as e:
        error = str(e)

    return {
        "empresa_id": str(emp.id),
        "cer_path": cer_path, "cer_exists": os.path.exists(cer_path),
        "key_path": key_path, "key_exists": os.path.exists(key_path),
        "pwd_len": (len(pwd) if pwd else None),
        "pwd_sha8": (hashlib.sha256(pwd).hexdigest()[:8] if pwd else None),
        "can_open_key": can_open, "method": method, "error": error,
    }

@router.get("/{id}/xml", summary="Descargar XML timbrado", response_class=FileResponse)
def descargar_xml_timbrado(
    id: UUID,
    db: Session = Depends(get_db),
):
    """
    Devuelve el XML timbrado como archivo descargable.
    Requiere que la factura esté TIMBRADA y que exista `xml_path`.
    """
    f = db.query(Factura).filter(Factura.id == id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if f.estatus != "TIMBRADA":
        raise HTTPException(status_code=409, detail="La factura debe estar TIMBRADA para descargar el XML")

    if not f.xml_path:
        raise HTTPException(status_code=404, detail="No hay ruta de XML registrada para esta factura")

    # Resolver ruta: soporta absoluta o relativa a DATA_DIR
    xml_path = f.xml_path
    if not os.path.isabs(xml_path):
        base_dir = getattr(settings, "DATA_DIR", "/data")
        xml_path = os.path.join(base_dir, xml_path.lstrip("/"))

    if not os.path.exists(xml_path):
        raise HTTPException(status_code=404, detail="El archivo XML no se encuentra en el servidor")

    # Nombre de descarga
    emisor_rfc = (getattr(f.empresa, "rfc", "") or "EMISOR").upper()
    if f.serie and f.folio:
        filename = f"{emisor_rfc}-{f.serie}-{f.folio}.xml"
    else:
        filename = f"{emisor_rfc}-{f.id}.xml"

    # Servir archivo
    return FileResponse(
        path=xml_path,
        media_type="application/xml",
        filename=filename,
    )