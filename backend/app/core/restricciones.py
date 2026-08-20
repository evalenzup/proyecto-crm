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
from datetime import datetime, time, timedelta
from typing import NamedTuple, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("app")

TZ_MX = ZoneInfo("America/Mexico_City")

_DIAS = {1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves",
         5: "viernes", 6: "sábado", 7: "domingo"}


class Bloqueo(NamedTuple):
    """Motivo legible del rechazo y el tipo de restricción que lo produjo."""
    motivo: str
    tipo: str          # "horario" | "red" | "eliminar" | "exportar"


# Una pestaña abierta reintenta cada minuto, así que sin control se llenaban
# el log y la auditoría con la misma línea toda la noche. Se avisa una vez por
# usuario y tipo dentro de esta ventana; los reintentos siguen recibiendo 403.
MINUTOS_ENTRE_AVISOS = 15
_ULTIMO_AVISO: dict[tuple, datetime] = {}


def debe_avisar(usuario_id, tipo: str) -> bool:
    """True si toca dejar constancia de este bloqueo (log y auditoría)."""
    ahora = _ahora_mx()
    corte = ahora - timedelta(minutes=MINUTOS_ENTRE_AVISOS)

    # Poda para que el diccionario no crezca sin límite en procesos largos.
    if len(_ULTIMO_AVISO) > 500:
        for k in [k for k, v in _ULTIMO_AVISO.items() if v < corte]:
            _ULTIMO_AVISO.pop(k, None)

    clave = (str(usuario_id), tipo)
    if _ULTIMO_AVISO.get(clave, datetime.min.replace(tzinfo=TZ_MX)) > corte:
        return False
    _ULTIMO_AVISO[clave] = ahora
    return True


def _ahora_mx() -> datetime:
    return datetime.now(TZ_MX)


def _hora(texto: str) -> Optional[time]:
    """Convierte "HH:MM" o "HH:MM:SS" a time; None si no se puede."""
    try:
        partes = [int(p) for p in str(texto).split(":")[:2]]
        return time(partes[0], partes[1] if len(partes) > 1 else 0)
    except (ValueError, IndexError):
        return None


def _dentro_del_rango(hora: time, inicio: time, fin: time) -> bool:
    # Si el fin es menor que el inicio, el horario cruza la medianoche.
    return (inicio <= hora <= fin) if inicio <= fin else (hora >= inicio or hora <= fin)


def motivo_horario_semanal(usuario, ahora: datetime) -> Optional[str]:
    """Evalúa el horario por día. Devuelve el motivo del rechazo, o None."""
    mapa = usuario.horario_semanal or {}
    if not mapa:
        return None

    dia = str(ahora.isoweekday())
    rango = mapa.get(dia)
    if not rango:
        dias_con_acceso = sorted(int(d) for d in mapa if str(d).isdigit())
        legibles = ", ".join(_DIAS[d] for d in dias_con_acceso if d in _DIAS)
        return f"Tu cuenta solo tiene acceso los días: {legibles}."

    inicio, fin = _hora(rango[0]), _hora(rango[1] if len(rango) > 1 else None)
    if not inicio or not fin:
        logger.warning("[Restricciones] horario_semanal inválido en %s: %r",
                       usuario.email, rango)
        return None

    hora = ahora.time()
    if not _dentro_del_rango(hora, inicio, fin):
        return (f"Hoy {_DIAS[ahora.isoweekday()]} tu cuenta tiene acceso de "
                f"{inicio.strftime('%H:%M')} a {fin.strftime('%H:%M')} "
                f"(hora del centro). Ahora son las {hora.strftime('%H:%M')}.")
    return None


def motivo_horario(usuario, ahora: Optional[datetime] = None) -> Optional[str]:
    """Devuelve el motivo del rechazo, o None si el momento está permitido."""
    ahora = ahora or _ahora_mx()

    # El horario por día, si está configurado, sustituye al horario único.
    if getattr(usuario, "horario_semanal", None):
        return motivo_horario_semanal(usuario, ahora)

    inicio, fin = usuario.horario_inicio, usuario.horario_fin
    dias = (usuario.dias_laborales or "").strip()
    if not inicio and not fin and not dias:
        return None

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
        if not _dentro_del_rango(hora, inicio, fin):
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


def verificar_acceso(usuario, request) -> Optional[Bloqueo]:
    """Bloqueo que impide operar ahora, o None si el usuario sí puede."""
    motivo = motivo_red(usuario, ip_del_request(request))
    if motivo:
        return Bloqueo(motivo, "red")
    motivo = motivo_horario(usuario)
    if motivo:
        return Bloqueo(motivo, "horario")
    return None
