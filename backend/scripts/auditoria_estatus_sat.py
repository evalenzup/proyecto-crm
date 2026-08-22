"""
Auditoría de estatus: compara lo que el sistema cree con lo que el SAT reporta,
para todas las facturas y complementos timbrados de todas las empresas.

SÓLO LEE. No modifica ningún estatus ni escribe en la bitácora: el objetivo es
ver el panorama, no reconciliarlo. Las diferencias se reportan para que la
decisión de corregir sea explícita.

Uso (dentro del contenedor):
  python scripts/auditoria_estatus_sat.py [--salida /data/auditoria/estatus.csv]
                                          [--hilos 3] [--limite N]
"""
import argparse
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models.factura import Factura
from app.models.pago import Pago
from app.services import sat_cfdi_service as sat_svc

# Qué estado del SAT corresponde a cada estatus nuestro.
EQUIVALENCIAS = {
    "TIMBRADA": "vigente", "TIMBRADO": "vigente",
    "CANCELADA": "cancelado", "CANCELADO": "cancelado",
    "EN_CANCELACION": "en_proceso",
}


def _clasificar_sat(acuse) -> str:
    if not acuse.encontrado:
        return "no_verificable"
    if acuse.cancelado_por_sat:
        return "cancelado"
    if acuse.en_proceso:
        return "en_proceso"
    return "vigente"


def _texto_sat(acuse) -> str:
    if not acuse.encontrado:
        return f"No verificable ({acuse.codigo_estatus})"
    extra = (acuse.estatus_cancelacion or "").strip()
    return f"{acuse.estado} ({extra})" if extra else acuse.estado


def _consultar(doc):
    """Devuelve el renglón del reporte. Nunca lanza."""
    es_factura = isinstance(doc, Factura)
    uuid_cfdi = (doc.cfdi_uuid if es_factura else doc.uuid) or ""
    estatus = getattr(doc.estatus, "value", doc.estatus)
    fecha = (
        (doc.fecha_emision or doc.fecha_timbrado) if es_factura
        else (doc.fecha_emision or doc.fecha_pago)
    )
    base = {
        "tipo": "Factura" if es_factura else "Complemento de pago",
        "fecha": fecha.strftime("%Y-%m-%d") if fecha else "",
        "folio": f"{doc.serie or ''}-{doc.folio}",
        "empresa": getattr(doc.empresa, "nombre_comercial", None)
        or getattr(doc.empresa, "nombre", "") or "",
        "cliente": getattr(doc.cliente, "nombre_razon_social", None)
        or getattr(doc.cliente, "nombre_comercial", "") or "",
        "estado_sistema": estatus,
        "uuid": uuid_cfdi,
    }
    try:
        rfc_e, rfc_r, total = sat_svc.datos_consulta(doc)
        acuse = sat_svc.consultar_cfdi(
            rfc_emisor=rfc_e, rfc_receptor=rfc_r, total=total, uuid=uuid_cfdi
        )
    except Exception as exc:  # noqa: BLE001
        return {**base, "estado_sat": f"ERROR: {exc}", "coincide": "?",
                "es_cancelable": "", "estatus_cancelacion": ""}

    clase_sat = _clasificar_sat(acuse)
    esperado = EQUIVALENCIAS.get(estatus)
    if clase_sat == "no_verificable":
        coincide = "?"
    else:
        coincide = "sí" if clase_sat == esperado else "NO"

    return {
        **base,
        "estado_sat": _texto_sat(acuse),
        "coincide": coincide,
        "es_cancelable": acuse.es_cancelable,
        "estatus_cancelacion": acuse.estatus_cancelacion,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="/data/auditoria/estatus_sat.csv")
    ap.add_argument("--hilos", type=int, default=3)
    ap.add_argument("--limite", type=int, default=0)
    args = ap.parse_args()

    db = SessionLocal()
    try:
        facturas = (
            db.query(Factura)
            .options(joinedload(Factura.empresa), joinedload(Factura.cliente))
            .filter(Factura.cfdi_uuid.isnot(None))
            .order_by(Factura.fecha_emision)
            .all()
        )
        pagos = (
            db.query(Pago)
            .options(joinedload(Pago.empresa), joinedload(Pago.cliente))
            .filter(Pago.uuid.isnot(None))
            .order_by(Pago.fecha_pago)
            .all()
        )
        docs = facturas + pagos
        if args.limite:
            docs = docs[: args.limite]

        print(f"Consultando al SAT {len(docs)} comprobantes "
              f"({len(facturas)} facturas + {len(pagos)} pagos)...", flush=True)

        t0 = time.time()
        filas = []
        with ThreadPoolExecutor(max_workers=args.hilos) as pool:
            for i, fila in enumerate(pool.map(_consultar, docs), 1):
                filas.append(fila)
                if i % 200 == 0:
                    print(f"  {i}/{len(docs)} — {time.time() - t0:.0f}s", flush=True)

        os.makedirs(os.path.dirname(args.salida), exist_ok=True)
        columnas = ["tipo", "fecha", "folio", "empresa", "cliente",
                    "estado_sistema", "estado_sat", "coincide",
                    "es_cancelable", "estatus_cancelacion", "uuid"]
        with open(args.salida, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=columnas)
            w.writeheader()
            w.writerows(filas)

        difs = [f for f in filas if f["coincide"] == "NO"]
        dudas = [f for f in filas if f["coincide"] == "?"]
        print(f"\nTerminado en {time.time() - t0:.0f}s → {args.salida}")
        print(f"  coinciden      : {sum(1 for f in filas if f['coincide'] == 'sí')}")
        print(f"  DISCREPANCIAS  : {len(difs)}")
        print(f"  no verificables: {len(dudas)}")
        for f in difs:
            print(f"    ! {f['tipo'][:8]:8} {f['folio']:10} {f['empresa'][:22]:22} "
                  f"sistema={f['estado_sistema']:15} sat={f['estado_sat']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
