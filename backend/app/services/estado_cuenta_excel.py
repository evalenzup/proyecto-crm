# app/services/estado_cuenta_excel.py
"""Lectura del movimiento de cuenta que Banamex deja bajar en Excel.

Es la fuente que de verdad les sirve. El PDF del estado de cuenta no existe
hasta el mes siguiente, y ellas mandan la conciliación a la contadora en dos
partes —del 1 al 15 y del 16 al cierre— para no acumular trabajo. Por eso
descargan el Excel por rango de fechas, que sí está disponible en cualquier
momento.

Cada descarga es una tabla con su propio encabezado y sus propios totales, así
que se valida con la misma disciplina que el PDF: si no cuadra al centavo, no
se importa. Un archivo puede traer varias hojas —cada quincena en la suya, que
es como arman su archivo de trabajo— y cada una se lee como un periodo aparte.

Las columnas de Comentarios y Área que ellas agregan al final no se leen: eso
es el trabajo de conciliación, y aquí sólo interesan los movimientos del banco.
"""
from __future__ import annotations

import datetime
import io
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from app.services.estado_cuenta_banamex import (
    EstadoCuenta, EstadoCuentaInvalido, MESES, Movimiento,
)

logger = logging.getLogger("app")

_PERIODO = re.compile(
    r"Resumen\s+del\s+(\d{2})/(\d{2})/(\d{4})\s+al\s+(\d{2})/(\d{2})/(\d{4})", re.I)
_CONTEO = re.compile(r"(Depósitos|Depositos|Retiros)\s*\((\d+)\)", re.I)


def _texto(v) -> str:
    return "" if v is None else str(v).strip()


def _numero(v) -> Optional[Decimal]:
    """Importe de una celda. El banco pone '-' donde no hay nada."""
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        d = Decimal(str(v))
        return d if d != 0 else None
    t = str(v).replace(",", "").replace("$", "").strip()
    if not t or t in {"-", "—", "–"}:
        return None
    try:
        d = Decimal(t)
    except InvalidOperation:
        return None
    return d if d != 0 else None


def _fecha(v) -> Optional[datetime.date]:
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    t = _texto(v)
    for patron in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(t[:10], patron).date()
        except ValueError:
            continue
    m = re.match(r"^(\d{2})\s+([A-Z]{3})$", t.upper())
    if m and m.group(2) in MESES:
        return None      # sin año no sirve; el encabezado manda
    return None


def _leer_hoja(ws) -> Optional[EstadoCuenta]:
    """Convierte una hoja en un periodo, o None si no parece un movimiento."""
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        return None

    # ── Encabezado ──
    periodo = saldo_ini = saldo_fin = None
    n_dep = n_ret = None
    total_dep = total_ret = None
    cuenta = sucursal = None
    fila_titulos = None

    for i, fila in enumerate(filas[:20]):
        celdas = [_texto(c) for c in fila]
        unido = " ".join(c for c in celdas if c)

        if periodo is None:
            m = _PERIODO.search(unido)
            if m:
                periodo = (
                    datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))),
                    datetime.date(int(m.group(6)), int(m.group(5)), int(m.group(4))),
                )

        for j, c in enumerate(celdas):
            bajo = c.lower()
            if bajo == "sucursal" and sucursal is None:
                sucursal = _numero(fila[j + 1]) if j + 1 < len(fila) else None
            elif bajo == "cuenta" and cuenta is None:
                cuenta = _numero(fila[j + 1]) if j + 1 < len(fila) else None
            elif bajo == "saldo inicial":
                saldo_ini = _numero(fila[j + 1]) if j + 1 < len(fila) else None
            elif bajo == "saldo final":
                saldo_fin = _numero(fila[j + 1]) if j + 1 < len(fila) else None
            elif bajo.startswith(("depósitos (", "depositos (")):
                mc = _CONTEO.search(c)
                if mc:
                    n_dep = int(mc.group(2))
                    total_dep = _numero(fila[j + 1]) if j + 1 < len(fila) else None
            elif bajo.startswith("retiros ("):
                mc = _CONTEO.search(c)
                if mc:
                    n_ret = int(mc.group(2))
                    total_ret = _numero(fila[j + 1]) if j + 1 < len(fila) else None

        # La fila de títulos de la tabla
        if fila_titulos is None and len(celdas) >= 5:
            bajos = [c.lower() for c in celdas[:5]]
            if bajos[0] == "fecha" and "descripci" in bajos[1]:
                fila_titulos = i

    if periodo is None or fila_titulos is None:
        return None

    faltan = [n for n, v in (
        ("saldo inicial", saldo_ini), ("saldo final", saldo_fin),
        ("total de depósitos", total_dep), ("total de retiros", total_ret),
    ) if v is None]
    if faltan or n_dep is None or n_ret is None:
        raise EstadoCuentaInvalido(
            f"A la hoja «{ws.title}» le falta {', '.join(faltan) or 'el conteo de movimientos'} "
            "en el resumen. ¿Se descargó completa del banco?"
        )

    # ── Movimientos ──
    movs: List[Movimiento] = []
    for fila in filas[fila_titulos + 1:]:
        fecha = _fecha(fila[0] if fila else None)
        if fecha is None:
            continue
        concepto = " ".join(_texto(fila[1]).split())
        dep = _numero(fila[2]) if len(fila) > 2 else None
        ret = _numero(fila[3]) if len(fila) > 3 else None
        if dep is None and ret is None:
            continue
        # Sólo lo que cae dentro del periodo que declara el encabezado. Su
        # archivo de trabajo trae pegados los primeros movimientos del mes
        # siguiente, y contarlos descuadraba la hoja contra sus propios totales.
        if fecha < periodo[0] or fecha > periodo[1]:
            continue
        movs.append(Movimiento(fecha=fecha, concepto=concepto, deposito=dep, retiro=ret))

    cuenta_txt = None
    if sucursal is not None and cuenta is not None:
        cuenta_txt = f"{int(sucursal):04d} {int(cuenta)}"

    return EstadoCuenta(
        periodo_inicio=periodo[0], periodo_fin=periodo[1], cuenta=cuenta_txt,
        saldo_inicial=saldo_ini, saldo_final=saldo_fin,
        total_depositos=total_dep, total_retiros=total_ret,
        n_depositos=n_dep, n_retiros=n_ret, movimientos=movs,
    )


