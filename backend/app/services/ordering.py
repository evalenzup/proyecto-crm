# app/services/ordering.py
"""Helper para aplicar ordenamiento dinámico y seguro a queries de listados."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import asc, desc


def apply_order(query, model, order_by: Optional[str], order_dir: Optional[str],
                allowed: Iterable[str], default: str):
    """Ordena `query` por `order_by` (validado contra `allowed`) en dirección
    `order_dir` ('asc'|'desc'). Si `order_by` no está permitido, usa `default`.
    """
    allowed_set = set(allowed)
    col_name = order_by if (order_by in allowed_set) else default
    col = getattr(model, col_name, None)
    if col is None:
        col = getattr(model, default)
    dir_fn = desc if (order_dir or "asc").lower() == "desc" else asc
    return query.order_by(dir_fn(col))
