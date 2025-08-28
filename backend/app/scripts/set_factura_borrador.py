# app/scripts/set_factura_borrador.py
from __future__ import annotations

import sys
from uuid import UUID
from contextlib import closing

from sqlalchemy.orm import Session

# 🔧 IMPORTA los modelos que participan en relaciones
# para que el registry conozca todas las clases.
# (No borres estos imports aunque "no se usen" directamente)
import app.models.empresa          # noqa: F401
import app.models.cliente          # noqa: F401
import app.models.factura_detalle  # noqa: F401
import app.models.factura          # noqa: F401

# Fuerza a SQLAlchemy a configurar mapeos ahora (evita el error de 'FacturaDetalle' no encontrada)
try:
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
except Exception:
    pass

# Obtén la sesión (compat con tus proyectos)
try:
    from app.database import SessionLocal  # type: ignore
    def _open_session() -> Session:
        return SessionLocal()
except Exception:  # pragma: no cover
    from app.database import get_db  # type: ignore
    def _open_session() -> Session:
        return next(get_db())

from app.models.factura import Factura


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: python -m app.scripts.set_factura_borrador <FACTURA_ID> [--force]")
        return 1

    try:
        factura_id = UUID(argv[1])
    except Exception:
        print("ERROR: FACTURA_ID inválido (debe ser UUID).")
        return 1

    force = "--force" in argv[2:]

    with closing(_open_session()) as db:
        f: Factura | None = db.query(Factura).filter(Factura.id == factura_id).first()
        if not f:
            print("ERROR: Factura no encontrada.")
            return 2

        if getattr(f, "cfdi_uuid", None) and not force:
            print("ERROR: La factura ya está timbrada (tiene UUID). Usa --force para forzar el cambio de estatus.")
            return 3

        prev = getattr(f, "estatus", None)
        f.estatus = "BORRADOR"
        f.cfdi_uuid = None
        f.fecha_timbrado = None
        db.add(f)
        db.commit()
        db.refresh(f)

        print(f"OK: {f.id} estatus {prev!r} -> {f.estatus!r}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))