from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import func, case, and_, cast, String
from sqlalchemy.orm import Session

from app.models.factura import Factura
from app.models.egreso import Egreso, EstatusEgreso


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _next_month(dt: datetime) -> datetime:
    y, m = dt.year, dt.month
    if m == 12:
        return dt.replace(year=y + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(month=m + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _year_start(dt: datetime) -> datetime:
    return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _to_period_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def ingresos_egresos_metrics(
    db: Session, *, empresa_id: Optional[str] = None, months: int = 12
) -> Dict[str, Any]:
    now = datetime.utcnow()
    # Generar exactamente `months` periodos incluyendo el mes actual, en orden ascendente
    periods: List[datetime] = []
    cursor = _month_start(now)
    # retrocedemos hasta el mes más antiguo a incluir
    for _ in range(months - 1):
        cursor = _month_start(cursor - timedelta(days=1))
    # y de ahí avanzamos mes a mes hasta incluir el actual
    for _ in range(months):
        periods.append(cursor)
        cursor = _next_month(cursor)

    # Ingresos (pagados): sumatoria de Factura.total con status_pago = PAGADA y estatus TIMBRADA
    # Convertimos a MXN si hay tipo_cambio y moneda != MXN
    monto_mxn = case(
        (
            (Factura.moneda != "MXN") & (Factura.tipo_cambio.isnot(None)),
            Factura.total * Factura.tipo_cambio,
        ),
        else_=Factura.total,
    )

    q_ing_pag = (
        db.query(
            func.date_trunc("month", Factura.fecha_emision).label("period"),
            func.sum(monto_mxn).label("ingresos"),
        )
        .filter(
            Factura.estatus == "TIMBRADA",
            Factura.status_pago == "PAGADA",
        )
    )
    if empresa_id:
        q_ing_pag = q_ing_pag.filter(Factura.empresa_id == empresa_id)
    q_ing_pag = (
        q_ing_pag.group_by(func.date_trunc("month", Factura.fecha_emision))
        .order_by(func.date_trunc("month", Factura.fecha_emision))
        .all()
    )

    ingresos_by_month: Dict[str, Decimal] = {
        _to_period_key(row.period): Decimal(str(row.ingresos or 0)) for row in q_ing_pag
    }

    # Por cobrar: facturas TIMBRADAS y NO_PAGADA
    q_por_cobrar = (
        db.query(
            func.date_trunc("month", Factura.fecha_emision).label("period"),
            func.sum(monto_mxn).label("por_cobrar"),
        )
        .filter(
            Factura.estatus == "TIMBRADA",
            Factura.status_pago == "NO_PAGADA",
        )
    )
    if empresa_id:
        q_por_cobrar = q_por_cobrar.filter(Factura.empresa_id == empresa_id)
    q_por_cobrar = (
        q_por_cobrar.group_by(func.date_trunc("month", Factura.fecha_emision))
        .order_by(func.date_trunc("month", Factura.fecha_emision))
        .all()
    )
    por_cobrar_by_month: Dict[str, Decimal] = {
        _to_period_key(row.period): Decimal(str(row.por_cobrar or 0)) for row in q_por_cobrar
    }

    # Egresos: sumatoria de Egreso.monto para estatus PAGADO (o distintos de CANCELADO)
    q_egr = db.query(
        func.date_trunc("month", Egreso.fecha_egreso).label("period"),
        func.sum(Egreso.monto).label("egresos"),
    ).filter(Egreso.estatus != EstatusEgreso.CANCELADO)
    if empresa_id:
        q_egr = q_egr.filter(Egreso.empresa_id == empresa_id)
    q_egr = (
        q_egr.group_by(func.date_trunc("month", Egreso.fecha_egreso))
        .order_by(func.date_trunc("month", Egreso.fecha_egreso))
        .all()
    )
    egresos_by_month: Dict[str, Decimal] = {
        _to_period_key(row.period): Decimal(str(row.egresos or 0)) for row in q_egr
    }

    # Por pagar: egresos con estatus PENDIENTE
    q_pp = db.query(
        func.date_trunc("month", Egreso.fecha_egreso).label("period"),
        func.sum(Egreso.monto).label("por_pagar"),
    ).filter(Egreso.estatus == EstatusEgreso.PENDIENTE)
    if empresa_id:
        q_pp = q_pp.filter(Egreso.empresa_id == empresa_id)
    q_pp = (
        q_pp.group_by(func.date_trunc("month", Egreso.fecha_egreso))
        .order_by(func.date_trunc("month", Egreso.fecha_egreso))
        .all()
    )
    por_pagar_by_month: Dict[str, Decimal] = {
        _to_period_key(row.period): Decimal(str(row.por_pagar or 0)) for row in q_pp
    }

    # Construimos serie para los últimos `months` meses
    series: List[Dict[str, Any]] = []
    for p in periods:
        k = _to_period_key(p)
        series.append(
            {
                "period": k,
                "ingresos": float(ingresos_by_month.get(k, Decimal("0"))),
                "egresos": float(egresos_by_month.get(k, Decimal("0"))),
                "por_cobrar": float(por_cobrar_by_month.get(k, Decimal("0"))),
                "por_pagar": float(por_pagar_by_month.get(k, Decimal("0"))),
            }
        )

    # MTD / YTD
    month_start = _month_start(now)
    next_month_start = _next_month(month_start)
    year_start = _year_start(now)

    q_ing_mtd = db.query(func.coalesce(func.sum(monto_mxn), 0)).filter(
        Factura.estatus == "TIMBRADA",
        Factura.status_pago == "PAGADA",
        Factura.fecha_emision >= month_start,
        Factura.fecha_emision < next_month_start,
    )
    q_ing_ytd = db.query(func.coalesce(func.sum(monto_mxn), 0)).filter(
        Factura.estatus == "TIMBRADA",
        Factura.status_pago == "PAGADA",
        Factura.fecha_emision >= year_start,
        Factura.fecha_emision < next_month_start,
    )
    # Por cobrar MTD/YTD
    q_pc_mtd = db.query(func.coalesce(func.sum(monto_mxn), 0)).filter(
        Factura.estatus == "TIMBRADA",
        Factura.status_pago == "NO_PAGADA",
        Factura.fecha_emision >= month_start,
        Factura.fecha_emision < next_month_start,
    )
    q_pc_ytd = db.query(func.coalesce(func.sum(monto_mxn), 0)).filter(
        Factura.estatus == "TIMBRADA",
        Factura.status_pago == "NO_PAGADA",
        Factura.fecha_emision >= year_start,
        Factura.fecha_emision < next_month_start,
    )
    if empresa_id:
        q_ing_mtd = q_ing_mtd.filter(Factura.empresa_id == empresa_id)
        q_ing_ytd = q_ing_ytd.filter(Factura.empresa_id == empresa_id)
        q_pc_mtd = q_pc_mtd.filter(Factura.empresa_id == empresa_id)
        q_pc_ytd = q_pc_ytd.filter(Factura.empresa_id == empresa_id)

    q_egr_mtd = db.query(func.coalesce(func.sum(Egreso.monto), 0)).filter(
        Egreso.estatus != EstatusEgreso.CANCELADO,
        Egreso.fecha_egreso >= month_start,
        Egreso.fecha_egreso < next_month_start,
    )
    q_egr_ytd = db.query(func.coalesce(func.sum(Egreso.monto), 0)).filter(
        Egreso.estatus != EstatusEgreso.CANCELADO,
        Egreso.fecha_egreso >= year_start,
        Egreso.fecha_egreso < next_month_start,
    )
    if empresa_id:
        q_egr_mtd = q_egr_mtd.filter(Egreso.empresa_id == empresa_id)
        q_egr_ytd = q_egr_ytd.filter(Egreso.empresa_id == empresa_id)

    ingresos_mtd = float(q_ing_mtd.scalar() or 0)
    ingresos_ytd = float(q_ing_ytd.scalar() or 0)
    por_cobrar_mtd = float(q_pc_mtd.scalar() or 0)
    por_cobrar_ytd = float(q_pc_ytd.scalar() or 0)

    # Por pagar MTD/YTD: egresos en estatus PENDIENTE
    q_pp_mtd = db.query(func.coalesce(func.sum(Egreso.monto), 0)).filter(
        Egreso.estatus == EstatusEgreso.PENDIENTE,
        Egreso.fecha_egreso >= month_start,
        Egreso.fecha_egreso < next_month_start,
    )
    q_pp_ytd = db.query(func.coalesce(func.sum(Egreso.monto), 0)).filter(
        Egreso.estatus == EstatusEgreso.PENDIENTE,
        Egreso.fecha_egreso >= year_start,
        Egreso.fecha_egreso < next_month_start,
    )
    if empresa_id:
        q_pp_mtd = q_pp_mtd.filter(Egreso.empresa_id == empresa_id)
        q_pp_ytd = q_pp_ytd.filter(Egreso.empresa_id == empresa_id)
    por_pagar_mtd = float(q_pp_mtd.scalar() or 0)
    por_pagar_ytd = float(q_pp_ytd.scalar() or 0)
    egresos_mtd = float(q_egr_mtd.scalar() or 0)
    egresos_ytd = float(q_egr_ytd.scalar() or 0)

    return {
        "mtd": {
            "ingresos": ingresos_mtd,
            "egresos": egresos_mtd,
            "por_cobrar": por_cobrar_mtd,
            "por_pagar": por_pagar_mtd,
        },
        "ytd": {
            "ingresos": ingresos_ytd,
            "egresos": egresos_ytd,
            "por_cobrar": por_cobrar_ytd,
            "por_pagar": por_pagar_ytd,
        },
        "series": series,
        "currency": "MXN",
    }


def presupuestos_metrics(db: Session, *, empresa_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula KPIs comerciales basados en presupuestos.
    """
    from app.models.presupuestos import Presupuesto

    base_query = db.query(Presupuesto)
    if empresa_id:
        base_query = base_query.filter(Presupuesto.empresa_id == empresa_id)
    
    # No queremos contar versiones archivadas para las sumas, solo la última versión activa
    # Sin embargo, para simplificar y dado que ARCHIVADO no suma al pipeline activo, filtramos.
    # Pero para tasa de cierre histórica, podríamos querer considerar todo.
    # Por ahora, filtramos ARCHIVADO para tener una foto del estado actual.
    base_query = base_query.filter(Presupuesto.estado != "ARCHIVADO")

    all_presupuestos = base_query.all()

    total_count = len(all_presupuestos)
    aceptados_count = 0
    
    pipeline_amount = Decimal(0)
    lost_sales_amount = Decimal(0)
    won_sales_amount = Decimal(0)
    won_sales_count = 0

    for p in all_presupuestos:
        # Normalizar moneda si es necesario (asumimos MXN o conversión simple por ahora)
        # Idealmente usaríamos p.tipo_cambio
        monto = p.total or Decimal(0)
        if p.moneda != "MXN" and p.tipo_cambio:
            monto = monto * p.tipo_cambio

        if p.estado in ["ACEPTADO", "FACTURADO"]:
            aceptados_count += 1
            won_sales_amount += monto
            won_sales_count += 1
        elif p.estado in ["BORRADOR", "ENVIADO"]:
            pipeline_amount += monto
        elif p.estado in ["RECHAZADO", "CADUCADO"]:
            lost_sales_amount += monto

    conversion_rate = 0.0
    if total_count > 0:
        conversion_rate = (aceptados_count / total_count) * 100

    avg_ticket = 0.0
    if won_sales_count > 0:
        avg_ticket = float(won_sales_amount) / won_sales_count

    return {
        "conversion_rate": round(conversion_rate, 1),
        "pipeline_amount": float(pipeline_amount),
        "lost_sales_amount": float(lost_sales_amount),
        "avg_ticket": float(avg_ticket),
        "currency": "MXN"
    }
