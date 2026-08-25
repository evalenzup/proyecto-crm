# app/services/conciliacion_sugerencias.py
"""Candidatas para cada movimiento del estado de cuenta.

El sistema no concilia solo: propone y la persona decide. Medido sobre junio
2026, de 202 depósitos sólo el 24% trae el folio escrito en el concepto y otro
10% lo identifica un monto único; el 47% coincide en monto con varias facturas
y el 19% restante no cuadra con nada, porque es un pago parcial, lo pagó un
tercero o no está facturado.

Cada candidata se puntúa con varias señales en vez de una sola regla. La razón
está en un caso real: un depósito de $2,700 con el folio 1498 escrito en el
concepto salía junto a otras dos facturas del mismo importe, una de ellas de
una escuela que no tenía nada que ver. Con el folio y el monto coincidiendo, la
respuesta ya era segura y las otras dos sólo hacían dudar.

Señales, de más a menos concluyente:
  · el folio viene escrito en el concepto y el monto cuadra → es esa, sin más
  · un alias aprendido dice que ese ordenante paga por ese cliente
  · el nombre de quien paga se parece al del cliente
  · el importe coincide exacto
  · la factura es reciente respecto al depósito
Y se descuenta lo que estorba: facturas ya conciliadas en otro movimiento y
facturas viejas.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.models.conciliacion import (
    ConciliacionAlias, ConciliacionBancaria, MovimientoBancario, MovimientoFactura,
)
from app.models.egreso import Egreso
from app.models.factura import Factura

# ── Lectura del concepto ─────────────────────────────────────────────────────

_REF_FOLIO = re.compile(
    r"\b(?:FACTURA|FACT|FACT\.|FT|F|PAGO|PAYO|REC|REF)\s*[-#:]?\s*([A-Z]?)(\d{3,5})\b",
    re.I,
)
_NUM_SUELTO = re.compile(r"\b(\d{3,5})\b")

# Bancos e intermediarios: aparecen como emisores pero no son quien paga
_INTERMEDIARIOS = {
    "BBVA", "BBVA MEXICO", "SANTANDER", "BANORTE", "BAJIO", "BANBAJIO", "AFIRME",
    "BANREGIO", "HEY BANCO", "HEY", "STP", "MERCADO PAGO", "BANAMEX", "CITIBANAMEX",
    "SCOTIABANK", "INBURSA", "AZTECA", "BANCOPPEL", "INTERCAM", "MONEX", "MIFEL",
    "ACTINVER", "MULTIVA", "COMPARTAMOS", "NU", "NUBANK", "KLAR", "SPIN", "OXXO",
}
# Palabras que no distinguen a nadie
_VACIAS = {
    "DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "SA", "CV", "SC", "RL", "SAPI",
    "SAS", "SRL", "MX", "MEXICO", "S", "A", "C", "V", "R", "L", "P", "I",
    "CTA", "ORDENANTE", "REF", "RASTREO", "POR", "ORDEN", "PAGO", "RECIBIDO",
    "SU", "AL", "BENEF", "COM", "SDE",
}

_QUITAR_ORDENANTE = re.compile(
    r"\b(CTA\.?ORDENANTE|SU\s+REF|REF\.?\d|RASTREO|CLABE|\d{6,})\b", re.I)


def normalizar(texto: Optional[str]) -> str:
    """Mayúsculas, sin acentos y sin puntuación. Base de toda comparación."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9 ]+", " ", t).upper().strip()


def palabras_clave(texto: Optional[str]) -> Set[str]:
    """Palabras que sí identifican a alguien: sin razón social ni relleno.

    Los números cortos se conservan porque muchas veces son el nombre —"260
    GRADOS", "SECUNDARIA #50"— y descartarlos rompía justo las coincidencias
    que importan. Los largos se van: son referencias bancarias.
    """
    palabras = set()
    for p in normalizar(texto).split():
        if p in _VACIAS:
            continue
        if p.isdigit():
            if 2 <= len(p) <= 4:
                palabras.add(p)
        elif len(p) > 2:
            palabras.add(p)
    return palabras


