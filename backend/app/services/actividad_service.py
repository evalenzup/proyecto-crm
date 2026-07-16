# app/services/actividad_service.py
"""
Reporte de actividad del personal a partir de la bitácora de auditoría.

Mide ACCIONES registradas (escrituras) en el sistema — no captura consultas ni
trabajo fuera del sistema. Las marcas de tiempo se guardan en UTC y se convierten
a hora local (America/Tijuana) para el análisis por hora / horario laboral.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time
from typing import Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.auditoria import AuditoriaLog
from app.models.usuario import Usuario
from app.utils.datetime_utils import TIJUANA_TZ

_UTC = ZoneInfo("UTC")

# Etiquetas legibles para las acciones de la bitácora.
ACCION_LABEL: Dict[str, str] = {
    "CREAR_FACTURA": "Facturas creadas",
    "TIMBRAR_FACTURA": "Facturas timbradas",
    "CANCELAR_FACTURA": "Facturas canceladas",
    "ELIMINAR_FACTURA": "Facturas eliminadas",
    "CREAR_PAGO": "Pagos registrados",
    "TIMBRAR_PAGO": "Pagos timbrados",
    "CANCELAR_PAGO": "Pagos cancelados",
    "CREAR_CLIENTE": "Clientes creados",
    "ACTUALIZAR_CLIENTE": "Clientes editados",
    "ELIMINAR_CLIENTE": "Clientes eliminados",
    "CREAR_EMPRESA": "Empresas creadas",
    "ACTUALIZAR_EMPRESA": "Empresas editadas",
    "CREAR_EGRESO": "Egresos creados",
    "ACTUALIZAR_EGRESO": "Egresos editados",
    "ELIMINAR_EGRESO": "Egresos eliminados",
    "CREAR_PRESUPUESTO": "Presupuestos creados",
    "ACTUALIZAR_PRESUPUESTO": "Presupuestos editados",
    "CAMBIAR_ESTADO_PRESUPUESTO": "Cambios de estado (presupuesto)",
    "ELIMINAR_PRESUPUESTO": "Presupuestos eliminados",
    "ENVIAR_PRESUPUESTO": "Presupuestos enviados",
    "CREAR_SERVICIO_OP": "Servicios creados",
    "ACTUALIZAR_SERVICIO_OP": "Servicios editados",
    "ELIMINAR_SERVICIO_OP": "Servicios eliminados",
    "CREAR_TECNICO": "Técnicos creados",
    "ACTUALIZAR_TECNICO": "Técnicos editados",
    "ELIMINAR_TECNICO": "Técnicos eliminados",
    "CREAR_UNIDAD": "Unidades creadas",
    "ACTUALIZAR_UNIDAD": "Unidades editadas",
    "ELIMINAR_UNIDAD": "Unidades eliminadas",
    "CREAR_MANTENIMIENTO": "Mantenimientos creados",
    "ACTUALIZAR_MANTENIMIENTO": "Mantenimientos editados",
    "ELIMINAR_MANTENIMIENTO": "Mantenimientos eliminados",
    "CREAR_POLIZA_SEGURO": "Pólizas creadas",
    "ACTUALIZAR_POLIZA_SEGURO": "Pólizas editadas",
    "ELIMINAR_POLIZA_SEGURO": "Pólizas eliminadas",
    "CREAR_ORDEN_SERVICIO": "Órdenes creadas",
    "ACTUALIZAR_ORDEN_SERVICIO": "Órdenes editadas",
    "CAMBIAR_ESTADO_ORDEN_SERVICIO": "Cambios de estado (orden)",
    "ELIMINAR_ORDEN_SERVICIO": "Órdenes eliminadas",
    "CREAR_CERTIFICADO": "Certificados creados",
    "ACTUALIZAR_CERTIFICADO": "Certificados editados",
    "ELIMINAR_CERTIFICADO": "Certificados eliminados",
    "CREAR_NOTA_COBRANZA": "Notas de cobranza",
    "ELIMINAR_NOTA_COBRANZA": "Notas de cobranza eliminadas",
    "ENVIAR_ESTADO_CUENTA": "Estados de cuenta enviados",
    "CREAR_USUARIO": "Usuarios creados",
    "ACTUALIZAR_USUARIO": "Usuarios editados",
    "ELIMINAR_USUARIO": "Usuarios eliminados",
    "ASIGNAR_EMPRESAS_USUARIO": "Asignación de empresas a usuario",
    "ASIGNAR_PERMISOS_USUARIO": "Asignación de permisos a usuario",
    "CREAR_CONTACTO": "Contactos creados",
    "ACTUALIZAR_CONTACTO": "Contactos editados",
    "ELIMINAR_CONTACTO": "Contactos eliminados",
    "CREAR_PRODUCTO": "Productos creados",
    "ACTUALIZAR_PRODUCTO": "Productos editados",
    "ELIMINAR_PRODUCTO": "Productos eliminados",
    "CREAR_TIPO_EQUIPO": "Tipos de equipo creados",
    "ACTUALIZAR_TIPO_EQUIPO": "Tipos de equipo editados",
    "ELIMINAR_TIPO_EQUIPO": "Tipos de equipo eliminados",
    "CREAR_ESTADO_EQUIPO": "Estados de equipo creados",
    "ACTUALIZAR_ESTADO_EQUIPO": "Estados de equipo editados",
    "ELIMINAR_ESTADO_EQUIPO": "Estados de equipo eliminados",
    "CREAR_EQUIPO": "Equipos creados",
    "ACTUALIZAR_EQUIPO": "Equipos editados",
    "ELIMINAR_EQUIPO": "Equipos eliminados",
    "ALTA_MASIVA_EQUIPOS": "Alta masiva de equipos",
    "CREAR_PROGRAMACION_FACTURA": "Programaciones de factura creadas",
    "ACTUALIZAR_PROGRAMACION_FACTURA": "Programaciones de factura editadas",
    "ELIMINAR_PROGRAMACION_FACTURA": "Programaciones de factura eliminadas",
    "LOGIN": "Inicios de sesión",
    "ENVIAR_FACTURA_EMAIL": "Facturas enviadas por correo",
    "ENVIAR_PAGO_EMAIL": "Pagos enviados por correo",
    "EXPORTAR_EXCEL": "Exportaciones a Excel",
    "VERIFICAR_SAT": "Verificaciones SAT",
    "REVERTIR_CANCELACION": "Reversiones de cancelación",
}


def _label(accion: str) -> str:
    return ACCION_LABEL.get(accion, accion.replace("_", " ").capitalize())


def _bounds_utc(fecha_desde: date, fecha_hasta: date):
    """Límites UTC (naive) para un rango de fechas locales (Tijuana)."""
    ini_local = datetime.combine(fecha_desde, time.min, tzinfo=TIJUANA_TZ)
    fin_local = datetime.combine(fecha_hasta, time.max, tzinfo=TIJUANA_TZ)
    ini_utc = ini_local.astimezone(_UTC).replace(tzinfo=None)
    fin_utc = fin_local.astimezone(_UTC).replace(tzinfo=None)
    return ini_utc, fin_utc


def reporte_actividad(
    db: Session,
    *,
    empresa_id: Optional[UUID],
    usuario_ids: List[UUID],
    fecha_desde: date,
    fecha_hasta: date,
    hora_ini: int = 8,
    hora_fin: int = 18,
) -> dict:
    horas_laborales = max(1, hora_fin - hora_ini)
    ini_utc, fin_utc = _bounds_utc(fecha_desde, fecha_hasta)

    q = db.query(AuditoriaLog).filter(
        AuditoriaLog.usuario_id.in_(usuario_ids),
        AuditoriaLog.creado_en >= ini_utc,
        AuditoriaLog.creado_en <= fin_utc,
    )
    if empresa_id:
        q = q.filter(AuditoriaLog.empresa_id == empresa_id)
    rows = q.all()

    # Nombres de los usuarios elegidos (incluye los que no tengan actividad)
    usuarios = {
        u.id: u
        for u in db.query(Usuario).filter(Usuario.id.in_(usuario_ids)).all()
    }

    # Acumuladores por usuario
    tot: Dict[UUID, int] = defaultdict(int)
    por_tipo: Dict[UUID, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    por_dia: Dict[UUID, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    heat: Dict[UUID, Dict[tuple, int]] = defaultdict(lambda: defaultdict(int))  # (dow, hora)
    horas_activas_por_dia: Dict[UUID, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    primera: Dict[UUID, Dict[str, int]] = defaultdict(dict)  # fecha -> minutos del día
    ultima: Dict[UUID, Dict[str, int]] = defaultdict(dict)
    resultados: Dict[UUID, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for r in rows:
        uid = r.usuario_id
        if uid not in usuarios:
            continue
        local = r.creado_en.replace(tzinfo=_UTC).astimezone(TIJUANA_TZ)
        f = local.strftime("%Y-%m-%d")
        h = local.hour
        dow = local.weekday()  # 0=Lun

        tot[uid] += 1
        por_tipo[uid][r.accion] += 1
        por_dia[uid][f] += 1
        minutos = h * 60 + local.minute
        primera[uid][f] = min(primera[uid].get(f, 10 ** 9), minutos)
        ultima[uid][f] = max(ultima[uid].get(f, -1), minutos)

        if hora_ini <= h < hora_fin:
            heat[uid][(dow, h)] += 1
            horas_activas_por_dia[uid][f].add(h)

        # Resultados (productividad)
        acc = r.accion
        if acc == "TIMBRAR_FACTURA":
            resultados[uid]["facturas_timbradas"] += 1
        elif acc == "CREAR_PAGO":
            resultados[uid]["pagos"] += 1
        elif acc == "CREAR_ORDEN_SERVICIO":
            resultados[uid]["ordenes_creadas"] += 1
        elif acc == "CREAR_CERTIFICADO":
            resultados[uid]["certificados"] += 1
        elif acc == "CREAR_CLIENTE":
            resultados[uid]["clientes"] += 1
        elif acc in ("CREAR_NOTA_COBRANZA", "ENVIAR_ESTADO_CUENTA"):
            resultados[uid]["cobranza"] += 1
        elif acc == "CAMBIAR_ESTADO_ORDEN_SERVICIO":
            try:
                d = json.loads(r.detalle or "{}")
                if str(d.get("estado_nuevo") or d.get("estado") or "").upper() == "COMPLETADO":
                    resultados[uid]["ordenes_completadas"] += 1
            except Exception:
                pass

    dias_rango = (fecha_hasta - fecha_desde).days + 1

    def _hhmm(minutos: Optional[int]) -> Optional[str]:
        if minutos is None:
            return None
        return f"{minutos // 60:02d}:{minutos % 60:02d}"

    salida: List[dict] = []
    for uid in usuario_ids:
        u = usuarios.get(uid)
        if not u:
            continue
        dias_activos = len(por_dia[uid])
        # Cobertura: promedio de (horas laborales con actividad / horas laborales) en días activos
        if dias_activos:
            cob = sum(
                len(horas_activas_por_dia[uid][f]) / horas_laborales
                for f in por_dia[uid]
            ) / dias_activos * 100
        else:
            cob = 0.0
        # Promedios de jornada
        prim = [primera[uid][f] for f in primera[uid]]
        ult = [ultima[uid][f] for f in ultima[uid]]
        accion_top = max(por_tipo[uid].items(), key=lambda kv: kv[1])[0] if por_tipo[uid] else None

        salida.append({
            "usuario_id": str(uid),
            "email": u.email,
            "nombre": u.nombre_completo or u.email,
            "rol": getattr(u.rol, "value", u.rol),
            "total": tot[uid],
            "dias_activos": dias_activos,
            "dias_rango": dias_rango,
            "cobertura_horario": round(cob, 1),
            "primera_accion_prom": _hhmm(round(sum(prim) / len(prim)) if prim else None),
            "ultima_accion_prom": _hhmm(round(sum(ult) / len(ult)) if ult else None),
            "accion_top": _label(accion_top) if accion_top else None,
            "por_tipo": sorted(
                [{"accion": a, "label": _label(a), "total": n} for a, n in por_tipo[uid].items()],
                key=lambda x: x["total"], reverse=True,
            ),
            "por_dia": [{"fecha": f, "total": n} for f, n in sorted(por_dia[uid].items())],
            "heatmap": [{"dow": dow, "hora": h, "total": n} for (dow, h), n in heat[uid].items()],
            "resultados": {
                "facturas_timbradas": resultados[uid].get("facturas_timbradas", 0),
                "pagos": resultados[uid].get("pagos", 0),
                "ordenes_creadas": resultados[uid].get("ordenes_creadas", 0),
                "ordenes_completadas": resultados[uid].get("ordenes_completadas", 0),
                "certificados": resultados[uid].get("certificados", 0),
                "clientes": resultados[uid].get("clientes", 0),
                "cobranza": resultados[uid].get("cobranza", 0),
            },
        })

    # Orden descendente por total (ranking)
    salida.sort(key=lambda x: x["total"], reverse=True)

    return {
        "rango": {
            "desde": fecha_desde.isoformat(),
            "hasta": fecha_hasta.isoformat(),
            "hora_ini": hora_ini,
            "hora_fin": hora_fin,
            "dias_rango": dias_rango,
        },
        "usuarios": salida,
    }
