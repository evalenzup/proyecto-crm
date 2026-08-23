# app/services/factura_service.py
from __future__ import annotations
import logging
import os
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from typing import List, Optional, Tuple, Literal
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, asc, desc, exists
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import re
from datetime import date, datetime, timezone

from app.models.factura import Factura
from app.models.factura_detalle import FacturaDetalle
from app.schemas.factura import FacturaCreate, FacturaUpdate
from app.models.associations import cliente_empresa as cliente_empresa_association
from app.services.timbrado_factmoderna import FacturacionModernaPAC
from app.services.cfdi40_xml import build_cfdi40_xml_sin_timbrar
from app.services import notificacion_service as notif_svc
from app.services.pac_errors import interpretar_error_pac
from app.services.pdf_factura import (
    render_factura_pdf_bytes_from_model,
    load_factura_full,
)

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


def obtener_factura(db: Session, id: UUID) -> Factura:
    factura = (
        db.query(Factura)
        .options(selectinload(Factura.conceptos), selectinload(Factura.cliente))
        .filter(Factura.id == id)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura


def eliminar_factura(db: Session, id: UUID):
    factura = db.query(Factura).filter(Factura.id == id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "BORRADOR":
        raise HTTPException(
            status_code=409, detail="Solo se pueden eliminar facturas en BORRADOR"
        )
    db.delete(factura)
    db.commit()
    return


def crear_factura(db: Session, payload: FacturaCreate) -> Factura:
    association_exists = (
        db.query(cliente_empresa_association)
        .filter_by(cliente_id=payload.cliente_id, empresa_id=payload.empresa_id)
        .first()
    )
    if not association_exists:
        raise HTTPException(
            status_code=422,
            detail=f"El cliente ID {payload.cliente_id} no está asociado a la empresa ID {payload.empresa_id}.",
        )

    serie = (payload.serie or "A").upper()
    folio = (
        payload.folio
        if payload.folio is not None
        else siguiente_folio(db, payload.empresa_id, serie)
    )

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
        # Relacionados
        # Relacionados (Fix: pad to 2 digits, e.g. "4" -> "04")
        cfdi_relacionados_tipo=(
            payload.cfdi_relacionados_tipo.zfill(2)
            if payload.cfdi_relacionados_tipo
            else None
        ),
        cfdi_relacionados=payload.cfdi_relacionados,
    )

    subtotal_general = Decimal("0")
    traslados_general = Decimal("0")
    retenciones_general = Decimal("0")
    
    # Track the exact sum of individual rounded importes to ensure Comprobante.Total matches Sum(Concepto.Importe + Impuestos)
    total_exacto = Decimal("0")

    for c in payload.conceptos:
        base_calculo = ((c.cantidad or Decimal("0")) * c.valor_unitario - (c.descuento or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        iva_importe = (base_calculo * (c.iva_tasa or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ret_iva_importe = (base_calculo * (c.ret_iva_tasa or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ret_isr_importe = (base_calculo * (c.ret_isr_tasa or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        importe_concepto = base_calculo + iva_importe - ret_iva_importe - ret_isr_importe

        subtotal_general += base_calculo
        traslados_general += iva_importe
        retenciones_general += ret_iva_importe + ret_isr_importe
        total_exacto += importe_concepto

        factura.conceptos.append(
            FacturaDetalle(
                **c.dict(),
                importe=importe_concepto,
                iva_importe=iva_importe,
                ret_iva_importe=ret_iva_importe,
                ret_isr_importe=ret_isr_importe,
            )
        )

    # Penny balancing for Factura Total
    factura.subtotal = subtotal_general
    factura.impuestos_trasladados = traslados_general
    factura.impuestos_retenidos = retenciones_general
    
    # El Total CFDI debe ser estrictamente Subtotal - Descuento + Traslados - Retenciones
    calculated_total = subtotal_general + traslados_general - retenciones_general
    
    if diff := total_exacto - calculated_total:
         if abs(diff) <= Decimal("0.99") and factura.conceptos:
               # Ajustar el último traslado general para cuadrar el total
               factura.impuestos_trasladados += diff
               traslados_general += diff
               calculated_total += diff
               # También ajustamos el último concepto
               factura.conceptos[-1].iva_importe += diff
               factura.conceptos[-1].importe += diff

    factura.total = calculated_total

    db.add(factura)
    try:
        db.commit()
        db.refresh(factura)
        return factura
    except IntegrityError as e:
        db.rollback()
        if "uq_fact_serie_folio_por_empresa" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail=f"El folio {factura.folio} para la serie '{factura.serie}' ya existe.",
            )
        raise HTTPException(
            status_code=500, detail=f"Error de integridad en la base de datos: {e.orig}"
        )


def actualizar_factura(
    db: Session, factura_id: UUID, payload: FacturaUpdate
) -> Factura:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    update_data = payload.dict(exclude_unset=True)

    if factura.estatus in ["TIMBRADA", "CANCELADA"]:
        campos_permitidos = {
            "status_pago",
            "fecha_pago",
            "fecha_cobro",
            "observaciones",
        }

        for key, value in update_data.items():
            if key in campos_permitidos:
                setattr(factura, key, value)
    else:
        if (
            "cliente_id" in update_data
            and payload.cliente_id
            and payload.cliente_id != factura.cliente_id
        ):
            association_exists = (
                db.query(cliente_empresa_association)
                .filter_by(cliente_id=payload.cliente_id, empresa_id=factura.empresa_id)
                .first()
            )
            if not association_exists:
                raise HTTPException(
                    status_code=422,
                    detail=f"El nuevo cliente ID {payload.cliente_id} no está asociado a la empresa.",
                )

        for key, value in update_data.items():
            if key in [
                "cfdi_relacionados_tipo",
                "cfdi_relacionados",
            ]:  # Permitir update explícito si viene en payload
                val = value
                if key == "cfdi_relacionados_tipo" and isinstance(val, str):
                    val = val.zfill(2)
                setattr(factura, key, val)
            if key != "conceptos":
                setattr(factura, key, value)

        if payload.conceptos is not None:
            db.query(FacturaDetalle).where(
                FacturaDetalle.factura_id == factura.id
            ).delete()
            subtotal_general = Decimal("0")
            traslados_general = Decimal("0")
            retenciones_general = Decimal("0")
            total_exacto = Decimal("0")

            for c in payload.conceptos:
                base_calculo = ((c.cantidad or Decimal("0")) * c.valor_unitario - (c.descuento or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                iva_importe = (base_calculo * (c.iva_tasa or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                ret_iva_importe = (base_calculo * (c.ret_iva_tasa or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                ret_isr_importe = (base_calculo * (c.ret_isr_tasa or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                
                importe_concepto = base_calculo + iva_importe - ret_iva_importe - ret_isr_importe

                subtotal_general += base_calculo
                traslados_general += iva_importe
                retenciones_general += ret_iva_importe + ret_isr_importe
                total_exacto += importe_concepto

                factura.conceptos.append(
                    FacturaDetalle(
                        **c.dict(),
                        factura_id=factura.id,
                        importe=importe_concepto,
                        iva_importe=iva_importe,
                        ret_iva_importe=ret_iva_importe,
                        ret_isr_importe=ret_isr_importe,
                    )
                )

            factura.subtotal = subtotal_general
            factura.impuestos_trasladados = traslados_general
            factura.impuestos_retenidos = retenciones_general
            
            calculated_total = subtotal_general + traslados_general - retenciones_general
            
            if diff := total_exacto - calculated_total:
                 if abs(diff) <= Decimal("0.99") and factura.conceptos:
                       factura.impuestos_trasladados += diff
                       traslados_general += diff
                       calculated_total += diff
                       factura.conceptos[-1].iva_importe += diff
                       factura.conceptos[-1].importe += diff

            factura.total = calculated_total

    db.commit()
    db.refresh(factura)
    return factura


def duplicar_factura(
    db: Session, factura_id: UUID, como_sustituta: bool = False
) -> Factura:
    """
    Copia la factura como nuevo BORRADOR.

    Con ``como_sustituta=True`` la nueva factura nace ya relacionada al CFDI
    original con TipoRelacion 04 (Sustitución de los CFDI previos), que es lo
    que el SAT exige para poder cancelar la original con motivo 01. Es la forma
    de que la relación quede bien desde el origen, en vez de depender de que el
    usuario la capture a mano después.
    """
    original = obtener_factura(db, factura_id)

    if como_sustituta and not original.cfdi_uuid:
        raise HTTPException(
            status_code=400,
            detail="Solo una factura timbrada puede sustituirse: la original no tiene UUID fiscal.",
        )

    # Calcular siguiente folio
    serie = original.serie
    folio = siguiente_folio(db, original.empresa_id, serie)

    nueva_factura = Factura(
        empresa_id=original.empresa_id,
        cliente_id=original.cliente_id,
        serie=serie,
        folio=folio,
        moneda=original.moneda,
        tipo_cambio=original.tipo_cambio,
        estatus="BORRADOR",
        status_pago="NO_PAGADA",
        # Reseteamos fechas de pago/cobro para la nueva factura
        fecha_pago=None,
        fecha_cobro=None,
        observaciones=original.observaciones,
        tipo_comprobante=original.tipo_comprobante,
        forma_pago=original.forma_pago,
        metodo_pago=original.metodo_pago,
        uso_cfdi=original.uso_cfdi,
        fecha_emision=datetime.now(timezone.utc), # Fecha actual en UTC
        lugar_expedicion=original.lugar_expedicion,
        condiciones_pago=original.condiciones_pago,
        rfc_proveedor_sat=original.rfc_proveedor_sat,

        # Relación de sustitución (04) hacia el CFDI que se va a cancelar
        cfdi_relacionados_tipo="04" if como_sustituta else None,
        cfdi_relacionados=original.cfdi_uuid if como_sustituta else None,

        # Copiamos totales (se podrían recalcular, pero si es copia fiel...)
        subtotal=original.subtotal,
        descuento=original.descuento,
        impuestos_trasladados=original.impuestos_trasladados,
        impuestos_retenidos=original.impuestos_retenidos,
        total=original.total,
    )
    
    # Copiar conceptos
    for c in original.conceptos:
         nueva_factura.conceptos.append(
            FacturaDetalle(
                clave_producto=c.clave_producto,
                no_identificacion=c.no_identificacion,
                cantidad=c.cantidad,
                clave_unidad=c.clave_unidad,
                unidad=c.unidad,
                descripcion=c.descripcion,
                valor_unitario=c.valor_unitario,
                importe=c.importe,
                descuento=c.descuento,
                objeto_imp=c.objeto_imp,
                
                # Impuestos
                iva_tasa=c.iva_tasa,
                iva_importe=c.iva_importe,
                
                ret_iva_tasa=c.ret_iva_tasa,
                ret_iva_importe=c.ret_iva_importe,
                
                ret_isr_tasa=c.ret_isr_tasa,
                ret_isr_importe=c.ret_isr_importe,
                
                # Campos adicionales
                tipo=c.tipo,
                requiere_lote=c.requiere_lote,
                lote=c.lote,
                # cuenta_predial no existe en el modelo actual
            )
         )

    db.add(nueva_factura)
    db.commit()
    db.refresh(nueva_factura)
    return nueva_factura


# ────────────────────────────────────────────────────────────────
# Acciones CFDI


def timbrar_factura(db: Session, factura_id: UUID) -> dict:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "BORRADOR":
        raise HTTPException(
            status_code=400, detail="Solo se puede timbrar una factura en BORRADOR"
        )

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
        try:
            notif_svc.crear_notificacion(
                db=db,
                empresa_id=factura.empresa_id,
                tipo=notif_svc.EXITO,
                titulo="Factura timbrada",
                mensaje=f"Factura {factura.serie}-{factura.folio} timbrada exitosamente.",
                metadata={"factura_id": str(factura_id)},
            )
        except Exception:
            pass  # La notificación no debe interrumpir el flujo principal
        return {"ok": True, **result}
    except HTTPException:
        raise
    except RuntimeError as e:
        code, detalle = interpretar_error_pac(e)
        raise HTTPException(status_code=code, detail=detalle)
    except Exception as e:
        logger.exception("Error de servicio al timbrar factura %s", factura_id)
        raise HTTPException(
            status_code=500, detail=f"Error interno al timbrar la factura: {e}"
        )


# Código con el que se marca una cancelación tramitada fuera del PAC. No es un
# código de Facturación Moderna: es etiqueta nuestra.
CODIGO_SAT_PORTAL = "SAT-PORTAL"


def _buscar_comprobante_por_uuid(db: Session, uuid_str: str):
    """
    Busca un CFDI por UUID entre facturas y complementos de pago.

    Returns:
        (documento | None, es_complemento: bool)
    """
    from app.models.pago import Pago

    doc = (
        db.query(Factura).filter(func.upper(Factura.cfdi_uuid) == uuid_str).first()
    )
    if doc:
        return doc, False
    pago = db.query(Pago).filter(func.upper(Pago.uuid) == uuid_str).first()
    return (pago, True) if pago else (None, False)


def _validar_sustitucion_motivo_01(
    db: Session, factura: Factura, folio_sustitucion: Optional[str]
) -> None:
    """
    Para el motivo 01 el SAT exige que el CFDI sustituto declare la relación
    ``TipoRelacion=04`` (Sustitución de los CFDI previos) apuntando al UUID de
    la factura que se cancela. Si no la trae, el SAT recibe la solicitud pero la
    rechaza con "Relación no válida o inexistente" y la factura se queda vigente
    sin que el usuario se entere.

    Además el sustituto tiene que seguir VIGENTE: señalar como reemplazo un
    comprobante que ya se canceló es pedirle al SAT que sustituya por algo que
    fiscalmente no existe, y descarta la solicitud. Le pasó a A-785, que declaraba
    a A-1202 estando A-1202 cancelada, y el trámite se perdió sin explicación.

    El sustituto puede ser una factura o un complemento de pago, así que se busca
    en los dos lados y el mensaje dice cuál es. Si no está en nuestra base (se
    emitió por fuera) no se puede validar y se deja pasar.
    """
    uuid_sust = (folio_sustitucion or "").strip().upper()
    uuid_cancelar = (factura.cfdi_uuid or "").strip().upper()
    if not uuid_sust or not uuid_cancelar:
        return

    sustituta, es_complemento = _buscar_comprobante_por_uuid(db, uuid_sust)
    if not sustituta:
        logger.warning(
            "Motivo 01: el CFDI sustituto %s no está en la base; no se puede "
            "validar antes de cancelar.", uuid_sust,
        )
        return

    tipo_doc = "el complemento de pago" if es_complemento else "la factura"
    etiqueta_doc = f"{tipo_doc} {sustituta.serie or ''}-{sustituta.folio}"
    estatus_sust = getattr(sustituta.estatus, "value", sustituta.estatus)

    # 1) ¿Sigue vigente? Un sustituto cancelado invalida la sustitución.
    if estatus_sust in ("CANCELADA", "CANCELADO"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede cancelar con motivo 01: {etiqueta_doc}, que se indicó "
                # El propio estatus trae el género que toca: CANCELADA para una
                # factura, CANCELADO para un complemento.
                f"como sustituto, está {estatus_sust}. El SAT no acepta que un comprobante "
                f"se reemplace por otro que ya no existe fiscalmente, y descarta la "
                f"solicitud sin avisar. Indica un sustituto vigente o cancela con "
                f"motivo 02 si en realidad no hubo reemplazo."
            ),
        )

    # 2) ¿Declara la relación? Sólo se puede comprobar en facturas: el sistema no
    #    guarda CfdiRelacionados de los complementos de pago (pago20_xml tampoco
    #    los emite), así que ahí no hay nada que revisar.
    if es_complemento:
        logger.warning(
            "Motivo 01: el sustituto %s es un complemento de pago; el sistema no "
            "guarda sus CFDI relacionados, así que no se puede validar la relación.",
            etiqueta_doc,
        )
        return

    tipo_rel = (sustituta.cfdi_relacionados_tipo or "").strip()
    relacionados = (sustituta.cfdi_relacionados or "").upper()

    if tipo_rel != "04" or uuid_cancelar not in relacionados:
        if not relacionados:
            problema = f"{etiqueta_doc}, indicada como sustituta, no declara ningún CFDI relacionado"
        elif tipo_rel != "04":
            problema = (
                f"{etiqueta_doc}, indicada como sustituta, usa el tipo de relación "
                f"'{tipo_rel}' en lugar de '04'"
            )
        else:
            problema = (
                f"la relación de {etiqueta_doc}, indicada como sustituta, apunta a otro CFDI"
            )
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede cancelar con motivo 01: {problema}. El SAT exige que el "
                "comprobante que sustituye declare la relación tipo 04 (Sustitución de "
                "los CFDI previos) hacia esta factura; de lo contrario rechaza la "
                "cancelación con «Relación no válida o inexistente». Como el sustituto "
                "ya está timbrado y no se puede modificar, emite una nueva factura "
                "sustituta con la relación correcta o cancela con motivo 02."
            ),
        )


def _complementos_pago_vigentes(db: Session, factura: Factura) -> list:
    """Complementos de pago que referencian a la factura y siguen sin cancelarse."""
    from app.models.pago import EstatusPago, Pago, PagoDocumentoRelacionado

    return (
        db.query(Pago)
        .join(PagoDocumentoRelacionado, PagoDocumentoRelacionado.pago_id == Pago.id)
        .filter(
            PagoDocumentoRelacionado.factura_id == factura.id,
            Pago.estatus.in_([EstatusPago.TIMBRADO, EstatusPago.EN_CANCELACION]),
        )
        .all()
    )


def diagnostico_cancelacion(db: Session, doc) -> dict:
    """
    Consulta al SAT si el CFDI se puede cancelar y, si no, explica por qué.

    El SAT marca "No cancelable" cuando otro comprobante lo referencia —lo más
    común, un complemento de pago—: hay que cancelar primero ese comprobante.
    Sin este aviso el usuario envía una solicitud que el SAT va a rechazar y se
    queda sin saber la razón.

    Sirve para Factura y para Pago (a los complementos no se les buscan
    complementos relacionados, sólo se reporta el motivo del SAT).
    """
    from app.services import sat_cfdi_service as sat_svc

    # "No cancelable" NO bloquea: es sólo una advertencia. Comprobado con A-2202
    # (2026-08-06): enviada desde el portal del SAT con motivo 01 y el UUID que la
    # reemplaza, el SAT la aceptó, rompió la relación él mismo y la pasó de
    # "No cancelable" a "Cancelable con aceptación" / "En proceso".
    # puede_cancelar=False se reserva para lo definitivo: ya cancelada en el SAT.
    resultado = {
        "puede_cancelar": True,
        "motivo": None,
        "advertencia": None,
        "estado_sat": None,
        "es_cancelable": None,
        "complementos": [],
        "relacionadas": [],
    }
    uuid_cfdi = (getattr(doc, "cfdi_uuid", None) or getattr(doc, "uuid", None) or "").strip()
    if not uuid_cfdi:
        return resultado

    try:
        rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(doc)
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_emisor, rfc_receptor=rfc_receptor,
            total=total, uuid=uuid_cfdi,
        )
    except Exception as exc:  # noqa: BLE001 — si el SAT no responde, no bloqueamos
        logger.info("No se pudo consultar el SAT antes de cancelar: %s", exc)
        return resultado

    if not acuse.encontrado:
        return resultado

    resultado["estado_sat"] = acuse.estado
    resultado["es_cancelable"] = acuse.es_cancelable

    if acuse.cancelado_por_sat:
        resultado.update(
            puede_cancelar=False,
            motivo="El CFDI ya está cancelado en el SAT. Usa «Verificar con SAT» para actualizar el estatus.",
        )
        return resultado

    if acuse.no_cancelable:
        # Los complementos de pago sólo aplican cuando el documento es una factura
        complementos = (
            _complementos_pago_vigentes(db, doc) if isinstance(doc, Factura) else []
        )
        # El SAT también bloquea cuando OTRO CFDI la referencia (por ejemplo la
        # factura que la sustituye o una nota de crédito). Se nombran para que el
        # usuario sepa cuál es, en vez de recibir un mensaje genérico.
        relacionadas = []
        if isinstance(doc, Factura) and doc.cfdi_uuid:
            relacionadas = (
                db.query(Factura)
                .filter(
                    Factura.empresa_id == doc.empresa_id,
                    func.upper(Factura.cfdi_relacionados).contains(doc.cfdi_uuid.upper()),
                    Factura.id != doc.id,
                    Factura.estatus.in_(["TIMBRADA", "EN_CANCELACION"]),
                )
                .all()
            )
        resultado["relacionadas"] = [
            {"id": str(x.id), "folio": f"{x.serie}-{x.folio}",
             "tipo_relacion": x.cfdi_relacionados_tipo}
            for x in relacionadas
        ]
        resultado["complementos"] = [
            {"id": str(p.id), "folio": f"{p.serie or ''}-{p.folio}",
             "estatus": getattr(p.estatus, "value", p.estatus)}
            for p in complementos
        ]
        if complementos:
            listado = ", ".join(c["folio"] for c in resultado["complementos"])
            uno = len(complementos) == 1
            motivo = (
                "El SAT reporta esta factura como «No cancelable» porque tiene "
                + (f"relacionado el complemento de pago {listado}. " if uno
                   else f"relacionados los complementos de pago {listado}. ")
                + ("Debe cancelarse primero ese complemento" if uno
                   else "Deben cancelarse primero esos complementos")
                + " y después la factura."
            )
        elif relacionadas:
            listado = ", ".join(r["folio"] for r in resultado["relacionadas"])
            uno = len(relacionadas) == 1
            motivo = (
                "El SAT reporta esta factura como «No cancelable» porque "
                + (f"la factura {listado} la relaciona" if uno
                   else f"las facturas {listado} la relacionan")
                + ". Envíala con motivo 01 indicando "
                + ("esa factura" if uno else "una de esas facturas")
                + " como sustituta: al recibir la solicitud el SAT rompe la "
                + "relación y la vuelve cancelable."
            )
        else:
            motivo = (
                "El SAT reporta esta factura como «No cancelable», normalmente porque "
                "otro comprobante la relaciona (un complemento de pago o una nota de "
                "crédito). Envíala con motivo 01 indicando el CFDI que la sustituye: "
                "al recibir la solicitud el SAT rompe la relación y la vuelve "
                "cancelable."
            )
        resultado.update(advertencia=motivo)

    return resultado


def _archivar_acuse_cancelacion(db: Session, doc) -> None:
    """
    Descarga y archiva el acuse sellado por el SAT justo después de solicitar la
    cancelación. Es la prueba fechada y firmada de que el trámite se presentó.

    Best-effort: el PAC puede tardar en publicarlo, así que un fallo aquí no
    interrumpe la cancelación (el acuse se puede bajar después bajo demanda).
    """
    from app.services import cancelacion_intento_service as bitacora_svc

    try:
        from app.services import acuse_cancelacion_service as acuse_svc

        acuse_svc.descargar_acuse_xml(doc, forzar=True)
        uuid = (getattr(doc, "cfdi_uuid", None) or getattr(doc, "uuid", None) or "").strip()
        ruta = f"acuses/{uuid}.xml" if uuid else None
        if ruta and hasattr(doc, "cancelacion_acuse_path"):
            doc.cancelacion_acuse_path = ruta
            db.add(doc)
        bitacora_svc.anotar_acuse(db, doc, path=ruta)
    except Exception as exc:  # noqa: BLE001
        # La ausencia del acuse se registra igual que su presencia: es el hecho
        # fechado que desmiente al PAC cuando afirma tener uno (caso A-2202).
        bitacora_svc.anotar_acuse(db, doc, error=str(exc))
        logger.info(
            "Acuse de cancelación aún no disponible en el PAC (%s); se podrá "
            "descargar más tarde.", exc,
        )


def solicitar_cancelacion_cfdi(
    db: Session, factura_id: UUID, motivo: str, folio_sustitucion: Optional[str] = None
) -> dict:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    # Se permite reintentar desde EN_CANCELACION: si la solicitud anterior nunca
    # llegó a registrarse en el SAT, esta es la única forma de destrabar la
    # factura. Si sí hay una solicitud viva, el PAC responde "solicitud previa"
    # y el flujo la deja EN_CANCELACION igual que antes.
    if factura.estatus not in ("TIMBRADA", "EN_CANCELACION"):
        raise HTTPException(
            status_code=400,
            detail="Solo se puede cancelar una factura TIMBRADA o en proceso de cancelación",
        )
    if not factura.cfdi_uuid:
        raise HTTPException(
            status_code=400, detail="La factura no tiene un UUID fiscal para cancelar."
        )

    # Antes de gastar consultas al SAT: que no haya otra cancelación de esta
    # misma factura en curso. Dos solicitudes simultáneas son lo que fabrica la
    # "solicitud previa" fantasma con la que el PAC luego se niega a reenviar.
    from app.services import cancelacion_intento_service as bitacora_svc

    bitacora_svc.tomar_candado(db, factura)

    # Sólo se detiene el trámite cuando ya está cancelada en el SAT. Un
    # "No cancelable" se registra y se envía igual: el procedimiento oficial es
    # emitir la sustituta y luego cancelar, y es el SAT quien resuelve.
    diag = diagnostico_cancelacion(db, factura)
    if not diag["puede_cancelar"]:
        raise HTTPException(status_code=400, detail=diag["motivo"])

    # Un CFDI "No cancelable" lo está por una de dos razones, y cada una necesita
    # lo contrario que la otra. Como el complemento de pago está obligado a
    # declarar qué factura paga, siempre sabemos cuál de las dos es:
    #
    #   · Lo traba un COMPLEMENTO DE PAGO → hay que cancelar primero el
    #     complemento. El motivo 01 no ayuda: la regla del SAT es liberar antes
    #     los documentos relacionados.
    #   · Lo traba una FACTURA SUSTITUTA → el motivo 01 con el UUID de esa
    #     sustituta es justo lo que hace que el SAT rompa la relación
    #     (comprobado con A-2202, A-390 y A-786).
    #
    # Antes se exigía motivo 01 en los dos casos, y a las trabadas por un
    # complemento se les mandaba por el camino que no lleva a ningún lado: A-783
    # y A-787, detenidas por P-299, recibieron ese consejo equivocado.
    if diag.get("advertencia"):
        if diag.get("complementos"):
            # diag["advertencia"] ya nombra los complementos que estorban.
            raise HTTPException(status_code=400, detail=diag["advertencia"])
        if (motivo or "").strip() != "01":
            raise HTTPException(
                status_code=400,
                detail=(
                    "El SAT reporta esta factura como «No cancelable». Para cancelarla "
                    "hay que enviarla con motivo 01 indicando el CFDI que la sustituye; "
                    "así el SAT rompe la relación y la vuelve cancelable."
                ),
            )

    if (motivo or "").strip() == "01":
        _validar_sustitucion_motivo_01(db, factura, folio_sustitucion)

    try:
        out = _pac.solicitar_cancelacion_cfdi(
            db=db,
            factura_id=factura_id,
            motivo=motivo,
            folio_sustitucion=folio_sustitucion,
        )
        _archivar_acuse_cancelacion(db, factura)
        # El aviso tiene que decir la verdad: antes anunciaba "Factura cancelada"
        # aunque el trámite hubiera quedado en proceso —o aunque el SAT no
        # hubiera registrado nada—, que es justo la falsa confianza que el resto
        # del flujo combate. Mismo criterio que en pago_service.
        confirmada = (factura.estatus or "").upper() == "CANCELADA"
        sat_sin_registro = out.get("sat_registro_solicitud") is False
        # El PAC bloqueó el reenvío alegando una solicitud previa que el SAT no
        # tiene. Reintentar por aquí no avanza, así que el aviso debe decirlo.
        pac_bloqueo = out.get("code") == "PAC-PREVIA" and sat_sin_registro
        try:
            if confirmada:
                titulo = "Factura cancelada"
                mensaje = f"Factura {factura.serie}-{factura.folio} cancelada ante el SAT."
            elif pac_bloqueo:
                titulo = "El PAC no reenvió la cancelación"
                mensaje = (
                    f"Factura {factura.serie}-{factura.folio}: el PAC se niega a "
                    "reenviar la solicitud porque cree tener una previa, y el SAT no "
                    "tiene ninguna registrada. Reintentar desde el sistema no va a "
                    "avanzar: hay que hacer el trámite en el portal del SAT."
                )
            elif sat_sin_registro:
                # NO es una falla todavía. El 20-ago-2026 este aviso se disparó en
                # tres cancelaciones que sí habían entrado y que el SAT reflejó ~16
                # minutos después: las tres alarmas fueron falsas. Quien sí puede
                # afirmar que el trámite se perdió es el cron, cuando vence el margen
                # de gracia y revierte a TIMBRADA (ver notificacion_cancelacion_service).
                titulo = "Cancelación enviada, falta que el SAT la refleje"
                mensaje = (
                    f"Factura {factura.serie}-{factura.folio}: el PAC acusó recibo y "
                    "el SAT todavía no la muestra, cosa normal en los primeros "
                    "minutos. El sistema la vigila y avisa si de verdad no prosperó."
                )
            else:
                titulo = "Cancelación en proceso"
                mensaje = (
                    f"Factura {factura.serie}-{factura.folio}: solicitud enviada al "
                    "SAT. Falta la resolución (puede requerir la aceptación del "
                    "receptor)."
                )
            notif_svc.crear_notificacion(
                db=db,
                empresa_id=factura.empresa_id,
                # ERROR sólo cuando ya se sabe que el trámite no va a avanzar.
                # En el resto, al enviar todavía no hay nada que reportar como
                # error: eso lo levanta el cron si vence el margen de gracia.
                tipo=notif_svc.ERROR if pac_bloqueo else notif_svc.ADVERTENCIA,
                titulo=titulo,
                mensaje=mensaje,
                metadata={"factura_id": str(factura_id), "motivo": motivo},
            )
        except Exception:
            pass
        return out
    except HTTPException:
        # Ya viene con su código y su explicación (p. ej. el 409 del candado de
        # envío en vuelo). Sin esto, el `except Exception` de abajo la convertía
        # en un 500 genérico y se perdía el motivo real.
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        code, detalle = interpretar_error_pac(e)
        raise HTTPException(status_code=code, detail=detalle)
    except Exception as e:
        logger.exception("Error de servicio al cancelar factura %s", factura_id)
        raise HTTPException(
            status_code=500, detail=f"Error inesperado al solicitar cancelación: {e}"
        )


# ────────────────────────────────────────────────────────────────
# Generación de Archivos


def registrar_cancelacion_portal(
    db: Session,
    doc,
    *,
    motivo: Optional[str] = None,
    folio_sustitucion: Optional[str] = None,
    acuse_xml: Optional[bytes] = None,
) -> dict:
    """
    Deja constancia de una cancelación tramitada directamente en el portal del SAT.

    Es el fallback operativo cuando el PAC acusa recibo sin transmitir la
    solicitud (caso A-2202). Hasta ahora terminaba en un UPDATE a mano sobre la
    base, sin bitácora ni acuse archivado.

    No se cree lo que diga el usuario: el estatus se toma de lo que el SAT
    reporta en el momento de registrar. Si el SAT no ve ni cancelación ni
    solicitud en proceso, no hay nada que registrar.
    """
    from app.models.cancelacion_intento import PORTAL_SAT
    from app.services import cancelacion_intento_service as bitacora_svc
    from app.services import sat_cfdi_service as sat_svc

    uuid_cfdi = (
        getattr(doc, "cfdi_uuid", None) or getattr(doc, "uuid", None) or ""
    ).strip()
    if not uuid_cfdi:
        raise HTTPException(status_code=400, detail="El comprobante no tiene UUID fiscal.")

    try:
        rfc_emisor, rfc_receptor, total = sat_svc.datos_consulta(doc)
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_emisor, rfc_receptor=rfc_receptor,
            total=total, uuid=uuid_cfdi,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo consultar el SAT para confirmar el trámite: {exc}",
        )

    if not acuse.encontrado:
        raise HTTPException(
            status_code=404,
            detail=f"El SAT no reconoce este CFDI ({acuse.codigo_estatus}).",
        )
    if not (acuse.cancelado_por_sat or acuse.en_proceso):
        raise HTTPException(
            status_code=400,
            detail=(
                "El SAT no tiene registrada ninguna cancelación para este "
                f"comprobante (Estado={acuse.estado}, "
                f"EstatusCancelacion={acuse.estatus_cancelacion or 'vacío'}). "
                "Verifica que la solicitud en el portal se haya completado."
            ),
        )

    es_factura = isinstance(doc, Factura)
    if acuse.cancelado_por_sat:
        nuevo_estatus = "CANCELADA" if es_factura else "CANCELADO"
    else:
        nuevo_estatus = "EN_CANCELACION"

    # El acuse sellado que el portal entrega es la prueba del trámite; el PAC no
    # lo tiene, porque la solicitud no pasó por él.
    ruta_acuse = None
    if acuse_xml:
        from app.config import settings

        destino = os.path.join(settings.DATA_DIR, "acuses")
        os.makedirs(destino, exist_ok=True)
        ruta_abs = os.path.join(destino, f"{uuid_cfdi}.portal.xml")
        with open(ruta_abs, "wb") as fh:
            fh.write(acuse_xml)
        ruta_acuse = f"acuses/{uuid_cfdi}.portal.xml"

    estatus_anterior = getattr(doc.estatus, "value", doc.estatus)
    if es_factura:
        doc.estatus = nuevo_estatus
    else:
        from app.models.pago import EstatusPago

        doc.estatus = EstatusPago(nuevo_estatus)

    if motivo:
        doc.motivo_cancelacion = motivo
    if (folio_sustitucion or "").strip():
        doc.folio_fiscal_sustituto = folio_sustitucion.strip()
    doc.cancelacion_code = CODIGO_SAT_PORTAL
    doc.cancelacion_message = (
        "Cancelación tramitada directamente en el portal del SAT. "
        f"El SAT reporta Estado={acuse.estado}, "
        f"EstatusCancelacion={acuse.estatus_cancelacion or 'vacío'}."
    )
    if ruta_acuse:
        doc.cancelacion_acuse_path = ruta_acuse
    doc.fecha_solicitud_cancelacion = (
        None if acuse.cancelado_por_sat else datetime.utcnow()
    )
    db.add(doc)

    bitacora_svc.registrar(
        db, doc,
        motivo=motivo or getattr(doc, "motivo_cancelacion", None),
        folio_sustitucion=folio_sustitucion,
        pac_code=CODIGO_SAT_PORTAL,
        pac_message="Trámite hecho en el portal del SAT (no pasó por el PAC).",
        pac_codigo_conocido=None,
        acuse_sat=acuse,
        sat_registro_solicitud=True,  # el SAT lo confirma, por eso llegamos aquí
        origen=PORTAL_SAT,
    )
    if ruta_acuse:
        bitacora_svc.anotar_acuse(db, doc, path=ruta_acuse)
    if nuevo_estatus != "EN_CANCELACION":
        bitacora_svc.cerrar_si_resuelto(db, doc, "EN_CANCELACION", nuevo_estatus)

    db.commit()
    db.refresh(doc)

    return {
        "estatus_anterior": estatus_anterior,
        "estatus_nuevo": nuevo_estatus,
        "sat_estado": acuse.estado,
        "sat_estatus_cancelacion": acuse.estatus_cancelacion,
        "acuse_guardado": bool(ruta_acuse),
    }


def generar_xml_preview_bytes(db: Session, factura_id: UUID) -> bytes:
    try:
        return build_cfdi40_xml_sin_timbrar(db, factura_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e) or "Factura no encontrada")
    except Exception as e:
        logger.exception("Error de servicio al generar XML preview para %s", factura_id)
        raise HTTPException(
            status_code=500, detail=f"Error interno al generar XML: {e}"
        )


def generar_pdf_bytes(db: Session, factura_id: UUID, preview: bool) -> bytes:
    factura = load_factura_full(db, factura_id)
    if not factura:
        raise HTTPException(
            status_code=404, detail="Factura no encontrada para generar PDF"
        )
    if not preview and factura.estatus == "BORRADOR":
        raise HTTPException(
            status_code=409, detail="Debe estar TIMBRADA o CANCELADA para PDF final"
        )
    try:
        return render_factura_pdf_bytes_from_model(
            db, factura_id, preview=preview, logo_path=None
        )
    except Exception as e:
        logger.exception("Error de servicio al generar PDF para %s", factura_id)
        raise HTTPException(
            status_code=500, detail=f"Error interno al generar PDF: {e}"
        )


def obtener_ruta_xml_timbrado(db: Session, factura_id: UUID) -> Tuple[str, str, str]:
    factura = (
        db.query(Factura)
        .options(selectinload(Factura.empresa))
        .filter(Factura.id == factura_id)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if factura.estatus != "TIMBRADA":
        raise HTTPException(
            status_code=409,
            detail="La factura debe estar TIMBRADA para descargar el XML",
        )
    if not factura.xml_path:
        raise HTTPException(
            status_code=404, detail="No hay ruta de XML registrada para esta factura"
        )

    emisor_rfc = (getattr(factura.empresa, "rfc", "") or "EMISOR").upper()
    filename = (
        f"{emisor_rfc}-{factura.serie}-{factura.folio}.xml"
        if factura.serie and factura.folio
        else f"{emisor_rfc}-{factura.id}.xml"
    )

    return factura.xml_path, filename


# ────────────────────────────────────────────────────────────────
# Otras Acciones


def marcar_pago_factura(
    db: Session,
    factura_id: UUID,
    status: Literal["PAGADA", "NO_PAGADA"],
    fecha_pago: Optional[date] = None,
    fecha_cobro: Optional[date] = None,
) -> Factura:
    factura = (
        db.query(Factura)
        .options(selectinload(Factura.conceptos))
        .filter(Factura.id == factura_id)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if status == "PAGADA" and not fecha_cobro:
        raise HTTPException(
            status_code=422, detail="Para marcar PAGADA, envía fecha_cobro"
        )

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


# Filtros de cancelación para el listado. No son estatus: son preguntas sobre el
# trámite, que es otra cosa. Una factura puede acumular tres solicitudes
# fallidas y seguir TIMBRADA —hoy eso no se ve por ningún lado, y es justo el
# caso que hay que atender.
FILTROS_CANCELACION = (
    "con_solicitud",     # alguna vez se intentó cancelar, sin importar cómo acabó
    "atorada",           # se pidió cancelar y la factura sigue vigente
    "en_tramite",        # esperando al SAT o al receptor
    "sin_registro_sat",  # el PAC acusó recibo y el SAT no tenía la solicitud
    "cancelada",         # el trámite llegó a su fin
)


def _existe_intento(extra=None):
    """
    EXISTS de una solicitud de cancelación para la factura de la consulta.

    EXISTS y no un join: una factura con varios intentos saldría repetida en el
    listado, y aquí interesa la factura, no cada solicitud.
    """
    from app.models.cancelacion_intento import FACTURA as DOC_FACTURA
    from app.models.cancelacion_intento import CancelacionIntento

    condicion = (CancelacionIntento.documento_id == Factura.id) & (
        CancelacionIntento.documento_tipo == DOC_FACTURA
    )
    if extra is not None:
        condicion = condicion & extra
    return exists().where(condicion)


def _filtrar_por_cancelacion(q, filtro: str):
    """Acota el listado por el estado del TRÁMITE, no del documento."""
    from app.models.cancelacion_intento import CancelacionIntento

    if filtro == "atorada":
        # El conjunto que no se ve en ninguna pantalla: se pidió la cancelación
        # y el comprobante sigue vigente ante el SAT. A-785 y A-22069 vivieron
        # días así sin que nadie lo notara.
        return q.filter(Factura.estatus == "TIMBRADA", _existe_intento())
    if filtro == "en_tramite":
        return q.filter(Factura.estatus == "EN_CANCELACION")
    if filtro == "cancelada":
        return q.filter(Factura.estatus == "CANCELADA", _existe_intento())
    if filtro == "sin_registro_sat":
        # El caso A-2202: el PAC contestó que sí y el SAT no sabía nada. Sólo
        # interesa mientras no se resuelva; una vez cancelada, da igual cómo
        # llegó ahí.
        return q.filter(
            Factura.estatus != "CANCELADA",
            _existe_intento(CancelacionIntento.sat_registro_solicitud.is_(False)),
        )
    return q.filter(_existe_intento())


def listar_facturas(
    db: Session,
    *,
    empresa_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    serie: Optional[str] = None,
    folio: Optional[int] = None,
    folio_min: Optional[int] = None,
    folio_max: Optional[int] = None,
    estatus: Optional[str] = None,
    status_pago: Optional[str] = None,
    cancelacion: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    order_by: str = "serie_folio",
    order_dir: str = "asc",
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Factura], int]:
    q = db.query(Factura).options(
        selectinload(Factura.conceptos), selectinload(Factura.cliente)
    )

    if empresa_id:
        q = q.filter(Factura.empresa_id == empresa_id)
    if cliente_id:
        q = q.filter(Factura.cliente_id == cliente_id)
    if serie:
        q = q.filter(Factura.serie == serie.upper())
    if folio is not None:
        q = q.filter(Factura.folio == folio)
    if folio_min is not None:
        q = q.filter(Factura.folio >= folio_min)
    if folio_max is not None:
        q = q.filter(Factura.folio <= folio_max)
    if estatus:
        q = q.filter(Factura.estatus == estatus.upper())
    if status_pago:
        q = q.filter(Factura.status_pago == status_pago.upper())
    if cancelacion:
        q = _filtrar_por_cancelacion(q, cancelacion)
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
