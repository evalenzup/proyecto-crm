# app/services/estado_cuenta_banamex.py
"""Lectura del estado de cuenta de Banamex en PDF.

El PDF es la única fuente: el banco sólo deja bajar el Excel del mes en curso,
así que para cualquier mes ya cerrado esto es lo que hay.

La extracción se valida contra los totales que el propio banco imprime, y
además contra el saldo: inicial + depósitos − retiros tiene que dar el saldo
final al centavo. Si no cuadra, la importación se rechaza. Vale más no importar
que conciliar sobre datos incompletos y que la contadora lo descubra después.

Dos trampas del formato, ambas encontradas cuadrando junio 2026:
  · Al final del PDF viene el CFDI de las comisiones del banco, con sus propios
    importes. Hay que cortar donde termina el detalle de operaciones.
  · La primera línea del detalle trae sangría antes del día, a diferencia del
    resto. Sin permitirla se pierde el primer movimiento del mes.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

logger = logging.getLogger("app")

MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
         "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}

_IMPORTE = re.compile(r"([\d,]+\.\d{2})")
_FECHA = re.compile(rf"^\s*(\d{{2}})\s+({'|'.join(MESES)})\s{{2,}}(.*)$")
# Después de esto ya no hay movimientos: vienen estadísticas y el CFDI del banco
_FIN_DETALLE = re.compile(r"SALDO PROMEDIO MINIMO REQUERIDO|COMISIONES COBRADAS")
# Renglones que traen fecha pero no son un movimiento
_NO_MOVIMIENTO = re.compile(r"NUMERO DE CHEQUES|SALDO ANTERIOR|SALDO AL ")
_RELLENO = re.compile(
    r"^\s*(CAJA \d|HORA |Página|CLIENTE|ESTADO DE CUENTA|DETALLE DE OPERACIONES|"
    r"FECHA\s+CONCEPTO|Centro de Atención|Ciudad de México|Resto del país|"
    r"\d{6}\.B\d{2})"
)

_ENCABEZADO_TABLA = re.compile(r"FECHA\s+CONCEPTO\s+RETIROS\s+DEPOSITOS\s+SALDO")


class EstadoCuentaInvalido(Exception):
    """El PDF no es un estado de cuenta legible, o los números no cuadran."""


@dataclass
class Movimiento:
    fecha: date
    concepto: str
    deposito: Optional[Decimal] = None
    retiro: Optional[Decimal] = None


@dataclass
class EstadoCuenta:
    periodo_inicio: date
    periodo_fin: date
    cuenta: Optional[str]
    saldo_inicial: Decimal
    saldo_final: Decimal
    total_depositos: Decimal
    total_retiros: Decimal
    n_depositos: int
    n_retiros: int
    movimientos: list[Movimiento] = field(default_factory=list)


def _texto(pdf_bytes: bytes) -> str:
    """PDF → texto conservando la posición de las columnas.

    Se usa pypdf en modo layout para no depender de nada instalado en el
    sistema: el contenedor no trae pdftotext y agregarlo obligaría a
    reconstruir la imagen.
    """
    import io

    import pypdf

    try:
        lector = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(
            p.extract_text(extraction_mode="layout") or "" for p in lector.pages
        )
    except Exception as exc:  # noqa: BLE001
        raise EstadoCuentaInvalido(f"No se pudo leer el PDF: {exc}")


def _columnas(texto: str) -> tuple[int, int]:
    """Dónde termina la columna de retiros y dónde la de depósitos.

    Se deducen del encabezado en vez de fijarlas, porque la posición exacta
    depende de cómo escale el extractor. Los importes van alineados a la
    derecha unos caracteres después del título de su columna, así que el
    límite se pone a media distancia entre un título y el siguiente.
    """
    for linea in texto.split("\n"):
        if _ENCABEZADO_TABLA.search(linea):
            fin_ret = linea.index("RETIROS") + len("RETIROS")
            fin_dep = linea.index("DEPOSITOS") + len("DEPOSITOS")
            fin_sal = linea.index("SALDO") + len("SALDO")
            return (fin_ret + fin_dep) // 2, (fin_dep + fin_sal) // 2
    raise EstadoCuentaInvalido(
        "No se encontró la tabla de movimientos. ¿Es un estado de cuenta de Banamex?"
    )


def _decimal(txt: str) -> Decimal:
    return Decimal(txt.replace(",", ""))


def _encabezado(texto: str) -> dict:
    """Periodo, cuenta, saldos y totales que declara el propio banco."""
    datos = {}

    m = re.search(r"RESUMEN DEL:\s*(\d{2})/(\w{3})/(\d{4})\s*AL\s*(\d{2})/(\w{3})/(\d{4})",
                  texto, re.I)
    if not m:
        raise EstadoCuentaInvalido(
            "No se encontró el periodo del estado de cuenta. "
            "¿Es un estado de cuenta de Banamex?"
        )
    datos["periodo_inicio"] = date(int(m.group(3)), MESES[m.group(2).upper()], int(m.group(1)))
    datos["periodo_fin"] = date(int(m.group(6)), MESES[m.group(5).upper()], int(m.group(4)))

    m = re.search(r"Saldo Anterior\s+\$?([\d,]+\.\d{2})", texto, re.I)
    if not m:
        raise EstadoCuentaInvalido("No se encontró el saldo anterior.")
    datos["saldo_inicial"] = _decimal(m.group(1))

    m = re.search(r"\(\s*\+\s*\)\s+(\d+)\s+Depósitos\s+\$?([\d,]+\.\d{2})", texto, re.I)
    if not m:
        raise EstadoCuentaInvalido("No se encontró el total de depósitos.")
    datos["n_depositos"], datos["total_depositos"] = int(m.group(1)), _decimal(m.group(2))

    m = re.search(r"\(\s*-\s*\)\s+(\d+)\s+Retiros\s+\$?([\d,]+\.\d{2})", texto, re.I)
    if not m:
        raise EstadoCuentaInvalido("No se encontró el total de retiros.")
    datos["n_retiros"], datos["total_retiros"] = int(m.group(1)), _decimal(m.group(2))

    m = re.search(r"SALDO AL \d{2} DE \w+ DE \d{4}\s+\$?([\d,]+\.\d{2})", texto, re.I)
    if not m:
        raise EstadoCuentaInvalido("No se encontró el saldo final.")
    datos["saldo_final"] = _decimal(m.group(1))

    m = re.search(r"Cheques\s+(\d{4})\s+(\d{5,})", texto)
    datos["cuenta"] = f"{m.group(1)} {m.group(2)}" if m else None
    return datos


def _movimientos(texto: str, anio: int, col_retiro: int, col_deposito: int) -> list[Movimiento]:
    movs: list[Movimiento] = []
    actual: Optional[dict] = None

    for linea in texto.split("\n"):
        if _FIN_DETALLE.search(linea):
            break
        if not linea.strip():
            continue

        f = _FECHA.match(linea)
        if f:
            if actual:
                movs.append(actual)
            if _NO_MOVIMIENTO.search(linea):
                actual = None
                continue
            actual = {
                "fecha": date(anio, MESES[f.group(2)], int(f.group(1))),
                "concepto": [f.group(3).strip()],
                "deposito": None, "retiro": None,
            }
        elif actual is not None and not _RELLENO.match(linea):
            resto = _IMPORTE.sub("", linea).strip()
            if resto:
                actual["concepto"].append(resto)

        if actual is not None:
            for m in _IMPORTE.finditer(linea):
                valor = _decimal(m.group(1))
                if m.end() <= col_retiro:
                    actual["retiro"] = valor
                elif m.end() <= col_deposito:
                    actual["deposito"] = valor
                # más a la derecha es el saldo corrido: no interesa

    if actual:
        movs.append(actual)

    return [
        Movimiento(fecha=m["fecha"], concepto=" ".join(m["concepto"]),
                   deposito=m["deposito"], retiro=m["retiro"])
        for m in movs if m["deposito"] or m["retiro"]
    ]


def leer(pdf_bytes: bytes) -> EstadoCuenta:
    """Lee el PDF y valida que cuadre. Lanza EstadoCuentaInvalido si no."""
    texto = _texto(pdf_bytes)
    cab = _encabezado(texto)
    col_ret, col_dep = _columnas(texto)
    movs = _movimientos(texto, cab["periodo_fin"].year, col_ret, col_dep)

    n_dep = sum(1 for m in movs if m.deposito)
    n_ret = sum(1 for m in movs if m.retiro)
    sum_dep = sum((m.deposito for m in movs if m.deposito), Decimal("0"))
    sum_ret = sum((m.retiro for m in movs if m.retiro), Decimal("0"))

    problemas = []
    if n_dep != cab["n_depositos"]:
        problemas.append(f"depósitos: se leyeron {n_dep} y el banco declara {cab['n_depositos']}")
    if n_ret != cab["n_retiros"]:
        problemas.append(f"retiros: se leyeron {n_ret} y el banco declara {cab['n_retiros']}")
    if sum_dep != cab["total_depositos"]:
        problemas.append(f"suma de depósitos: {sum_dep:,.2f} contra {cab['total_depositos']:,.2f}")
    if sum_ret != cab["total_retiros"]:
        problemas.append(f"suma de retiros: {sum_ret:,.2f} contra {cab['total_retiros']:,.2f}")

    # El control de fondo: el saldo tiene que cerrar solo
    calculado = cab["saldo_inicial"] + sum_dep - sum_ret
    if calculado != cab["saldo_final"]:
        problemas.append(
            f"el saldo no cierra: {calculado:,.2f} contra {cab['saldo_final']:,.2f}"
        )

    if problemas:
        logger.warning("[Conciliación] PDF no cuadra: %s", " · ".join(problemas))
        raise EstadoCuentaInvalido(
            "El estado de cuenta no se pudo leer completo, así que no se importó. "
            + " · ".join(problemas)
        )

    return EstadoCuenta(movimientos=movs, **cab)
