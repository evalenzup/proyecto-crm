# app/services/plan_servicio_service.py
"""
Planes de servicio (contratos) + tablero mensual de programación.

No genera órdenes por adelantado: el tablero calcula los periodos esperados de
cada plan en un mes y el usuario programa (crea la orden) cuando corresponde.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.orden_servicio import OrdenServicio
from app.models.plan_servicio import PlanServicio
from app.schemas.plan_servicio import (
    PlanServicioCreate,
    PlanServicioUpdate,
    ProgramarRequest,
)

# Intervalo en meses por periodicidad (QUINCENAL se maneja aparte).
_MESES_INTERVALO = {"MENSUAL": 1, "BIMESTRAL": 2, "TRIMESTRAL": 3}

# Estados de orden que cuentan como "servicio realizado" / "cancelado".
_ESTADOS_COMPLETADA = {"COMPLETADO"}
_ESTADOS_CANCELADA = {"CANCELADO"}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _clamp_dia(anio: int, mes: int, dia: int) -> date:
    """Día del mes acotado al último día real (ej. 31 en febrero → 28/29)."""
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(max(dia, 1), ultimo))


def _mes_index(d: date) -> int:
    return d.year * 12 + (d.month - 1)


def periodos_del_mes(plan: PlanServicio, anio: int, mes: int) -> List[date]:
    """
    Fechas tentativas esperadas del plan dentro del mes (anio, mes),
    respetando vigencia y periodicidad. Devuelve la lista ordenada.
    """
    dia = plan.dia_preferido or 1
    inicio_mes = date(anio, mes, 1)
    fin_mes = _clamp_dia(anio, mes, 31)

    def _en_vigencia(f: date) -> bool:
        if f < plan.vigencia_desde:
            return False
        if plan.vigencia_hasta and f > plan.vigencia_hasta:
            return False
        return True

    fechas: List[date] = []

    if plan.periodicidad == "QUINCENAL":
        # Dos visitas: el día base y quince días después, ambas dentro del mes.
        f1 = _clamp_dia(anio, mes, dia)
        segundo_dia = dia + 15
        f2 = date(anio, mes, segundo_dia) if segundo_dia <= calendar.monthrange(anio, mes)[1] else None
        for f in (f1, f2):
            if f and _en_vigencia(f):
                fechas.append(f)
    else:
        intervalo = _MESES_INTERVALO.get(plan.periodicidad, 1)
        # ¿Este mes es un mes de servicio según la vigencia inicial?
        delta = _mes_index(inicio_mes) - _mes_index(plan.vigencia_desde.replace(day=1))
        if delta >= 0 and delta % intervalo == 0:
            f = _clamp_dia(anio, mes, dia)
            if _en_vigencia(f):
                fechas.append(f)

    return sorted(fechas)


# ─── CRUD ─────────────────────────────────────────────────────────────────────
def _to_out_extra(plan: PlanServicio) -> dict:
    """Campos denormalizados para PlanServicioOut."""
    return {
        "cliente_nombre": getattr(plan.cliente, "nombre_comercial", None)
        or getattr(plan.cliente, "razon_social", None),
        "servicio_nombre": getattr(plan.servicio, "nombre", None) if plan.servicio else None,
        "tecnico_nombre": getattr(plan.tecnico, "nombre_completo", None)
        or getattr(plan.tecnico, "nombre", None) if plan.tecnico else None,
        "certificado_folio": getattr(plan.certificado, "folio", None) if plan.certificado else None,
    }


def crear_plan(db: Session, payload: PlanServicioCreate) -> PlanServicio:
    plan = PlanServicio(id=uuid4(), **payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def obtener_plan(db: Session, plan_id: UUID) -> PlanServicio:
    plan = db.query(PlanServicio).filter(PlanServicio.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan de servicio no encontrado.")
    return plan


def listar_planes(
    db: Session,
    *,
    empresa_id: Optional[UUID] = None,
    cliente_id: Optional[UUID] = None,
    activo: Optional[bool] = None,
) -> List[PlanServicio]:
    q = db.query(PlanServicio)
    if empresa_id:
        q = q.filter(PlanServicio.empresa_id == empresa_id)
    if cliente_id:
        q = q.filter(PlanServicio.cliente_id == cliente_id)
    if activo is not None:
        q = q.filter(PlanServicio.activo == activo)
    return q.order_by(PlanServicio.creado_en.desc()).all()


def actualizar_plan(db: Session, plan_id: UUID, payload: PlanServicioUpdate) -> PlanServicio:
    plan = obtener_plan(db, plan_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(plan, campo, valor)
    db.commit()
    db.refresh(plan)
    return plan


def eliminar_plan(db: Session, plan_id: UUID) -> None:
    plan = obtener_plan(db, plan_id)
    db.delete(plan)
    db.commit()


# ─── Tablero ──────────────────────────────────────────────────────────────────
def tablero(db: Session, *, empresa_id: UUID, anio: int, mes: int) -> dict:
    """
    Estatus por plan/periodo para el mes consultado.

    Estatus de cada periodo:
      SIN_PROGRAMAR — sin orden ligada al plan en esa fecha
      PROGRAMADA    — hay orden ligada (estado activo)
      COMPLETADA    — la orden está COMPLETADO
      CANCELADA     — la orden está CANCELADO
    """
    inicio_mes = date(anio, mes, 1)
    fin_mes = _clamp_dia(anio, mes, 31)

    planes = (
        db.query(PlanServicio)
        .filter(
            PlanServicio.empresa_id == empresa_id,
            PlanServicio.activo.is_(True),
            PlanServicio.vigencia_desde <= fin_mes,
        )
        .all()
    )
    planes = [
        p for p in planes
        if p.vigencia_hasta is None or p.vigencia_hasta >= inicio_mes
    ]

    filas = []
    for plan in planes:
        fechas = periodos_del_mes(plan, anio, mes)
        if not fechas:
            continue

        # Órdenes del plan dentro del mes.
        ordenes = (
            db.query(OrdenServicio)
            .filter(
                OrdenServicio.plan_id == plan.id,
                OrdenServicio.fecha_programada >= inicio_mes,
                OrdenServicio.fecha_programada <= fin_mes,
            )
            .all()
        )

        periodos = []
        usadas: set = set()
        for ft in fechas:
            # Asignar la orden más cercana a la fecha tentativa (aún no usada).
            mejor = None
            mejor_dist = None
            for o in ordenes:
                if o.id in usadas:
                    continue
                dist = abs((o.fecha_programada - ft).days)
                if mejor_dist is None or dist < mejor_dist:
                    mejor, mejor_dist = o, dist
            if mejor is not None:
                usadas.add(mejor.id)
                if mejor.estado in _ESTADOS_COMPLETADA:
                    estatus = "COMPLETADA"
                elif mejor.estado in _ESTADOS_CANCELADA:
                    estatus = "CANCELADA"
                else:
                    estatus = "PROGRAMADA"
                periodos.append({
                    "fecha_tentativa": ft,
                    "estatus": estatus,
                    "orden_id": mejor.id,
                    "orden_folio": mejor.folio_os,
                    "orden_estado": mejor.estado,
                })
            else:
                periodos.append({
                    "fecha_tentativa": ft,
                    "estatus": "SIN_PROGRAMAR",
                    "orden_id": None,
                    "orden_folio": None,
                    "orden_estado": None,
                })

        por_vencer = bool(
            plan.vigencia_hasta and 0 <= (plan.vigencia_hasta - fin_mes).days <= 30
        )

        filas.append({
            "plan_id": plan.id,
            "cliente_id": plan.cliente_id,
            "cliente_nombre": getattr(plan.cliente, "nombre_comercial", None)
            or getattr(plan.cliente, "razon_social", "") or "",
            "servicio_nombre": getattr(plan.servicio, "nombre", None) if plan.servicio else None,
            "tecnico_nombre": getattr(plan.tecnico, "nombre_completo", None)
            or getattr(plan.tecnico, "nombre", None) if plan.tecnico else None,
            "periodicidad": plan.periodicidad,
            "precio_pactado": plan.precio_pactado,
            "por_vencer": por_vencer,
            "vigencia_hasta": plan.vigencia_hasta,
            "periodos": periodos,
        })

    filas.sort(key=lambda r: r["cliente_nombre"].lower())
    return {"anio": anio, "mes": mes, "planes": filas}


# ─── Programar (crear orden desde el plan) ────────────────────────────────────
def _generar_folio_os(db: Session, empresa_id: UUID) -> str:
    count = db.query(OrdenServicio).filter(OrdenServicio.empresa_id == empresa_id).count()
    return f"OS-{count + 1:04d}"


def programar(
    db: Session, plan_id: UUID, req: ProgramarRequest, usuario_id: Optional[UUID] = None
) -> OrdenServicio:
    """Crea una OrdenServicio prellenada a partir del plan."""
    plan = obtener_plan(db, plan_id)

    hora_inicio = None
    if req.hora_inicio:
        try:
            hh, mm = req.hora_inicio.split(":")
            hora_inicio = time(int(hh), int(mm))
        except Exception:
            raise HTTPException(status_code=422, detail="Hora inválida (formato HH:MM).")

    orden = OrdenServicio(
        id=uuid4(),
        empresa_id=plan.empresa_id,
        cliente_id=plan.cliente_id,
        servicio_id=plan.servicio_id,
        tecnico_id=req.tecnico_id or plan.tecnico_id,
        plan_id=plan.id,
        folio_os=_generar_folio_os(db, plan.empresa_id),
        fecha_programada=req.fecha,
        hora_inicio=hora_inicio,
        estado="PENDIENTE",
        prioridad="MEDIA",
        precio_acordado=plan.precio_pactado,
        notas_internas=f"Generada desde el plan de servicio {plan.id}.",
    )
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return orden
