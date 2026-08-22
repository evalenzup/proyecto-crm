"""
Siembra la bitácora de cancelaciones con los comprobantes que ya estaban
EN_CANCELACION cuando se creó la tabla.

La bitácora sólo escribe en el momento del envío, así que los trámites abiertos
de antes quedarían invisibles en ella y el cron no tendría qué cerrar cuando el
SAT resuelva. Este script reconstruye un renglón por documento a partir de lo
que sus propias columnas conservan (fecha de solicitud, motivo, folio sustituto,
código y mensaje del PAC, acuse).

Lo que NO se puede reconstruir se deja en nulo a propósito: los campos sat_*
describen lo que el SAT contestaba en el instante del envío, y eso nadie lo
observó. Por eso los renglones quedan marcados con origen=RECONSTRUIDO.

Uso (dentro del contenedor):
  docker exec <backend> python scripts/backfill_bitacora_cancelacion.py [--aplicar]

Sin --aplicar sólo muestra lo que haría.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.cancelacion_intento import RECONSTRUIDO, CancelacionIntento
from app.models.factura import Factura
from app.models.pago import EstatusPago, Pago
from app.services import cancelacion_intento_service as bitacora
from app.services.timbrado_factmoderna import CODIGOS_SOLICITUD_ACEPTADA


def _ya_registrado(db, doc) -> bool:
    tipo, _uuid, _etq = bitacora._datos_documento(doc)
    return (
        db.query(CancelacionIntento)
        .filter(
            CancelacionIntento.documento_tipo == tipo,
            CancelacionIntento.documento_id == doc.id,
        )
        .count()
        > 0
    )


def main(aplicar: bool) -> None:
    db = SessionLocal()
    try:
        pendientes = list(
            db.query(Factura)
            .filter(Factura.estatus == "EN_CANCELACION", Factura.cfdi_uuid.isnot(None))
            .all()
        ) + list(
            db.query(Pago)
            .filter(Pago.estatus == EstatusPago.EN_CANCELACION, Pago.uuid.isnot(None))
            .all()
        )

        creados = 0
        for doc in pendientes:
            if _ya_registrado(db, doc):
                print(f"  = {doc.serie}-{doc.folio}: ya tiene renglón en la bitácora")
                continue

            code = getattr(doc, "cancelacion_code", None)
            conocido = (
                (code or "").strip().upper() in CODIGOS_SOLICITUD_ACEPTADA
                if code
                else None
            )
            print(
                f"  + {doc.serie}-{doc.folio}: envío {doc.fecha_solicitud_cancelacion}, "
                f"PAC={code or '—'}, acuse={'sí' if getattr(doc, 'cancelacion_acuse_path', None) else 'no'}"
            )
            if not aplicar:
                creados += 1
                continue

            intento = bitacora.registrar(
                db, doc,
                motivo=getattr(doc, "motivo_cancelacion", None),
                folio_sustitucion=getattr(doc, "folio_fiscal_sustituto", None),
                pac_code=code,
                pac_message=getattr(doc, "cancelacion_message", None),
                pac_codigo_conocido=conocido,
                acuse_sat=None,           # nadie observó al SAT en ese momento
                sat_registro_solicitud=None,
                origen=RECONSTRUIDO,
                fecha_envio=doc.fecha_solicitud_cancelacion,
            )
            if intento is not None:
                intento.acuse_path = getattr(doc, "cancelacion_acuse_path", None)
                db.add(intento)
                creados += 1

        if aplicar:
            db.commit()
            print(f"\n{creados} renglón(es) creado(s).")
        else:
            print(f"\n[dry-run] se crearían {creados} renglón(es). Usa --aplicar.")
    finally:
        db.close()


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
