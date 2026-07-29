"""
Backfill del snapshot del CFDI (RFC emisor / RFC receptor / Total) leyendo el
XML timbrado de cada factura y complemento de pago.

Sin estos datos, la consulta al SAT usa los valores actuales de la BD, que
cambian (cliente que cambia de RFC, total recalculado) y hacen fallar la
consulta con "601: la expresión impresa no es válida".

Uso (dentro del contenedor):
  docker exec <backend> python scripts/backfill_snapshot_cfdi.py [--dry-run]
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal

from app.config import settings
from app.database import SessionLocal
from app.models.factura import Factura
from app.models.pago import Pago
from app.services.sat_cfdi_service import extraer_datos_cfdi


def _ruta_xml(xml_path: str | None) -> str | None:
    if not xml_path:
        return None
    if os.path.isabs(xml_path) and os.path.isfile(xml_path):
        return xml_path
    candidato = os.path.join(settings.DATA_DIR, xml_path)
    if os.path.isfile(candidato):
        return candidato
    # Algunos registros guardan sólo el nombre del archivo
    base = os.path.basename(xml_path)
    for raiz in (os.path.join(settings.DATA_DIR, "cfdi"), settings.DATA_DIR):
        candidato = os.path.join(raiz, base)
        if os.path.isfile(candidato):
            return candidato
    return None


def _procesar(db, modelo, etiqueta: str, dry_run: bool) -> tuple[int, int, int]:
    docs = (
        db.query(modelo)
        .filter(modelo.cfdi_rfc_receptor.is_(None))
        .filter(modelo.xml_path.isnot(None))
        .all()
    )
    print(f"{etiqueta}: {len(docs)} sin snapshot con XML registrado")

    ok = sin_archivo = sin_datos = 0
    for d in docs:
        ruta = _ruta_xml(d.xml_path)
        if not ruta:
            sin_archivo += 1
            continue
        try:
            with open(ruta, "rb") as fh:
                datos = extraer_datos_cfdi(fh.read())
        except Exception:
            sin_archivo += 1
            continue

        if not datos.get("rfc_receptor"):
            sin_datos += 1
            continue

        d.cfdi_rfc_emisor = datos.get("rfc_emisor")
        d.cfdi_rfc_receptor = datos.get("rfc_receptor")
        if datos.get("total") is not None:
            d.cfdi_total = Decimal(str(datos["total"]))
        db.add(d)
        ok += 1

    return ok, sin_archivo, sin_datos


def run(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        f_ok, f_na, f_nd = _procesar(db, Factura, "Facturas", dry_run)
        p_ok, p_na, p_nd = _procesar(db, Pago, "Pagos", dry_run)

        if dry_run:
            db.rollback()
            print(f"[DRY-RUN] Se llenarían: {f_ok} facturas, {p_ok} pagos. Nada guardado.")
        else:
            db.commit()
            print(f"OK: {f_ok} facturas y {p_ok} pagos con snapshot.")
        print(f"  Sin XML en disco: {f_na} facturas, {p_na} pagos")
        print(f"  XML sin datos legibles: {f_nd} facturas, {p_nd} pagos")
    finally:
        db.close()


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
