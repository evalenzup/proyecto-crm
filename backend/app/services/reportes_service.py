from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.models.factura import Factura
from app.models.egreso import Egreso, EstatusEgreso
from app.models.cliente import Cliente


def _next_month(dt: datetime) -> datetime:
    y, m = dt.year, dt.month
    if m == 12:
        return dt.replace(year=y + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(month=m + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def financiero_mensual(
    db: Session,
    *,
    empresa_ids: Optional[List[str]] = None,
    fecha_inicio: datetime,   # first day of start month
    fecha_fin: datetime,      # first day of end month (inclusive)
) -> Dict[str, Any]:
    """
    Returns monthly financial breakdown and summary KPIs for the given date range.
    fecha_inicio and fecha_fin are the first day of their respective months.
    The range is [fecha_inicio, fecha_fin] inclusive (both months included).
    """
    fecha_fin_exclusive = _next_month(fecha_fin)

    monto_mxn = case(
        ((Factura.moneda != "MXN") & (Factura.tipo_cambio.isnot(None)),
         Factura.total * Factura.tipo_cambio),
        else_=Factura.total,
    )

    # --- Facturas by month ---
    q_fact = db.query(
        func.date_trunc("month", Factura.fecha_emision).label("periodo"),
        func.sum(case((Factura.status_pago == "PAGADA", monto_mxn), else_=0)).label("cobrado"),
        func.sum(case((Factura.status_pago == "NO_PAGADA", monto_mxn), else_=0)).label("por_cobrar"),
        func.sum(monto_mxn).label("facturado"),
    ).filter(
        Factura.estatus == "TIMBRADA",
        Factura.fecha_emision >= fecha_inicio,
        Factura.fecha_emision < fecha_fin_exclusive,
    )
    if empresa_ids:
        q_fact = q_fact.filter(Factura.empresa_id.in_(empresa_ids))
    fact_rows = {
        row.periodo.strftime("%Y-%m"): row
        for row in q_fact.group_by(func.date_trunc("month", Factura.fecha_emision)).all()
    }

    # --- Egresos by month ---
    q_egr = db.query(
        func.date_trunc("month", Egreso.fecha_egreso).label("periodo"),
        func.sum(Egreso.monto).label("egresos"),
    ).filter(
        Egreso.estatus != EstatusEgreso.CANCELADO,
        Egreso.fecha_egreso >= fecha_inicio,
        Egreso.fecha_egreso < fecha_fin_exclusive,
    )
    if empresa_ids:
        q_egr = q_egr.filter(Egreso.empresa_id.in_(empresa_ids))
    egr_rows = {
        row.periodo.strftime("%Y-%m"): float(row.egresos or 0)
        for row in q_egr.group_by(func.date_trunc("month", Egreso.fecha_egreso)).all()
    }

    # --- Build month list ---
    meses: List[Dict[str, Any]] = []
    cursor = fecha_inicio
    while cursor <= fecha_fin:
        key = cursor.strftime("%Y-%m")
        fr = fact_rows.get(key)
        facturado  = float(fr.facturado  or 0) if fr else 0.0
        cobrado    = float(fr.cobrado    or 0) if fr else 0.0
        por_cobrar = float(fr.por_cobrar or 0) if fr else 0.0
        egresos    = egr_rows.get(key, 0.0)
        utilidad   = cobrado - egresos
        margen     = round(utilidad / cobrado * 100, 1) if cobrado > 0 else 0.0
        meses.append({
            "periodo": key,
            "facturado": facturado,
            "cobrado": cobrado,
            "por_cobrar": por_cobrar,
            "egresos": egresos,
            "utilidad": utilidad,
            "margen_pct": margen,
        })
        cursor = _next_month(cursor)

    # --- KPIs (totals) ---
    tot_facturado  = sum(m["facturado"]  for m in meses)
    tot_cobrado    = sum(m["cobrado"]    for m in meses)
    tot_por_cobrar = sum(m["por_cobrar"] for m in meses)
    tot_egresos    = sum(m["egresos"]    for m in meses)
    tot_utilidad   = tot_cobrado - tot_egresos
    tot_margen     = round(tot_utilidad / tot_cobrado * 100, 1) if tot_cobrado > 0 else 0.0

    return {
        "kpis": {
            "total_facturado": tot_facturado,
            "cobrado": tot_cobrado,
            "por_cobrar": tot_por_cobrar,
            "egresos": tot_egresos,
            "utilidad": tot_utilidad,
            "margen_pct": tot_margen,
        },
        "meses": meses,
    }


def egresos_categoria_rango(
    db: Session,
    *,
    empresa_ids: Optional[List[str]] = None,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> List[Dict[str, Any]]:
    fecha_fin_exclusive = _next_month(fecha_fin)

    q = db.query(
        Egreso.categoria,
        func.sum(Egreso.monto).label("total"),
    ).filter(
        Egreso.estatus != EstatusEgreso.CANCELADO,
        Egreso.fecha_egreso >= fecha_inicio,
        Egreso.fecha_egreso < fecha_fin_exclusive,
    )
    if empresa_ids:
        q = q.filter(Egreso.empresa_id.in_(empresa_ids))
    rows = q.group_by(Egreso.categoria).order_by(func.sum(Egreso.monto).desc()).all()

    total = sum(float(r.total or 0) for r in rows)
    return [
        {
            "name": r.categoria.value if hasattr(r.categoria, "value") else str(r.categoria),
            "value": float(r.total or 0),
            "pct": round(float(r.total or 0) / total * 100, 1) if total > 0 else 0.0,
        }
        for r in rows
    ]


def ventas_reporte(
    db: Session,
    *,
    empresa_ids: Optional[List[str]] = None,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> Dict[str, Any]:
    from app.models.presupuestos import Presupuesto
    from collections import defaultdict

    fecha_fin_exclusive = _next_month(fecha_fin)

    # fecha_emision is a Date column — compare directly with .date()
    fi_date = fecha_inicio.date()
    ff_date = fecha_fin_exclusive.date()

    monto_mxn_p = case(
        ((Presupuesto.moneda != "MXN") & (Presupuesto.tipo_cambio.isnot(None)),
         Presupuesto.total * Presupuesto.tipo_cambio),
        else_=Presupuesto.total,
    )

    # Funnel aggregation in single query
    agg = db.query(
        Presupuesto.estado,
        func.count().label("cantidad"),
        func.sum(monto_mxn_p).label("monto"),
    ).filter(
        Presupuesto.estado != "ARCHIVADO",
        Presupuesto.fecha_emision >= fi_date,
        Presupuesto.fecha_emision < ff_date,
    )
    if empresa_ids:
        agg = agg.filter(Presupuesto.empresa_id.in_(empresa_ids))
    agg_rows = {r.estado: r for r in agg.group_by(Presupuesto.estado).all()}

    ETAPAS = ["BORRADOR", "ENVIADO", "ACEPTADO", "FACTURADO", "RECHAZADO", "CADUCADO"]
    ETAPA_LABELS = {
        "BORRADOR": "Borrador", "ENVIADO": "Enviado",
        "ACEPTADO": "Aceptado", "FACTURADO": "Facturado",
        "RECHAZADO": "Rechazado", "CADUCADO": "Caducado",
    }
    embudo = [
        {
            "etapa": ETAPA_LABELS.get(e, e),
            "cantidad": agg_rows[e].cantidad if e in agg_rows else 0,
            "monto": float(agg_rows[e].monto or 0) if e in agg_rows else 0.0,
        }
        for e in ETAPAS
    ]

    total = sum(r["cantidad"] for r in embudo)
    won_count  = sum(r["cantidad"] for r in embudo if r["etapa"] in ("Aceptado", "Facturado"))
    won_amount = sum(r["monto"]    for r in embudo if r["etapa"] in ("Aceptado", "Facturado"))
    pipeline   = sum(r["monto"]    for r in embudo if r["etapa"] in ("Borrador", "Enviado"))
    tasa   = round(won_count / total * 100, 1) if total > 0 else 0.0
    ticket = round(won_amount / won_count, 2)   if won_count > 0 else 0.0

    # Monthly evolution: cerrados (Aceptado+Facturado) vs enviados/borrador
    # fecha_emision is a Date column — use func.date_trunc directly
    q_meses = db.query(
        func.date_trunc("month", Presupuesto.fecha_emision).label("periodo"),
        Presupuesto.estado,
        func.count().label("cantidad"),
        func.sum(monto_mxn_p).label("monto"),
    ).filter(
        Presupuesto.estado != "ARCHIVADO",
        Presupuesto.fecha_emision >= fi_date,
        Presupuesto.fecha_emision < ff_date,
    )
    if empresa_ids:
        q_meses = q_meses.filter(Presupuesto.empresa_id.in_(empresa_ids))
    meses_rows = q_meses.group_by(
        func.date_trunc("month", Presupuesto.fecha_emision),
        Presupuesto.estado,
    ).all()

    meses_dict: Dict[str, Dict] = defaultdict(
        lambda: {"cerrados": 0, "monto_cerrado": 0.0, "enviados": 0, "monto_pipeline": 0.0}
    )
    for r in meses_rows:
        key = r.periodo.strftime("%Y-%m")
        if r.estado in ("ACEPTADO", "FACTURADO"):
            meses_dict[key]["cerrados"]      += r.cantidad
            meses_dict[key]["monto_cerrado"] += float(r.monto or 0)
        elif r.estado in ("BORRADOR", "ENVIADO"):
            meses_dict[key]["enviados"]        += r.cantidad
            meses_dict[key]["monto_pipeline"]  += float(r.monto or 0)

    meses_list = []
    cursor = fecha_inicio
    while cursor <= fecha_fin:
        key = cursor.strftime("%Y-%m")
        d = meses_dict.get(key, {})
        meses_list.append({
            "periodo": key,
            "cerrados": d.get("cerrados", 0),
            "monto_cerrado": d.get("monto_cerrado", 0.0),
            "enviados": d.get("enviados", 0),
            "monto_pipeline": d.get("monto_pipeline", 0.0),
        })
        cursor = _next_month(cursor)

    return {
        "kpis": {
            "total_presupuestos": total,
            "tasa_conversion_pct": tasa,
            "pipeline_abierto": pipeline,
            "ticket_promedio": ticket,
        },
        "embudo": embudo,
        "meses": meses_list,
    }


def financiero_por_empresa(
    db: Session,
    *,
    empresa_ids: Optional[List[str]] = None,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> List[Dict[str, Any]]:
    """
    Devuelve totales financieros y desglose mensual por empresa.
    Usado cuando el usuario selecciona 'General (todas)'.
    """
    from app.models.empresa import Empresa as EmpresaModel

    fecha_fin_exclusive = _next_month(fecha_fin)

    monto_mxn = case(
        ((Factura.moneda != "MXN") & (Factura.tipo_cambio.isnot(None)),
         Factura.total * Factura.tipo_cambio),
        else_=Factura.total,
    )

    # Obtener empresas accesibles ordenadas por nombre
    q_emp = db.query(EmpresaModel.id, EmpresaModel.nombre_comercial)
    if empresa_ids:
        q_emp = q_emp.filter(EmpresaModel.id.in_(empresa_ids))
    empresas_list = q_emp.order_by(EmpresaModel.nombre_comercial).all()

    # Facturas agrupadas por (empresa_id, mes)
    q_fact = db.query(
        Factura.empresa_id,
        func.date_trunc("month", Factura.fecha_emision).label("periodo"),
        func.sum(case((Factura.status_pago == "PAGADA", monto_mxn), else_=0)).label("cobrado"),
        func.sum(case((Factura.status_pago == "NO_PAGADA", monto_mxn), else_=0)).label("por_cobrar"),
        func.sum(monto_mxn).label("facturado"),
    ).filter(
        Factura.estatus == "TIMBRADA",
        Factura.fecha_emision >= fecha_inicio,
        Factura.fecha_emision < fecha_fin_exclusive,
    )
    if empresa_ids:
        q_fact = q_fact.filter(Factura.empresa_id.in_(empresa_ids))
    # {(empresa_id_str, "YYYY-MM"): row}
    fact_map: Dict[tuple, Any] = {}
    for r in q_fact.group_by(Factura.empresa_id, func.date_trunc("month", Factura.fecha_emision)).all():
        fact_map[(str(r.empresa_id), r.periodo.strftime("%Y-%m"))] = r

    # Egresos agrupados por (empresa_id, mes)
    q_egr = db.query(
        Egreso.empresa_id,
        func.date_trunc("month", Egreso.fecha_egreso).label("periodo"),
        func.sum(Egreso.monto).label("egresos"),
    ).filter(
        Egreso.estatus != EstatusEgreso.CANCELADO,
        Egreso.fecha_egreso >= fecha_inicio,
        Egreso.fecha_egreso < fecha_fin_exclusive,
    )
    if empresa_ids:
        q_egr = q_egr.filter(Egreso.empresa_id.in_(empresa_ids))
    egr_map: Dict[tuple, float] = {
        (str(r.empresa_id), r.periodo.strftime("%Y-%m")): float(r.egresos or 0)
        for r in q_egr.group_by(Egreso.empresa_id, func.date_trunc("month", Egreso.fecha_egreso)).all()
    }

    # Construir lista de meses del rango
    meses_keys: List[str] = []
    cursor = fecha_inicio
    while cursor <= fecha_fin:
        meses_keys.append(cursor.strftime("%Y-%m"))
        cursor = _next_month(cursor)

    result = []
    for emp in empresas_list:
        eid = str(emp.id)
        meses_data: List[Dict[str, Any]] = []
        tot_facturado = 0.0
        tot_cobrado = 0.0
        tot_por_cobrar = 0.0
        tot_egresos = 0.0

        for key in meses_keys:
            fr = fact_map.get((eid, key))
            facturado = float(fr.facturado or 0) if fr else 0.0
            cobrado   = float(fr.cobrado   or 0) if fr else 0.0
            por_cobrar= float(fr.por_cobrar or 0) if fr else 0.0
            egresos   = egr_map.get((eid, key), 0.0)
            meses_data.append({
                "periodo": key,
                "cobrado": cobrado,
                "por_cobrar": por_cobrar,
                "facturado": facturado,
                "egresos": egresos,
            })
            tot_facturado += facturado
            tot_cobrado   += cobrado
            tot_por_cobrar+= por_cobrar
            tot_egresos   += egresos

        utilidad = tot_cobrado - tot_egresos
        margen   = round(utilidad / tot_cobrado * 100, 1) if tot_cobrado > 0 else 0.0
        result.append({
            "empresa_id": eid,
            "nombre_comercial": emp.nombre_comercial,
            "facturado": tot_facturado,
            "cobrado": tot_cobrado,
            "por_cobrar": tot_por_cobrar,
            "egresos": tot_egresos,
            "utilidad": utilidad,
            "margen_pct": margen,
            "meses": meses_data,
        })

    result.sort(key=lambda x: x["facturado"], reverse=True)
    return result


def clientes_reporte(
    db: Session,
    *,
    empresa_ids: Optional[List[str]] = None,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> Dict[str, Any]:
    import datetime as dt_module
    from sqlalchemy import select

    fecha_fin_exclusive = _next_month(fecha_fin)
    now = datetime.utcnow()
    dias_90 = now - dt_module.timedelta(days=90)

    monto_mxn = case(
        ((Factura.moneda != "MXN") & (Factura.tipo_cambio.isnot(None)),
         Factura.total * Factura.tipo_cambio),
        else_=Factura.total,
    )

    base_filter = [
        Factura.estatus == "TIMBRADA",
        Factura.fecha_emision >= fecha_inicio,
        Factura.fecha_emision < fecha_fin_exclusive,
    ]
    if empresa_ids:
        base_filter.append(Factura.empresa_id.in_(empresa_ids))

    # Top clientes by monto (group by RFC to consolidate)
    top_rows = db.query(
        Cliente.rfc,
        Cliente.nombre_comercial,
        Cliente.nombre_razon_social,
        func.sum(monto_mxn).label("monto"),
        func.count(Factura.id).label("facturas"),
        func.max(Factura.fecha_emision).label("ultima_factura"),
    ).join(
        Cliente, Factura.cliente_id == Cliente.id
    ).filter(*base_filter).group_by(
        Cliente.rfc, Cliente.nombre_comercial, Cliente.nombre_razon_social
    ).order_by(func.sum(monto_mxn).desc()).limit(15).all()

    top_clientes = [
        {
            "rfc": r.rfc,
            "nombre_comercial": r.nombre_comercial,
            "nombre_razon_social": r.nombre_razon_social,
            "monto": float(r.monto or 0),
            "facturas": r.facturas,
            "ticket_promedio": round(float(r.monto or 0) / r.facturas, 2) if r.facturas > 0 else 0.0,
            "ultima_factura": r.ultima_factura.strftime("%Y-%m-%d") if r.ultima_factura else None,
        }
        for r in top_rows
    ]

    # KPI: total clientes activos in period
    total_activos = db.query(func.count(func.distinct(Factura.cliente_id))).filter(*base_filter).scalar() or 0

    # KPI: new clients (first invoice ever in this period)
    sub_antes = (
        select(Factura.cliente_id)
        .where(
            Factura.estatus == "TIMBRADA",
            Factura.fecha_emision < fecha_inicio,
            *(([Factura.empresa_id.in_(empresa_ids)]) if empresa_ids else []),
        )
        .distinct()
        .scalar_subquery()
    )
    nuevos = db.query(func.count(func.distinct(Factura.cliente_id))).filter(
        *base_filter,
        Factura.cliente_id.notin_(sub_antes),
    ).scalar() or 0

    # KPI: clients at risk (had history, no activity in 90 days)
    sub_hist = (
        select(Factura.cliente_id)
        .where(Factura.estatus == "TIMBRADA",
               *(([Factura.empresa_id.in_(empresa_ids)]) if empresa_ids else []))
        .distinct().scalar_subquery()
    )
    sub_recent = (
        select(Factura.cliente_id)
        .where(Factura.estatus == "TIMBRADA",
               Factura.fecha_emision >= dias_90,
               *(([Factura.empresa_id.in_(empresa_ids)]) if empresa_ids else []))
        .distinct().scalar_subquery()
    )
    en_riesgo = db.query(func.count(func.distinct(Factura.cliente_id))).filter(
        Factura.estatus == "TIMBRADA",
        Factura.cliente_id.in_(sub_hist),
        Factura.cliente_id.notin_(sub_recent),
        *(([Factura.empresa_id.in_(empresa_ids)]) if empresa_ids else []),
    ).scalar() or 0

    # New vs recurring per month
    meses_list = []
    cursor = fecha_inicio
    while cursor <= fecha_fin:
        m_end = _next_month(cursor)
        key = cursor.strftime("%Y-%m")
        m_filter = [
            Factura.estatus == "TIMBRADA",
            Factura.fecha_emision >= cursor,
            Factura.fecha_emision < m_end,
        ]
        if empresa_ids:
            m_filter.append(Factura.empresa_id.in_(empresa_ids))

        sub_antes_m = (
            select(Factura.cliente_id)
            .where(Factura.estatus == "TIMBRADA",
                   Factura.fecha_emision < cursor,
                   *(([Factura.empresa_id.in_(empresa_ids)]) if empresa_ids else []))
            .distinct().scalar_subquery()
        )
        nuevos_m = db.query(func.count(func.distinct(Factura.cliente_id))).filter(
            *m_filter, Factura.cliente_id.notin_(sub_antes_m)
        ).scalar() or 0

        recurrentes_m = db.query(func.count(func.distinct(Factura.cliente_id))).filter(
            *m_filter, Factura.cliente_id.in_(sub_antes_m)
        ).scalar() or 0

        meses_list.append({
            "periodo": key,
            "nuevos": nuevos_m,
            "recurrentes": recurrentes_m,
        })
        cursor = m_end

    return {
        "kpis": {
            "total_activos": total_activos,
            "nuevos": nuevos,
            "en_riesgo": en_riesgo,
        },
        "top_clientes": top_clientes,
        "meses": meses_list,
    }