def ordenante_del_concepto(concepto: str) -> str:
    """Quién envió el dinero, descartando al banco que lo transporta.

    "PAGO RECIBIDO DE SANTANDER POR ORDEN DE 260 GRADOS S DE RL DE CV
     CTA.ORDENANTE 014022..." → "260 GRADOS"
    """
    t = normalizar(concepto)

    m = re.search(r"POR ORDEN DE (.+?)(?:$|CTA|SU REF|REF |RASTREO|CLABE)", t)
    if not m:
        m = re.search(r"(?:PAGO |ABONO )?RECIBIDO DE (.+?)(?:$|CTA|SU REF|REF |RASTREO|POR ORDEN)", t)
    if not m:
        return ""

    nombre = _QUITAR_ORDENANTE.sub(" ", m.group(1)).strip()
    # Si lo que quedó es sólo el banco, no aporta
    if nombre in _INTERMEDIARIOS:
        return ""
    for banco in _INTERMEDIARIOS:
        if nombre.startswith(banco + " "):
            nombre = nombre[len(banco):].strip()
    return " ".join(nombre.split()[:8])


def clave_alias(concepto: str) -> str:
    """Llave estable para recordar a un ordenante."""
    return " ".join(sorted(palabras_clave(ordenante_del_concepto(concepto))))[:200]


def _folios_del_concepto(texto: str) -> Set[int]:
    folios = {int(n) for _, n in _REF_FOLIO.findall(texto or "")}
    if folios or re.search(r"FACTURA|FACT|PAGO|PAYO|FUMIGACION", texto or "", re.I):
        folios |= {int(n) for n in _NUM_SUELTO.findall(texto or "")}
    return {f for f in folios if 1 <= f <= 99999}


# ── Puntajes ─────────────────────────────────────────────────────────────────

P_FOLIO = 50          # el folio viene escrito en el concepto
P_ALIAS = 40          # un alias aprendido apunta a ese cliente
P_MONTO = 30          # el importe coincide exacto
P_NOMBRE = 25         # el nombre de quien paga se parece al del cliente
P_YA_USADA = -100     # esa factura ya se concilió en otro movimiento

DIAS_ANTES, DIAS_DESPUES = 75, 20
MAX_POR_MONTO = 6
MAX_CANDIDATAS = 6


def _cercania(dias: int) -> float:
    """Premia lo reciente. Un depósito de junio suele pagar mayo, no febrero."""
    if dias < 0:
        return 2.0            # la factura es posterior al depósito: raro
    if dias <= 45:
        return 10.0 - (dias / 9)
    return max(0.0, 5.0 - (dias - 45) / 12)


def _confianza(puntos: float) -> str:
    if puntos >= 70:
        return "alta"
    if puntos >= 40:
        return "media"
    return "baja"


