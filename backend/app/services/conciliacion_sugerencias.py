# app/services/conciliacion_sugerencias.py
"""Candidatas para cada movimiento del estado de cuenta.

El sistema no concilia solo: propone y la persona decide. Medido sobre junio
2026, de 202 depósitos sólo el 24% trae el folio escrito en el concepto y otro
10% lo identifica un monto único; el 47% coincide en monto con varias facturas
—ahí lo útil es poner las candidatas enfrente— y el 19% restante no cuadra con
nada, porque es un pago parcial, lo pagó un tercero o no está facturado.

Por eso cada sugerencia viene con su origen y su confianza: no es lo mismo un
folio escrito por el propio cliente que una coincidencia de monto entre cinco.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.models.conciliacion import ConciliacionBancaria, MovimientoBancario
from app.models.egreso import Egreso
from app.models.factura import Factura

# Folios que la gente escribe en la transferencia: "FACTURA 1412", "FT A1585",
# "Payo f1567", "FUMIGACION F1561". Se captura el número; la letra es la serie.
_REF_FOLIO = re.compile(
    r"\b(?:FACTURA|FACT|FACT\.|FT|F|PAGO|PAYO|REC|REF)\s*[-#:]?\s*([A-Z]?)(\d{3,5})\b",
    re.I,
)
# Números sueltos de 3 a 5 dígitos que pueden ser un folio sin etiqueta
_NUM_SUELTO = re.compile(r"\b(\d{3,5})\b")

# Ventana alrededor de la fecha del movimiento para buscar por monto. El cobro
# no cae el mismo día que se factura ni que se registra el gasto.
DIAS_ANTES, DIAS_DESPUES = 75, 20

# Cuántas candidatas por monto vale la pena mostrar. Si hay más, la coincidencia
# no distingue nada y conviene que busque a mano.
MAX_POR_MONTO = 6


def _folios_del_concepto(texto: str) -> set[int]:
    """Números que en ese texto parecen un folio de factura."""
    folios = {int(n) for _, n in _REF_FOLIO.findall(texto or "")}
    # Los sueltos sólo cuentan si el concepto menciona factura o pago; si no,
    # cualquier referencia bancaria de 4 dígitos entraría como folio.
    if folios or re.search(r"FACTURA|FACT|PAGO|PAYO|FUMIGACION", texto or "", re.I):
        folios |= {int(n) for n in _NUM_SUELTO.findall(texto or "")}
    # Las referencias bancarias largas ya se descartaron por el límite de dígitos
    return {f for f in folios if 1 <= f <= 99999}


def _factura_dict(f: Factura, origen: str, confianza: str) -> dict:
    return {
        "tipo": "factura",
        "id": str(f.id),
        "folio": f"{f.serie}-{f.folio}",
        "total": f.total,
        "fecha": f.fecha_emision.date() if hasattr(f.fecha_emision, "date") else f.fecha_emision,
        "descripcion": f.cliente.nombre_comercial if f.cliente else None,
        "empresa": f.empresa.nombre_comercial if f.empresa else None,
        "origen": origen,
        "confianza": confianza,
    }


def _egreso_dict(e: Egreso, origen: str, confianza: str) -> dict:
    return {
        "tipo": "egreso",
        "id": str(e.id),
        "folio": e.proveedor or "(sin proveedor)",
        "total": e.monto,
        "fecha": e.fecha_egreso,
        "descripcion": e.descripcion,
        "empresa": e.empresa.nombre_comercial if getattr(e, "empresa", None) else None,
        "origen": origen,
        "confianza": confianza,
    }


def calcular(db: Session, conciliacion_id: UUID, empresas: List[UUID]) -> Dict[str, List[dict]]:
    """Candidatas por movimiento. Devuelve {movimiento_id: [candidata, ...]}."""
    conc = (
        db.query(ConciliacionBancaria)
        .options(selectinload(ConciliacionBancaria.movimientos)
                 .selectinload(MovimientoBancario.facturas))
        .filter(ConciliacionBancaria.id == conciliacion_id)
        .first()
    )
    if not conc:
        return {}

    desde = conc.periodo_inicio - timedelta(days=DIAS_ANTES)
    hasta = conc.periodo_fin + timedelta(days=DIAS_DESPUES)

    # Se traen una vez y se indexan en memoria: son cientos de movimientos y
    # consultar por cada uno haría la pantalla inservible.
    facturas = (
        db.query(Factura)
        .options(selectinload(Factura.cliente), selectinload(Factura.empresa))
        .filter(
            Factura.empresa_id.in_(empresas),
            Factura.estatus.notin_(["BORRADOR", "CANCELADA"]),
            Factura.fecha_emision >= desde,
            Factura.fecha_emision <= hasta,
        )
        .all()
    )
    egresos = (
        db.query(Egreso)
        .options(selectinload(Egreso.empresa))
        .filter(
            Egreso.empresa_id.in_(empresas),
            Egreso.fecha_egreso >= desde,
            Egreso.fecha_egreso <= hasta,
        )
        .all()
    )

    por_folio: Dict[int, List[Factura]] = defaultdict(list)
    fact_por_monto: Dict[Decimal, List[Factura]] = defaultdict(list)
    for f in facturas:
        if f.folio:
            por_folio[int(f.folio)].append(f)
        fact_por_monto[Decimal(f.total).quantize(Decimal("0.01"))].append(f)

    egr_por_monto: Dict[Decimal, List[Egreso]] = defaultdict(list)
    for e in egresos:
        egr_por_monto[Decimal(e.monto).quantize(Decimal("0.01"))].append(e)

    sugerencias: Dict[str, List[dict]] = {}
    for m in conc.movimientos:
        if m.facturas or m.conciliado:
            continue   # ya resuelto, no estorbar

        candidatas: List[dict] = []
        vistos: set[str] = set()

        if m.deposito is not None:
            monto = Decimal(m.deposito).quantize(Decimal("0.01"))

            # 1. El folio viene escrito en el concepto: es lo más confiable
            for folio in sorted(_folios_del_concepto(m.concepto)):
                for f in por_folio.get(folio, []):
                    if str(f.id) in vistos:
                        continue
                    vistos.add(str(f.id))
                    cuadra = Decimal(f.total).quantize(Decimal("0.01")) == monto
                    candidatas.append(_factura_dict(
                        f, f"folio {folio} en el concepto",
                        "alta" if cuadra else "media"))

            # 2. Por monto exacto
            mismas = [f for f in fact_por_monto.get(monto, []) if str(f.id) not in vistos]
            if mismas and len(mismas) <= MAX_POR_MONTO:
                for f in mismas:
                    vistos.add(str(f.id))
                    candidatas.append(_factura_dict(
                        f, "mismo importe", "alta" if len(mismas) == 1 else "baja"))

        elif m.retiro is not None:
            monto = Decimal(m.retiro).quantize(Decimal("0.01"))
            mismos = egr_por_monto.get(monto, [])
            if mismos and len(mismos) <= MAX_POR_MONTO:
                for e in mismos:
                    candidatas.append(_egreso_dict(
                        e, "mismo importe", "alta" if len(mismos) == 1 else "baja"))

        if candidatas:
            # Primero lo más confiable, y dentro de eso lo más cercano en fecha
            orden = {"alta": 0, "media": 1, "baja": 2}
            candidatas.sort(key=lambda c: (
                orden.get(c["confianza"], 3),
                abs((c["fecha"] - m.fecha).days) if c["fecha"] else 999,
            ))
            sugerencias[str(m.id)] = candidatas[:8]

    return sugerencias
