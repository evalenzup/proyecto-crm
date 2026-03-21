# app/utils/datetime_utils.py
"""
Utilidades de timezone para el proyecto.

Convención:
  - La BD guarda datetimes en UTC naive (sin tzinfo).
  - Internamente se usa datetime.now(timezone.utc) en lugar del deprecated utcnow().
  - En las respuestas API se serializa a America/Tijuana mediante TijuanaDatetime.
  - En PDFs ya existe _to_tijuana() en pdf_factura.py que usa esta misma lógica.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from pydantic import PlainSerializer

TIJUANA_TZ = ZoneInfo("America/Tijuana")
UTC_TZ = timezone.utc


def utc_now() -> datetime:
    """
    Reemplazo seguro de datetime.utcnow() (deprecated en Python 3.12+).
    Devuelve un datetime aware en UTC.
    El ORM lo almacena como UTC naive — SQLAlchemy descarta el tzinfo al persistir.
    """
    return datetime.now(UTC_TZ)


def to_tijuana(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convierte un datetime (naive UTC o aware) a America/Tijuana.
    Devuelve None si la entrada es None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(TIJUANA_TZ)


def _tijuana_serializer(dt: Optional[datetime]) -> Optional[str]:
    """Serializador Pydantic: convierte datetime → ISO 8601 en hora de Tijuana."""
    if dt is None:
        return None
    tj = to_tijuana(dt)
    return tj.isoformat()


# Tipo anotado para usar en schemas de respuesta (Out).
# - Parsing (entrada): se comporta como datetime normal.
# - Serialización JSON (salida API): convierte a string ISO 8601 en Tijuana.
TijuanaDatetime = Annotated[
    datetime,
    PlainSerializer(_tijuana_serializer, return_type=str, when_used="json"),
]