def calcular(db: Session, conciliacion_id: UUID, empresas: List[UUID]) -> Dict[str, List[dict]]:
    """Candidatas por movimiento: {movimiento_id: [candidata, ...]}."""
    conc = (
        db.query(ConciliacionBancaria)
        .options(selectinload(ConciliacionBancaria.movimientos)
                 .selectinload(MovimientoBancario.facturas),
                 selectinload(ConciliacionBancaria.movimientos)
                 .selectinload(MovimientoBancario.egresos))
        .filter(ConciliacionBancaria.id == conciliacion_id)
        .first()
    )
    if not conc:
        return {}

    desde = conc.periodo_inicio - timedelta(days=DIAS_ANTES)
    hasta = conc.periodo_fin + timedelta(days=DIAS_DESPUES)

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

    # Facturas ya enlazadas en cualquier conciliación: no deben competir de nuevo
    ya_usadas = {r[0] for r in db.query(MovimientoFactura.factura_id).all()}

    alias = defaultdict(set)
    for a in db.query(ConciliacionAlias).filter(
            ConciliacionAlias.empresa_id.in_(empresas)).all():
        alias[a.ordenante].add(a.cliente_id)

    por_folio: Dict[int, List[Factura]] = defaultdict(list)
    fact_por_monto: Dict[Decimal, List[Factura]] = defaultdict(list)
    palabras_cliente: Dict[UUID, Set[str]] = {}
    for f in facturas:
        if f.folio:
            por_folio[int(f.folio)].append(f)
        fact_por_monto[Decimal(f.total).quantize(Decimal("0.01"))].append(f)
        if f.cliente_id and f.cliente_id not in palabras_cliente:
            palabras_cliente[f.cliente_id] = palabras_clave(
                f.cliente.nombre_comercial if f.cliente else "")

    egr_por_monto: Dict[Decimal, List[Egreso]] = defaultdict(list)
    for e in egresos:
        egr_por_monto[Decimal(e.monto).quantize(Decimal("0.01"))].append(e)

    resultado: Dict[str, List[dict]] = {}

    for m in conc.movimientos:
        if m.facturas or m.egresos or m.conciliado:
            continue

        if m.deposito is not None:
            cands = _candidatas_deposito(
                m, por_folio, fact_por_monto, palabras_cliente, alias, ya_usadas)
        elif m.retiro is not None:
            cands = _candidatas_retiro(m, egr_por_monto)
        else:
            cands = []

        if cands:
            resultado[str(m.id)] = cands

    return resultado


def _fecha(f) -> Optional[object]:
    v = getattr(f, "fecha_emision", None)
    return v.date() if hasattr(v, "date") else v


def _candidatas_deposito(m, por_folio, fact_por_monto, palabras_cliente,
                         alias, ya_usadas) -> List[dict]:
    monto = Decimal(m.deposito).quantize(Decimal("0.01"))
    folios = _folios_del_concepto(m.concepto)
    pistas = palabras_clave(ordenante_del_concepto(m.concepto))
    clientes_alias = alias.get(clave_alias(m.concepto), set())

    marcadas: Dict[str, dict] = {}

    def evaluar(f: Factura, origenes: List[str], puntos: float):
        clave = str(f.id)
        if clave in marcadas and marcadas[clave]["puntos"] >= puntos:
            return
        if f.id in ya_usadas:
            puntos += P_YA_USADA
        fecha = _fecha(f)
        dias = (m.fecha - fecha).days if fecha else 999
        puntos += _cercania(dias)
        marcadas[clave] = {
            "tipo": "factura", "id": clave, "folio": f"{f.serie}-{f.folio}",
            "total": f.total, "fecha": fecha,
            "descripcion": f.cliente.nombre_comercial if f.cliente else None,
            "empresa": f.empresa.nombre_comercial if f.empresa else None,
            "origen": " + ".join(origenes), "puntos": puntos,
            "confianza": _confianza(puntos),
        }

    # 1. Folio escrito en el concepto
    for folio in sorted(folios):
        for f in por_folio.get(folio, []):
            cuadra = Decimal(f.total).quantize(Decimal("0.01")) == monto
            origenes = [f"folio {folio} en el concepto"]
            puntos = P_FOLIO
            if cuadra:
                origenes.append("importe exacto")
                puntos += P_MONTO
            evaluar(f, origenes, puntos)

            # Con el folio escrito Y el importe cuadrando ya no hay duda:
            # mostrar alternativas sólo hace dudar de una respuesta segura.
            if cuadra:
                return [_limpiar(marcadas[str(f.id)])]

    # 2. Mismo importe, afinado por alias y por nombre
    mismas = fact_por_monto.get(monto, [])
    if mismas and len(mismas) <= MAX_POR_MONTO:
        for f in mismas:
            origenes = ["importe exacto"]
            puntos = P_MONTO
            if f.cliente_id and f.cliente_id in clientes_alias:
                origenes.append("ya habías asignado a este cliente")
                puntos += P_ALIAS
            elif pistas and palabras_cliente.get(f.cliente_id):
                if pistas & palabras_cliente[f.cliente_id]:
                    origenes.append("coincide el nombre de quien paga")
                    puntos += P_NOMBRE
            evaluar(f, origenes, puntos)

    # 3. Sin importe coincidente, pero el alias sí sabe de quién es
    if not marcadas and clientes_alias:
        for f in [x for lista in fact_por_monto.values() for x in lista
                  if x.cliente_id in clientes_alias][:MAX_CANDIDATAS]:
            evaluar(f, ["ya habías asignado a este cliente"], P_ALIAS)

    salida = sorted(marcadas.values(), key=lambda c: -c["puntos"])[:MAX_CANDIDATAS]
    return [_limpiar(c) for c in salida]


