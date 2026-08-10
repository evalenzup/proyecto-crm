"""Restricciones de acceso por usuario: horario, origen de red y borrado.

Sirven para acotar a un usuario sin bajarle el rol. Todas son opcionales: un
usuario sin nada configurado se comporta exactamente como antes.

Las tres se evalúan en `deps.get_current_active_user`, que es la dependencia
por la que pasan los 231 endpoints protegidos, y también al iniciar sesión
para que el usuario reciba el motivo en vez de fallar después en cada pantalla.
"""
from __future__ import annotations

import ipaddress
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("app")

TZ_MX = ZoneInfo("America/Mexico_City")

_DIAS = {1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves",
         5: "viernes", 6: "sábado", 7: "domingo"}


def _ahora_mx() -> datetime:
    return datetime.now(TZ_MX)


def motivo_horario(usuario, ahora: Optional[datetime] = None) -> Optional[str]:
    """Devuelve el motivo del rechazo, o None si el momento está permitido."""
    inicio, fin = usuario.horario_inicio, usuario.horario_fin
    dias = (usuario.dias_laborales or "").strip()
    if not inicio and not fin and not dias:
        return None

    ahora = ahora or _ahora_mx()

    if dias:
        try:
            permitidos = {int(d) for d in dias.split(",") if d.strip()}
        except ValueError:
            logger.warning("[Restricciones] dias_laborales inválido en %s: %r",
                           usuario.email, dias)
            permitidos = set()
        if permitidos and ahora.isoweekday() not in permitidos:
            legibles = ", ".join(_DIAS[d] for d in sorted(permitidos) if d in _DIAS)
            return f"Tu cuenta solo tiene acceso los días: {legibles}."

    if inicio and fin:
        hora = ahora.time()
        # Si el fin es menor que el inicio, el horario cruza la medianoche.
        dentro = (inicio <= hora <= fin) if inicio <= fin else (hora >= inicio or hora <= fin)
        if not dentro:
            return (f"Tu cuenta solo tiene acceso de {inicio.strftime('%H:%M')} "
                    f"a {fin.strftime('%H:%M')} (hora del centro). "
                    f"Ahora son las {hora.strftime('%H:%M')}.")

    return None


def ip_permitida(usuario, ip: Optional[str]) -> bool:
    """True si la IP viene de un origen autorizado (o si no hay restricción)."""
    permitidas = (usuario.ips_permitidas or "").strip()
    if not permitidas:
        return True
    if not ip:
        # Sin IP no se puede comprobar el origen; con restricción activa se niega.
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for entrada in permitidas.split(","):
        entrada = entrada.strip()
        if not entrada:
            continue
        try:
            if addr in ipaddress.ip_network(entrada, strict=False):
                return True
        except ValueError:
            logger.warning("[Restricciones] entrada de IP inválida en %s: %r",
                           usuario.email, entrada)
    return False


def motivo_red(usuario, ip: Optional[str]) -> Optional[str]:
    if ip_permitida(usuario, ip):
        return None
    return ("Tu cuenta solo puede usarse desde la red de las instalaciones. "
            f"Estás conectando desde {ip or 'un origen no identificado'}.")


def ip_del_request(request) -> Optional[str]:
    """IP real del cliente.

    uvicorn corre con --proxy-headers, así que request.client.host ya trae la
    del extremo y no la del proxy. Se conserva la lectura directa de
    X-Forwarded-For como respaldo por si esa bandera cambiara.
    """
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return getattr(getattr(request, "client", None), "host", None)


def verificar_acceso(usuario, request) -> Optional[str]:
    """Motivo por el que el usuario no puede operar ahora, o None si sí puede."""
    return motivo_red(usuario, ip_del_request(request)) or motivo_horario(usuario)
