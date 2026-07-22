"""
Traducción de errores del PAC / validaciones locales a mensajes para el usuario.

Fuente única de verdad para los 4 flujos que hablan con el PAC (timbrado y
cancelación, de facturas y de complementos de pago). Antes cada uno tenía su
propia versión: algunos extraían el <faultstring> y otros volcaban el XML SOAP
completo en pantalla, o devolvían un 502 que la UI traducía a "no se pudo
contactar al servidor".
"""
import re
from typing import Tuple

from app.core.logger import logger

# Marcas que delatan que el texto es una respuesta del PAC y no un mensaje nuestro
_MARCAS_SOAP = ("<", "soap", "envelope", "http/")

_GENERICO = (
    "El PAC no pudo procesar la solicitud y devolvió una respuesta que no se "
    "pudo interpretar. Intenta de nuevo; si continúa, reporta a soporte."
)


def interpretar_error_pac(exc: Exception | str) -> Tuple[int, str]:
    """
    Devuelve ``(status_code, mensaje)`` legible para el usuario.

    Orden de preferencia:
      1. <faultstring> del SOAP — es el mensaje real del PAC/SAT.
      2. Formato "PAC devolvió Fault: <code> <mensaje>".
      3. Etiquetas de mensaje comunes (<message>, <mensaje>).
      4. Validación local nuestra (texto sin marcas de SOAP) — se devuelve tal cual.
      5. Respuesta del PAC no interpretable — mensaje genérico; el XML completo
         queda en el log, nunca en la pantalla del usuario.
    """
    msg = str(exc)

    m = re.search(r"<faultstring>(.*?)</faultstring>", msg, flags=re.IGNORECASE | re.DOTALL)
    if m and m.group(1).strip():
        return 400, m.group(1).strip()

    m = re.search(r"PAC devolvió Fault:\s*\S*\s*(.+)$", msg, flags=re.IGNORECASE | re.DOTALL)
    if m and m.group(1).strip():
        return 400, m.group(1).strip()

    m = re.search(r"<(?:message|mensaje)>(.*?)</(?:message|mensaje)>", msg, flags=re.IGNORECASE | re.DOTALL)
    if m and m.group(1).strip():
        return 400, m.group(1).strip()

    # Validación local (nunca se contactó al PAC): el mensaje ya es para el usuario.
    if not any(k in msg.lower() for k in _MARCAS_SOAP):
        return 400, msg

    logger.warning("Respuesta del PAC no interpretable: %s", msg[:4000])
    return 502, _GENERICO