def _candidatas_retiro(m, egr_por_monto) -> List[dict]:
    monto = Decimal(m.retiro).quantize(Decimal("0.01"))
    pistas = palabras_clave(m.concepto)
    mismos = egr_por_monto.get(monto, [])
    if not mismos or len(mismos) > MAX_POR_MONTO:
        return []

    cands = []
    for e in mismos:
        puntos = P_MONTO
        origenes = ["importe exacto"]
        texto = palabras_clave(f"{e.proveedor or ''} {e.descripcion or ''}")
        if pistas & texto:
            origenes.append("coincide el proveedor")
            puntos += P_NOMBRE
        dias = (m.fecha - e.fecha_egreso).days if e.fecha_egreso else 999
        puntos += _cercania(abs(dias))
        cands.append({
            "tipo": "egreso", "id": str(e.id),
            "folio": e.proveedor or "(sin proveedor)", "total": e.monto,
            "fecha": e.fecha_egreso, "descripcion": e.descripcion,
            "empresa": e.empresa.nombre_comercial if getattr(e, "empresa", None) else None,
            "archivo_pdf": e.archivo_pdf or e.path_documento,
            "origen": " + ".join(origenes), "puntos": puntos,
            "confianza": _confianza(puntos),
        })
    cands.sort(key=lambda c: -c["puntos"])
    return [_limpiar(c) for c in cands[:MAX_CANDIDATAS]]


def _limpiar(c: dict) -> dict:
    """El puntaje es interno; afuera sólo viaja la confianza."""
    return {k: v for k, v in c.items() if k != "puntos"}


# ── Aprender ─────────────────────────────────────────────────────────────────

def aprender_alias(db: Session, movimiento: MovimientoBancario,
                   usuario_id: Optional[UUID] = None) -> None:
    """Recuerda que ese ordenante paga por ese cliente.

    Se llama cuando alguien enlaza facturas a mano. Sólo aprende si todas las
    facturas son del mismo cliente: si el depósito junta varios, la equivalencia
    sería ambigua y es mejor no inventarla.
    """
    if movimiento.deposito is None or not movimiento.facturas:
        return
    clientes = {f.cliente_id for f in movimiento.facturas if f.cliente_id}
    if len(clientes) != 1:
        return
    clave = clave_alias(movimiento.concepto)
    if len(clave) < 4:
        return

    cliente_id = clientes.pop()
    empresa_id = movimiento.conciliacion.empresa_id

    existente = (
        db.query(ConciliacionAlias)
        .filter(ConciliacionAlias.empresa_id == empresa_id,
                ConciliacionAlias.ordenante == clave,
                ConciliacionAlias.cliente_id == cliente_id)
        .first()
    )
    if existente:
        existente.veces += 1
    else:
        db.add(ConciliacionAlias(
            empresa_id=empresa_id, ordenante=clave, cliente_id=cliente_id,
            creado_por=usuario_id,
        ))
