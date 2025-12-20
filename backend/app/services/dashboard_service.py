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

    # --- OPTIMIZATION START ---
    # Consolidate MTD/YTD queries into single queries per table (Factura, Egreso) to reduce roundtrips.
    
    # 1. Facturas Aggregation (Ingresos + Por Cobrar for MTD & YTD)
    # Filter common: estatus TIMBRADA, fecha >= year_start
    q_facturas_agg = db.query(
        # Ingresos MTD
        func.sum(
             case(
                 (
                     (Factura.status_pago == "PAGADA") & 
                     (Factura.fecha_emision >= month_start) & 
                     (Factura.fecha_emision < next_month_start), 
                     monto_mxn
                 ),
                 else_=0
             )
        ).label("ingresos_mtd"),
        # Ingresos YTD
        func.sum(
             case(
                 (
                     (Factura.status_pago == "PAGADA") &
                     (Factura.fecha_emision >= year_start) &
                     (Factura.fecha_emision < next_month_start),
                     monto_mxn
                 ),
                 else_=0
             )
        ).label("ingresos_ytd"),
        # Por Cobrar MTD
        func.sum(
             case(
                 (
                     (Factura.status_pago == "NO_PAGADA") &
                     (Factura.fecha_emision >= month_start) &
                     (Factura.fecha_emision < next_month_start),
                     monto_mxn
                 ),
                 else_=0
             )
        ).label("por_cobrar_mtd"),
        # Por Cobrar YTD
        func.sum(
             case(
                 (
                     (Factura.status_pago == "NO_PAGADA") &
                     (Factura.fecha_emision >= year_start) &
                     (Factura.fecha_emision < next_month_start),
                     monto_mxn
                 ),
                 else_=0
             )
        ).label("por_cobrar_ytd"),
    ).filter(
        Factura.estatus == "TIMBRADA",
        Factura.fecha_emision >= year_start, # Base filter is YTD (since MTD is subset of YTD)
        Factura.fecha_emision < next_month_start
    )
    
    if empresa_id:
        q_facturas_agg = q_facturas_agg.filter(Factura.empresa_id == empresa_id)

    fact_agg = q_facturas_agg.one()
    
    ingresos_mtd = float(fact_agg.ingresos_mtd or 0)
    ingresos_ytd = float(fact_agg.ingresos_ytd or 0)
    por_cobrar_mtd = float(fact_agg.por_cobrar_mtd or 0)
    por_cobrar_ytd = float(fact_agg.por_cobrar_ytd or 0)

    # 2. Egresos Aggregation (Egresos + Por Pagar for MTD & YTD)
    # Filter common: fecha >= year_start
    q_egresos_agg = db.query(
        # Egresos MTD (estatus != CANCELADO)
        func.sum(
             case(
                 (
                     (Egreso.estatus != EstatusEgreso.CANCELADO) & 
                     (Egreso.fecha_egreso >= month_start) & 
                     (Egreso.fecha_egreso < next_month_start), 
                     Egreso.monto
                 ),
                 else_=0
             )
        ).label("egresos_mtd"),
        # Egresos YTD
        func.sum(
             case(
                 (
                     (Egreso.estatus != EstatusEgreso.CANCELADO) & 
                     (Egreso.fecha_egreso >= year_start) & 
                     (Egreso.fecha_egreso < next_month_start), 
                     Egreso.monto
                 ),
                 else_=0
             )
        ).label("egresos_ytd"),
        # Por Pagar MTD (estatus == PENDIENTE)
        func.sum(
             case(
                 (
                     (Egreso.estatus == EstatusEgreso.PENDIENTE) & 
                     (Egreso.fecha_egreso >= month_start) & 
                     (Egreso.fecha_egreso < next_month_start), 
                     Egreso.monto
                 ),
                 else_=0
             )
        ).label("por_pagar_mtd"),
        # Por Pagar YTD
        func.sum(
             case(
                 (
                     (Egreso.estatus == EstatusEgreso.PENDIENTE) & 
                     (Egreso.fecha_egreso >= year_start) & 
                     (Egreso.fecha_egreso < next_month_start), 
                     Egreso.monto
                 ),
                 else_=0
             )
        ).label("por_pagar_ytd"),
    ).filter(
        Egreso.fecha_egreso >= year_start,
        Egreso.fecha_egreso < next_month_start
    )

    if empresa_id:
        q_egresos_agg = q_egresos_agg.filter(Egreso.empresa_id == empresa_id)

    egr_agg = q_egresos_agg.one()

    egresos_mtd = float(egr_agg.egresos_mtd or 0)
    egresos_ytd = float(egr_agg.egresos_ytd or 0)
    por_pagar_mtd = float(egr_agg.por_pagar_mtd or 0)
    por_pagar_ytd = float(egr_agg.por_pagar_ytd or 0)
    # --- OPTIMIZATION END ---

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

    # Base query filters
    filters = [Presupuesto.estado != "ARCHIVADO"]
    if empresa_id:
        filters.append(Presupuesto.empresa_id == empresa_id)

    # Expression for normalized amount (MXN)
    # SUM(CASE WHEN moneda != 'MXN' AND tipo_cambio IS NOT NULL THEN total * tipo_cambio ELSE total END)
    monto_mxn = case(
        (
            (Presupuesto.moneda != "MXN") & (Presupuesto.tipo_cambio.isnot(None)),
            Presupuesto.total * Presupuesto.tipo_cambio,
        ),
        else_=Presupuesto.total,
    )

    # Aggregations in a single query
    q = db.query(
        func.count().label("total_count"),
        func.sum(
            case(
                (Presupuesto.estado.in_(["ACEPTADO", "FACTURADO"]), 1), else_=0
            )
        ).label("won_count"),
        func.sum(
            case(
                (Presupuesto.estado.in_(["ACEPTADO", "FACTURADO"]), monto_mxn),
                else_=0,
            )
        ).label("won_amount"),
        func.sum(
            case(
                (Presupuesto.estado.in_(["BORRADOR", "ENVIADO"]), monto_mxn),
                else_=0,
            )
        ).label("pipeline_amount"),
        func.sum(
            case(
                (Presupuesto.estado.in_(["RECHAZADO", "CADUCADO"]), monto_mxn),
                else_=0,
            )
        ).label("lost_amount"),
    ).filter(*filters)

    result = q.one()

    total_count = result.total_count or 0
    won_count = result.won_count or 0
    won_sales_amount = float(result.won_amount or 0)
    pipeline_amount = float(result.pipeline_amount or 0)
    lost_sales_amount = float(result.lost_amount or 0)

    conversion_rate = 0.0
    if total_count > 0:
        conversion_rate = (won_count / total_count) * 100

    avg_ticket = 0.0
    if won_count > 0:
        avg_ticket = won_sales_amount / won_count

    return {
        "conversion_rate": round(conversion_rate, 1),
        "pipeline_amount": pipeline_amount,
        "lost_sales_amount": lost_sales_amount,
        "avg_ticket": float(avg_ticket),
        "currency": "MXN",
    }
