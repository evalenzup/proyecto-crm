# app/api/conciliacion.py
"""Conciliación bancaria — /api/conciliacion"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.conciliacion import AREAS
from app.models.usuario import RolUsuario, Usuario
from app.schemas.conciliacion import (
    AreaOut, ComplementoPago, ConciliacionDetalleOut, ConciliacionListOut,
    EgresoEnlazado, EnlaceEgresos, EnlaceFacturas, FacturaEnlazada,
    MovimientoOut, MovimientoUpdate, Sugerencia,
)
from app.services import auditoria_service as audit_svc
from app.services import conciliacion_service as svc
from app.services import conciliacion_sugerencias as sug_svc

# Todo el módulo va restringido a ADMIN y SUPERADMIN: la conciliación toca
# facturación, gastos y saldos del banco, y quien la trabaja necesita ver las
# tres empresas del RFC. require_admin_or_above se aplica en cada endpoint.
router = APIRouter()

MAX_PDF_MB = 20


def _empresa_activa(empresa_id: Optional[UUID], current_user: Usuario) -> UUID:
    """La empresa sobre la que se trabaja, sin dejar que la petición mande."""
    if current_user.rol in (RolUsuario.SUPERVISOR, RolUsuario.ESTANDAR,
                            RolUsuario.OPERATIVO):
        if not current_user.empresa_id:
            raise HTTPException(status_code=400,
                                detail="Tu cuenta no tiene una empresa asignada.")
        return current_user.empresa_id
    if empresa_id:
        return empresa_id
    if current_user.empresa_id:
        return current_user.empresa_id
    raise HTTPException(status_code=400, detail="Se requiere empresa_id")


def _factura_out(f, complementos=None) -> FacturaEnlazada:
    # fecha_emision viene como datetime del modelo; el esquema expone la fecha
    emision = f.fecha_emision
    if emision is not None and hasattr(emision, "date"):
        emision = emision.date()
    return FacturaEnlazada(
        id=f.id, folio=f"{f.serie}-{f.folio}", total=f.total,
        fecha_emision=emision,
        cliente_nombre=f.cliente.nombre_comercial if f.cliente else None,
        empresa_nombre=f.empresa.nombre_comercial if f.empresa else None,
        estatus=getattr(f.estatus, "value", f.estatus),
        metodo_pago=f.metodo_pago,
        complementos=complementos or [],
    )


def _egreso_out(e) -> EgresoEnlazado:
    return EgresoEnlazado(
        id=e.id, proveedor=e.proveedor, descripcion=e.descripcion, monto=e.monto,
        fecha_egreso=e.fecha_egreso,
        categoria=getattr(e.categoria, "value", e.categoria) if e.categoria else None,
        empresa_nombre=e.empresa.nombre_comercial if getattr(e, "empresa", None) else None,
        archivo_pdf=e.archivo_pdf or e.path_documento,
    )


def _movimiento_out(m, db: Optional[Session] = None) -> MovimientoOut:
    comps = svc.complementos_de(db, [f.id for f in m.facturas]) if db and m.facturas else {}
    facturas = [_factura_out(f, comps.get(f.id)) for f in m.facturas]
    egresos = [_egreso_out(e) for e in m.egresos]
    total = (sum((f.total for f in facturas), Decimal("0"))
             + sum((e.monto for e in egresos), Decimal("0")))
    return MovimientoOut(
        id=m.id, orden=m.orden, fecha=m.fecha, concepto=m.concepto,
        deposito=m.deposito, retiro=m.retiro, comentario=m.comentario,
        area=m.area, conciliado=m.conciliado, facturas=facturas, egresos=egresos,
        suma_facturas=total,
    )


def _conciliacion_out(c, con_movimientos: bool, db: Optional[Session] = None):
    base = dict(
        id=c.id, periodo_inicio=c.periodo_inicio, periodo_fin=c.periodo_fin,
        banco=c.banco, cuenta=c.cuenta, estado=c.estado,
        saldo_inicial=c.saldo_inicial, saldo_final=c.saldo_final,
        total_depositos=c.total_depositos, total_retiros=c.total_retiros,
        n_depositos=c.n_depositos, n_retiros=c.n_retiros,
        total_movimientos=c.total_movimientos, conciliados=c.conciliados,
        tiene_archivo=bool(c.archivo_path and os.path.exists(c.archivo_path)),
        archivo_nombre=c.archivo_nombre,
        creado_en=c.creado_en,
    )
    if con_movimientos:
        return ConciliacionDetalleOut(
            **base, movimientos=[_movimiento_out(m, db) for m in c.movimientos])
    return ConciliacionListOut(**base)


# ── Catálogo ─────────────────────────────────────────────────────────────────

@router.get("/areas", response_model=List[AreaOut])
def listar_areas(current_user: Usuario = Depends(deps.require_admin_or_above)):
    return [AreaOut(clave=k, nombre=v) for k, v in AREAS.items()]


# ── Conciliaciones ───────────────────────────────────────────────────────────

@router.get("", response_model=List[ConciliacionListOut])
def listar(
    empresa_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    eid = _empresa_activa(empresa_id, current_user)
    return [_conciliacion_out(c, False) for c in svc.listar(db, eid)]


@router.post("", response_model=List[ConciliacionDetalleOut], status_code=201)
async def importar(
    request: Request,
    archivo: UploadFile = File(...),
    empresa_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    """Sube el movimiento de cuenta y crea una conciliación por periodo.

    Acepta el Excel que el banco deja bajar por rango de fechas —que es el
    camino habitual, porque el PDF no existe hasta el mes siguiente— y también
    el PDF para los meses ya cerrados. Un Excel con las dos quincenas en hojas
    distintas produce dos conciliaciones.
    """
    eid = _empresa_activa(empresa_id, current_user)

    nombre = archivo.filename or ""
    if not nombre.lower().endswith((".pdf", ".xlsx", ".xlsm", ".xls")):
        raise HTTPException(
            status_code=422,
            detail="El archivo debe ser el Excel que descargas del banco o el PDF "
                   "del estado de cuenta.")
    contenido = await archivo.read()
    if len(contenido) > MAX_PDF_MB * 1024 * 1024:
        raise HTTPException(status_code=422,
                            detail=f"El archivo no puede pesar más de {MAX_PDF_MB} MB.")

    creadas = svc.importar(db, empresa_id=eid, pdf_bytes=contenido,
                           nombre_archivo=nombre or "estado.pdf",
                           usuario_id=current_user.id)
    for conc in creadas:
        audit_svc.registrar(
            db, accion="IMPORTAR_ESTADO_CUENTA", entidad="conciliacion_bancaria",
            usuario_id=current_user.id, usuario_email=current_user.email,
            empresa_id=eid, entidad_id=str(conc.id),
            detalle={"periodo": f"{conc.periodo_inicio}–{conc.periodo_fin}",
                     "movimientos": conc.total_movimientos, "archivo": nombre},
            ip=audit_svc.get_ip(request),
        )
    db.commit()
    return [_conciliacion_out(svc.obtener(db, c.id), True, db) for c in creadas]


@router.get("/{conciliacion_id}", response_model=ConciliacionDetalleOut)
def obtener(
    conciliacion_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    return _conciliacion_out(svc.obtener(db, conciliacion_id), True, db)


@router.delete("/{conciliacion_id}", status_code=204)
def eliminar(
    conciliacion_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    conc = svc.obtener(db, conciliacion_id)
    audit_svc.registrar(
        db, accion="ELIMINAR_ESTADO_CUENTA", entidad="conciliacion_bancaria",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=conc.empresa_id, entidad_id=str(conciliacion_id),
        detalle={"periodo": f"{conc.periodo_inicio}–{conc.periodo_fin}"},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    svc.eliminar(db, conciliacion_id)


@router.get("/{conciliacion_id}/pdf")
def descargar_pdf(
    conciliacion_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    """El estado de cuenta original, tal como se subió."""
    conc = svc.obtener(db, conciliacion_id)
    if not conc.archivo_path or not os.path.exists(conc.archivo_path):
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible.")
    es_excel = conc.archivo_path.lower().endswith((".xlsx", ".xlsm", ".xls"))
    return FileResponse(
        conc.archivo_path,
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if es_excel else "application/pdf"),
        filename=conc.archivo_nombre or (
            f"estado-{conc.periodo_inicio:%Y-%m}{'.xlsx' if es_excel else '.pdf'}"),
    )


@router.get("/{conciliacion_id}/export-excel")
def exportar(
    conciliacion_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    conc = svc.obtener(db, conciliacion_id)
    archivo = svc.exportar_excel(db, conciliacion_id)
    nombre = f"conciliacion-{conc.periodo_inicio:%Y-%m}.xlsx"
    audit_svc.registrar(
        db, accion=audit_svc.EXPORTAR_EXCEL, entidad="conciliacion_bancaria",
        usuario_id=current_user.id, usuario_email=current_user.email,
        empresa_id=conc.empresa_id, entidad_id=str(conciliacion_id),
        detalle={"periodo": f"{conc.periodo_inicio}–{conc.periodo_fin}"},
        ip=audit_svc.get_ip(request),
    )
    db.commit()
    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{conciliacion_id}/sugerencias", response_model=dict)
def sugerencias(
    conciliacion_id: UUID,
    empresa_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    """Candidatas por movimiento: {movimiento_id: [sugerencia, ...]}.

    Va aparte del detalle para no retrasar la carga de la pantalla: los
    movimientos aparecen de inmediato y las sugerencias llegan después.
    """
    eid = _empresa_activa(empresa_id, current_user)
    conc = svc.obtener(db, conciliacion_id)
    empresas = svc._empresas_hermanas(db, conc.empresa_id or eid)
    return sug_svc.calcular(db, conciliacion_id, empresas)


# ── Movimientos ──────────────────────────────────────────────────────────────

@router.put("/movimientos/{movimiento_id}", response_model=MovimientoOut)
def actualizar_movimiento(
    movimiento_id: UUID,
    payload: MovimientoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    datos = payload.model_dump(exclude_unset=True)
    return _movimiento_out(svc.actualizar_movimiento(db, movimiento_id, datos), db)


@router.delete("/movimientos/{movimiento_id}/enlaces", response_model=MovimientoOut)
def limpiar_movimiento(
    movimiento_id: UUID,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    """Deshace la conciliación del movimiento: quita enlaces, comentario y área."""
    return _movimiento_out(svc.limpiar_movimiento(db, movimiento_id), db)


@router.put("/movimientos/{movimiento_id}/facturas", response_model=MovimientoOut)
def enlazar_facturas(
    movimiento_id: UUID,
    payload: EnlaceFacturas,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    """Fija qué facturas componen el movimiento. Reemplaza las anteriores."""
    return _movimiento_out(svc.enlazar_facturas(
        db, movimiento_id, payload.factura_ids, usuario_id=current_user.id), db)


@router.put("/movimientos/{movimiento_id}/egresos", response_model=MovimientoOut)
def enlazar_egresos(
    movimiento_id: UUID,
    payload: EnlaceEgresos,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    """Fija qué gastos componen el retiro. Reemplaza los anteriores."""
    return _movimiento_out(svc.enlazar_egresos(db, movimiento_id, payload.egreso_ids), db)


@router.get("/egresos/busqueda", response_model=List[EgresoEnlazado])
def buscar_egresos(
    q: str = Query("", description="Proveedor o descripción del gasto"),
    empresa_id: Optional[UUID] = Query(None),
    limite: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    eid = _empresa_activa(empresa_id, current_user)
    return [_egreso_out(e) for e in svc.buscar_egresos(db, empresa_id=eid, q=q, limite=limite)]


@router.get("/facturas/busqueda", response_model=List[FacturaEnlazada])
def buscar_facturas(
    q: str = Query("", description="Folio (1585, A-1585) o nombre del cliente"),
    empresa_id: Optional[UUID] = Query(None),
    limite: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(deps.require_admin_or_above),
):
    eid = _empresa_activa(empresa_id, current_user)
    facturas = svc.buscar_facturas(db, empresa_id=eid, q=q, limite=limite)
    comps = svc.complementos_de(db, [f.id for f in facturas])
    return [_factura_out(f, comps.get(f.id)) for f in facturas]
