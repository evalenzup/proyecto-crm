"""Reglas del rol OPERATIVO — la cuenta de un técnico de campo.

Un técnico entra desde su celular a ver su agenda y a ir avanzando el estado de
sus órdenes. No tiene por qué ver facturación, clientes, cobranza ni reportes,
así que en vez de ir tapando módulo por módulo se hace al revés: se le niega
todo y se abre sólo lo que necesita. Un endpoint nuevo no queda expuesto por
descuido; hay que agregarlo aquí a propósito.

La lista se aplica en deps.get_current_active_user, que es por donde pasan
todos los endpoints protegidos.
"""
from __future__ import annotations

# Prefijos de ruta que puede usar una cuenta de técnico.
# Se comparan contra request.url.path completo (incluye /api).
RUTAS_PERMITIDAS: tuple[str, ...] = (
    # Su agenda y el detalle de sus órdenes; el filtrado por técnico va aparte,
    # en el propio endpoint de listado.
    "/api/ordenes-servicio",
    # Sesión y cuenta propia
    "/api/login",
    "/api/users/me",
    "/api/users/preferences",
    # Avisos
    "/api/notificaciones",
    # Datos de su empresa (logo y nombre en la pantalla)
    "/api/empresas/logos",
    # Salud del servicio
    "/health",
)

# Estados que un técnico puede fijar, y desde cuáles. El flujo es de una sola
# vía: puede avanzar, nunca regresar. Si se equivocó, lo corrige la oficina y
# así el historial refleja lo que de verdad pasó.
#
# CANCELADO no está a propósito: cancelar arrastra consecuencias de facturación
# y cobranza que el técnico no ve. Para eso reporta una incidencia y la oficina
# decide si cancela o reagenda.
TRANSICIONES: dict[str, tuple[str, ...]] = {
    "PENDIENTE":  ("EN_CAMINO",),
    "ASIGNADO":   ("EN_CAMINO",),
    "EN_CAMINO":  ("EN_PROGRESO",),
    "EN_PROGRESO": ("COMPLETADO",),
}


def ruta_permitida(path: str) -> bool:
    path = path.rstrip("/")
    return any(path == p or path.startswith(p + "/") or path.startswith(p + "?")
               for p in RUTAS_PERMITIDAS)


def transicion_permitida(estado_actual: str, estado_nuevo: str) -> bool:
    return estado_nuevo in TRANSICIONES.get(estado_actual, ())


def explicar_transicion(estado_actual: str, estado_nuevo: str) -> str:
    """Mensaje para el técnico cuando el cambio que pide no procede."""
    if estado_nuevo == "CANCELADO":
        return ("No puedes cancelar una orden desde tu cuenta. Si el servicio no "
                "se pudo realizar, repórtalo con el motivo y la oficina decide "
                "si se cancela o se reagenda.")
    permitidos = TRANSICIONES.get(estado_actual)
    if not permitidos:
        return (f"La orden está en «{estado_actual}» y ya no la puedes mover "
                "desde tu cuenta.")
    return (f"Desde «{estado_actual}» sólo puedes pasar a "
            f"«{permitidos[0]}». El estado avanza en un solo sentido; si te "
            "equivocaste, la oficina lo corrige.")
