"""Reglas del rol OPERATIVO — la cuenta de un técnico de campo.

Un técnico entra desde su celular a ver su agenda y a ir avanzando el estado de
sus órdenes. No tiene por qué ver facturación, clientes, cobranza ni reportes,
así que en vez de ir tapando módulo por módulo se hace al revés: se le niega
todo y se abre sólo lo que necesita.

La lista distingue el MÉTODO, no sólo la ruta. Filtrar por prefijo dejaba
abierto todo /api/ordenes-servicio, y una prueba de intrusión lo confirmó: con
la cuenta de un técnico se podía leer y editar cualquier orden —incluidas las
de otra empresa— y crear órdenes nuevas. Sólo el listado estaba protegido.

Las reglas se aplican en deps.get_current_active_user; la pertenencia de cada
orden se verifica además en el propio endpoint.
"""
from __future__ import annotations

import re

# (métodos permitidos, patrón de la ruta). El patrón se ancla completo.
_UUID = r"[0-9a-fA-F-]{36}"

REGLAS: tuple[tuple[frozenset[str], re.Pattern], ...] = (
    # Su agenda y el detalle de una orden suya (la pertenencia se revisa aparte)
    (frozenset({"GET"}),   re.compile(r"/api/ordenes-servicio/?")),
    (frozenset({"GET"}),   re.compile(rf"/api/ordenes-servicio/{_UUID}")),
    # Avanzar el estado y reportar que no se pudo realizar
    (frozenset({"PATCH"}), re.compile(rf"/api/ordenes-servicio/{_UUID}/estado")),
    (frozenset({"POST"}),  re.compile(rf"/api/ordenes-servicio/{_UUID}/incidencia")),
    # Sesión y cuenta propia
    (frozenset({"POST"}),  re.compile(r"/api/login/[\w-]+")),
    (frozenset({"GET", "PUT"}), re.compile(r"/api/users/(me|preferences)(/password)?")),
    # Avisos
    (frozenset({"GET", "PATCH", "POST"}), re.compile(r"/api/notificaciones(/.*)?")),
    # Logo de su empresa
    (frozenset({"GET"}),   re.compile(r"/api/empresas/logos/.*")),
    # Salud del servicio
    (frozenset({"GET"}),   re.compile(r"/health(/.*)?")),
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


def peticion_permitida(metodo: str, path: str) -> bool:
    path = path.rstrip("/") or "/"
    for metodos, patron in REGLAS:
        if metodo in metodos and patron.fullmatch(path):
            return True
    return False


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
