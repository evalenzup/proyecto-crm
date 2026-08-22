"""
Aplica «Verificar con SAT» a una lista de comprobantes identificados por UUID.

Usa exactamente la misma lógica que el botón de la pantalla y que el cron
(`sat_cfdi_service.aplicar_acuse_sat`), así que el resultado es idéntico a
hacerlo a mano uno por uno. Deja rastro en auditoria_log y cierra el intento
abierto en la bitácora, si lo hubiera.

NO toca status_pago ni fecha_cobro: el botón tampoco lo hace, y decidir si una
factura cancelada deja de contar como cobrada es una decisión contable aparte.

Uso (dentro del contenedor):
  python scripts/corregir_discrepancias_sat.py UUID [UUID...] [--aplicar]

Sin --aplicar sólo muestra qué cambiaría.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.factura import Factura
from app.models.pago import Pago
from app.services import auditoria_service as aud
from app.services import cancelacion_intento_service as bitacora_svc
from app.services import sat_cfdi_service as sat_svc

ORIGEN = "correccion-discrepancias-sat"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    aplicar = "--aplicar" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)

    db = SessionLocal()
    cambios = 0
    try:
        for clave in args:
            doc = db.query(Factura).filter(Factura.cfdi_uuid.ilike(clave)).first()
            if doc is None:
                doc = db.query(Pago).filter(Pago.uuid.ilike(clave)).first()
            if doc is None:
                print(f"  ✗ {clave}: no encontrado")
                continue

            es_factura = isinstance(doc, Factura)
            etiqueta = f"{doc.serie or ''}-{doc.folio}"
            uuid_cfdi = doc.cfdi_uuid if es_factura else doc.uuid

            try:
                e, r, t = sat_svc.datos_consulta(doc)
                acuse = sat_svc.consultar_cfdi(
                    rfc_emisor=e, rfc_receptor=r, total=t, uuid=uuid_cfdi
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ {etiqueta}: no se pudo consultar el SAT ({exc})")
                continue

            if not acuse.encontrado:
                print(f"  ✗ {etiqueta}: el SAT no lo reconoce ({acuse.codigo_estatus})")
                continue

            anterior = getattr(doc.estatus, "value", doc.estatus)
            aplicar_fn = (
                sat_svc.aplicar_acuse_sat if es_factura else sat_svc.aplicar_acuse_sat_pago
            )
            nuevo, hubo_cambio = aplicar_fn(doc, acuse)

            flecha = f"{anterior} → {nuevo}" if hubo_cambio else f"{anterior} (sin cambio)"
            sat_txt = acuse.estado + (
                f" / {acuse.estatus_cancelacion}" if acuse.estatus_cancelacion else ""
            )
            print(f"  {'✓' if hubo_cambio else '='} {etiqueta:10} {flecha:32} SAT: {sat_txt}")

            if not hubo_cambio:
                db.rollback()
                continue
            cambios += 1

            if not aplicar:
                db.rollback()
                continue

            db.add(doc)
            bitacora_svc.cerrar_si_resuelto(db, doc, anterior, nuevo)
            aud.registrar(
                db,
                accion=aud.VERIFICAR_SAT,
                entidad="Factura" if es_factura else "pago",
                usuario_email=ORIGEN,
                empresa_id=doc.empresa_id,
                entidad_id=str(doc.id),
                detalle={
                    "cfdi_uuid": uuid_cfdi,
                    "estatus_anterior": anterior,
                    "estatus_nuevo": nuevo,
                    "sat_estado": acuse.estado,
                    "sat_estatus_cancelacion": acuse.estatus_cancelacion,
                    "sat_es_cancelable": acuse.es_cancelable,
                    "origen": ORIGEN,
                },
            )
            db.commit()

        print()
        if aplicar:
            print(f"{cambios} comprobante(s) corregido(s).")
        else:
            print(f"[dry-run] cambiarían {cambios}. Agrega --aplicar para escribir.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
