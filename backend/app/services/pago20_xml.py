# app/services/pago20_xml.py
from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from decimal import Decimal

from app.models.pago import Pago, PagoDocumentoRelacionado
from app.services.cfdi40_xml import (
    _build_cadena_original_40,
    _load_csd_key_for_empresa,
    _sign_cadena_sha256_pkcs1v15,
    _load_csd_cert_for_empresa,
    _fmt_cfdi_fecha_local,
    money2,
    tasa6,
)


def build_pago20_xml_sin_timbrar(db: Session, pago_id: UUID) -> bytes:
    pago = (
        db.query(Pago)
        .options(
            selectinload(Pago.empresa),
            selectinload(Pago.cliente),
            selectinload(Pago.documentos_relacionados).selectinload(
                PagoDocumentoRelacionado.factura
            ),
        )
        .filter(Pago.id == pago_id)
        .first()
    )

    if not pago:
        raise ValueError("Pago no encontrado")

    empresa = pago.empresa
    cliente = pago.cliente

    NS_CFDI = "http://www.sat.gob.mx/cfd/4"
    NS_PAGO20 = "http://www.sat.gob.mx/Pagos20"
    NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
    register_namespace("cfdi", NS_CFDI)
    register_namespace("pago20", NS_PAGO20)

    # --- START: Calculate Totals ---
    monto_total_pagos = sum(dr.imp_pagado for dr in pago.documentos_relacionados)

    total_retenciones_isr = Decimal("0.0")
    total_retenciones_iva = Decimal("0.0")
    total_traslados_base_iva16 = Decimal("0.0")
    total_traslados_impuesto_iva16 = Decimal("0.0")
    # IVA 8% (frontera)
    total_traslados_base_iva8 = Decimal("0.0")
    total_traslados_impuesto_iva8 = Decimal("0.0")

    for dr in pago.documentos_relacionados:
        if not dr.impuestos_dr:
            continue

        for ret in dr.impuestos_dr.get("retenciones_dr", []):
            if ret["impuesto_dr"] == "001":  # ISR
                total_retenciones_isr += Decimal(ret["importe_dr"])
            elif ret["impuesto_dr"] == "002":  # IVA
                total_retenciones_iva += Decimal(ret["importe_dr"])

        for tras in dr.impuestos_dr.get("traslados_dr", []):
            if tras["impuesto_dr"] == "002":  # IVA
                # Evitar problemas de precisión si viene float: convertir con str y cuantizar a 6 decimales
                tasa = Decimal(str(tras["tasa_o_cuota_dr"]))
                tasa = tasa.quantize(Decimal("0.000001"))
                if tasa == Decimal("0.160000"):
                    total_traslados_base_iva16 += Decimal(tras["base_dr"])
                    total_traslados_impuesto_iva16 += Decimal(tras["importe_dr"])
                elif tasa == Decimal("0.080000"):
                    total_traslados_base_iva8 += Decimal(tras["base_dr"])
                    total_traslados_impuesto_iva8 += Decimal(tras["importe_dr"])
    # --- END: Calculate Totals ---

    comprobante_attrs = {
        "xmlns:cfdi": NS_CFDI,
        "xmlns:pago20": NS_PAGO20,
        "xmlns:xsi": NS_XSI,
        "xsi:schemaLocation": "http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd http://www.sat.gob.mx/Pagos20 http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos20.xsd",
        "Version": "4.0",
        "Serie": pago.serie or "P",
        "Folio": pago.folio or "1",
        "Fecha": _fmt_cfdi_fecha_local(pago.fecha_emision),
        "SubTotal": "0",
        "Moneda": "XXX",
        "Total": "0",
        "TipoDeComprobante": "P",
        "Exportacion": "01",
        "LugarExpedicion": (str(empresa.codigo_postal or "").strip()[:5]).zfill(5),
    }

    comprobante = Element("cfdi:Comprobante", comprobante_attrs)

    no_cert, cert_b64, _ = _load_csd_cert_for_empresa(empresa)
    if no_cert:
        comprobante.set("NoCertificado", no_cert)
    if cert_b64:
        comprobante.set("Certificado", cert_b64)

    SubElement(
        comprobante,
        "cfdi:Emisor",
        {
            "Rfc": empresa.rfc,
            "Nombre": empresa.nombre,
            "RegimenFiscal": empresa.regimen_fiscal,
        },
    )

    SubElement(
        comprobante,
        "cfdi:Receptor",
        {
            "Rfc": cliente.rfc,
            "Nombre": cliente.nombre_razon_social,
            "DomicilioFiscalReceptor": (str(cliente.codigo_postal or "").strip()[:5]).zfill(5),
            "RegimenFiscalReceptor": cliente.regimen_fiscal,
            "UsoCFDI": "CP01",
        },
    )

    conceptos = SubElement(comprobante, "cfdi:Conceptos")
    SubElement(
        conceptos,
        "cfdi:Concepto",
        {
            "ClaveProdServ": "84111506",
            "Cantidad": "1",
            "ClaveUnidad": "ACT",
            "Descripcion": "Pago",
            "ValorUnitario": "0",
            "Importe": "0",
            "ObjetoImp": "01",
        },
    )

    complemento = SubElement(comprobante, "cfdi:Complemento")
    pagos_node = SubElement(complemento, "pago20:Pagos", {"Version": "2.0"})

    totales_attrs = {
        "MontoTotalPagos": money2(monto_total_pagos),
    }
    if total_retenciones_isr > 0:
        totales_attrs["TotalRetencionesISR"] = money2(total_retenciones_isr)
    if total_retenciones_iva > 0:
        totales_attrs["TotalRetencionesIVA"] = money2(total_retenciones_iva)
    if total_traslados_impuesto_iva16 > 0:
        totales_attrs["TotalTrasladosBaseIVA16"] = money2(total_traslados_base_iva16)
        totales_attrs["TotalTrasladosImpuestoIVA16"] = money2(
            total_traslados_impuesto_iva16
        )
    if total_traslados_impuesto_iva8 > 0:
        totales_attrs["TotalTrasladosBaseIVA8"] = money2(total_traslados_base_iva8)
        totales_attrs["TotalTrasladosImpuestoIVA8"] = money2(
            total_traslados_impuesto_iva8
        )

    SubElement(pagos_node, "pago20:Totales", totales_attrs)

    # Normalizar FormaDePagoP a 2 dígitos (e.g., '3' -> '03') por requisitos del SAT
    forma_pago_p_norm = (
        f"{int(pago.forma_pago_p):02d}" if pago.forma_pago_p and pago.forma_pago_p.isdigit() else pago.forma_pago_p
    )

    pago_node = SubElement(
        pagos_node,
        "pago20:Pago",
        {
            "FechaPago": _fmt_cfdi_fecha_local(pago.fecha_pago),
            "FormaDePagoP": forma_pago_p_norm,
            "MonedaP": pago.moneda_p,
            "Monto": money2(pago.monto),
            "TipoCambioP": str(pago.tipo_cambio_p) if pago.moneda_p != "MXN" else "1",
        },
    )

    # (ImpuestosP se insertará más adelante, después de DoctoRelacionado, para cumplir con el orden del XSD)

    for doc in pago.documentos_relacionados:
        docto_rel_attrs = {
            "IdDocumento": doc.id_documento,
            "MonedaDR": doc.moneda_dr,
            "NumParcialidad": str(doc.num_parcialidad),
            "ImpSaldoAnt": money2(doc.imp_saldo_ant),
            "ImpPagado": money2(doc.imp_pagado),
            "ImpSaldoInsoluto": money2(doc.imp_saldo_insoluto),
            "ObjetoImpDR": "02",  # Asumiendo que es objeto de impuesto
        }
        # EquivalenciaDR: reglas SAT
        # - Si MonedaDR == MonedaP → EquivalenciaDR = "1"
        # - Si MonedaDR != MonedaP → EquivalenciaDR es requerido y debe ser el tipo de cambio del documento
        if doc.moneda_dr == pago.moneda_p:
            docto_rel_attrs["EquivalenciaDR"] = "1"
        else:
            if doc.tipo_cambio_dr is None:
                raise RuntimeError(
                    "EquivalenciaDR requerido: cuando MonedaDR difiere de MonedaP, se debe especificar tipo_cambio_dr en el documento relacionado."
                )
            docto_rel_attrs["EquivalenciaDR"] = str(doc.tipo_cambio_dr)
        docto_relacionado_node = SubElement(
            pago_node, "pago20:DoctoRelacionado", docto_rel_attrs
        )

        if doc.impuestos_dr:
            impuestos_dr_node = SubElement(docto_relacionado_node, "pago20:ImpuestosDR")

            # --- START: TrasladosDR (Level: Document) ---
            if "traslados_dr" in doc.impuestos_dr and doc.impuestos_dr["traslados_dr"]:
                traslados_dr_node = SubElement(impuestos_dr_node, "pago20:TrasladosDR")
                for tras in doc.impuestos_dr["traslados_dr"]:
                    SubElement(
                        traslados_dr_node,
                        "pago20:TrasladoDR",
                        {
                            "BaseDR": money2(Decimal(tras["base_dr"])),
                            "ImpuestoDR": tras["impuesto_dr"],
                            "TipoFactorDR": tras["tipo_factor_dr"],
                            "TasaOCuotaDR": tasa6(Decimal(str(tras["tasa_o_cuota_dr"]))),
                            "ImporteDR": money2(Decimal(tras["importe_dr"])),
                        },
                    )
            # --- END: TrasladosDR ---

            if (
                "retenciones_dr" in doc.impuestos_dr
                and doc.impuestos_dr["retenciones_dr"]
            ):
                retenciones_dr_node = SubElement(
                    impuestos_dr_node, "pago20:RetencionesDR"
                )
                for ret in doc.impuestos_dr["retenciones_dr"]:
                    SubElement(
                        retenciones_dr_node,
                        "pago20:RetencionDR",
                        {
                            "BaseDR": money2(Decimal(ret["base_dr"])),
                            "ImpuestoDR": ret["impuesto_dr"],
                            "TipoFactorDR": ret["tipo_factor_dr"],
                            "TasaOCuotaDR": tasa6(Decimal(str(ret["tasa_o_cuota_dr"]))),
                            "ImporteDR": money2(Decimal(ret["importe_dr"])),
                        },
                    )

    # --- START: ImpuestosP (DESPUÉS de DoctoRelacionado, según XSD) ---
    has_impuestos_p = (
        total_retenciones_isr > 0
        or total_retenciones_iva > 0
        or total_traslados_impuesto_iva16 > 0
        or total_traslados_impuesto_iva8 > 0
    )
    if has_impuestos_p:
        impuestos_p_node = SubElement(pago_node, "pago20:ImpuestosP")

        if total_traslados_impuesto_iva16 > 0 or total_traslados_impuesto_iva8 > 0:
            traslados_p_node = SubElement(impuestos_p_node, "pago20:TrasladosP")
            if total_traslados_impuesto_iva16 > 0:
                SubElement(
                    traslados_p_node,
                    "pago20:TrasladoP",
                    {
                        "BaseP": money2(total_traslados_base_iva16),
                        "ImpuestoP": "002",  # IVA
                        "TipoFactorP": "Tasa",
                        "TasaOCuotaP": tasa6(Decimal("0.16")),
                        "ImporteP": money2(total_traslados_impuesto_iva16),
                    },
                )
            if total_traslados_impuesto_iva8 > 0:
                SubElement(
                    traslados_p_node,
                    "pago20:TrasladoP",
                    {
                        "BaseP": money2(total_traslados_base_iva8),
                        "ImpuestoP": "002",  # IVA
                        "TipoFactorP": "Tasa",
                        "TasaOCuotaP": tasa6(Decimal("0.08")),
                        "ImporteP": money2(total_traslados_impuesto_iva8),
                    },
                )

        if total_retenciones_isr > 0 or total_retenciones_iva > 0:
            retenciones_p_node = SubElement(impuestos_p_node, "pago20:RetencionesP")
            if total_retenciones_isr > 0:
                SubElement(
                    retenciones_p_node,
                    "pago20:RetencionP",
                    {
                        "ImpuestoP": "001",  # ISR
                        "ImporteP": money2(total_retenciones_isr),
                    },
                )
            if total_retenciones_iva > 0:
                SubElement(
                    retenciones_p_node,
                    "pago20:RetencionP",
                    {
                        "ImpuestoP": "002",  # IVA
                        "ImporteP": money2(total_retenciones_iva),
                    },
                )
    # --- END: ImpuestosP ---

    xml_sin_sello = tostring(comprobante, encoding="UTF-8", xml_declaration=False)

    cadena_original = _build_cadena_original_40(xml_sin_sello)
    if not cadena_original:
        raise RuntimeError(
            "No se pudo generar la Cadena Original 4.0 para el complemento de pago."
        )

    private_key = _load_csd_key_for_empresa(empresa)
    if not private_key:
        raise RuntimeError(
            "No se pudo cargar la llave privada del CSD para firmar el pago."
        )

    sello = _sign_cadena_sha256_pkcs1v15(cadena_original, private_key)
    if not sello:
        raise RuntimeError("No se pudo firmar la cadena original del pago.")

    comprobante.set("Sello", sello)

    xml_final = tostring(comprobante, encoding="UTF-8", xml_declaration=True)

    return xml_final
