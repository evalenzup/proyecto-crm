# app/utils/cache.py
"""
Caché en memoria con TTL para reducir queries repetidas.
Sin dependencias externas (no Redis). Adecuado para entornos de un solo proceso.
"""
import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple

_store: Dict[str, Tuple[Any, float]] = {}
_lock = Lock()


def cache_get(key: str) -> Optional[Any]:
    """Retorna el valor cacheado si no ha expirado, o None."""
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() < expiry:
            return value
        del _store[key]
        return None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Guarda un valor con tiempo de vida en segundos."""
    with _lock:
        _store[key] = (value, time.monotonic() + ttl)


def cache_invalidate_prefix(prefix: str) -> None:
    """Elimina todas las claves que empiecen con `prefix`."""
    with _lock:
        keys_to_delete = [k for k in _store if k.startswith(prefix)]
        for k in keys_to_delete:
            del _store[k]