def _validar(e: EstadoCuenta, hoja: str) -> None:
    """Mismo rigor que con el PDF: si no cuadra, no se importa."""
    n_dep = sum(1 for m in e.movimientos if m.deposito)
    n_ret = sum(1 for m in e.movimientos if m.retiro)
    sum_dep = sum((m.deposito for m in e.movimientos if m.deposito), Decimal("0"))
    sum_ret = sum((m.retiro for m in e.movimientos if m.retiro), Decimal("0"))

    problemas = []
    if n_dep != e.n_depositos:
        problemas.append(f"depósitos: se leyeron {n_dep} y el banco declara {e.n_depositos}")
    if n_ret != e.n_retiros:
        problemas.append(f"retiros: se leyeron {n_ret} y el banco declara {e.n_retiros}")
    if sum_dep != e.total_depositos:
        problemas.append(f"suma de depósitos: {sum_dep:,.2f} contra {e.total_depositos:,.2f}")
    if sum_ret != e.total_retiros:
        problemas.append(f"suma de retiros: {sum_ret:,.2f} contra {e.total_retiros:,.2f}")

    calculado = e.saldo_inicial + sum_dep - sum_ret
    if calculado != e.saldo_final:
        problemas.append(f"el saldo no cierra: {calculado:,.2f} contra {e.saldo_final:,.2f}")

    if problemas:
        logger.warning("[Conciliación] hoja %s no cuadra: %s", hoja, " · ".join(problemas))
        raise EstadoCuentaInvalido(
            f"La hoja «{hoja}» no se pudo leer completa, así que no se importó. "
            + " · ".join(problemas)
        )


def leer(contenido: bytes) -> List[EstadoCuenta]:
    """Periodos contenidos en el archivo. Una hoja por periodo.

    Una descarga del banco trae una sola hoja; el archivo de trabajo de la
    oficina trae las dos quincenas, cada una en la suya. Los dos casos entran.
    """
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001
        raise EstadoCuentaInvalido(f"No se pudo abrir el Excel: {exc}")

    periodos: List[EstadoCuenta] = []
    for ws in wb.worksheets:
        try:
            e = _leer_hoja(ws)
        except EstadoCuentaInvalido:
            raise
        if e is None:
            continue
        _validar(e, ws.title)
        periodos.append(e)

    if not periodos:
        raise EstadoCuentaInvalido(
            "No se encontró ningún movimiento de cuenta en el archivo. Debe ser el "
            "Excel que descarga el banco, con su resumen de cuenta y el detalle de "
            "movimientos."
        )
    return periodos
