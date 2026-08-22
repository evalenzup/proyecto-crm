"""
Lista los comprobantes a los que se les pidió cancelación y siguen vigentes.

Cruza tres rastros —la bitácora de auditoría, las columnas de cancelación del
propio documento y el acuse sellado del PAC— contra lo que el SAT reporta hoy,
y propone una causa para cada caso.

Causas que distingue:
  · Motivo 01 sin relación válida — el SAT exige que la sustituta declare
    TipoRelacion=04 hacia el UUID que se cancela; si no, rechaza la solicitud.
  · No cancelable — otro comprobante la referencia (típicamente un complemento
    de pago) y el SAT no la libera.
  · Sin acuse del PAC — la solicitud no dejó rastro sellado: o no se transmitió,
    o el PAC no llegó a publicarlo.
  · Rechazada por el receptor.
  · En proceso — todavía puede prosperar.

Uso (dentro del contenedor):
  python scripts/cancelaciones_no_aplicadas.py [--salida /data/auditoria/no_aplicadas.csv]
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models.factura import Factura
from app.models.pago import EstatusPago, Pago
from app.services import acuse_cancelacion_service as acuse_svc
from app.services import sat_cfdi_service as sat_svc

VIGENTES = ("TIMBRADA", "TIMBRADO")

# Antes del commit be183cb2 (2026-06-23) el folio sustituto se enviaba al PAC
# pero no se guardaba en la factura. Para los intentos anteriores a esa fecha,
# que la columna esté vacía NO significa que se haya enviado sin sustituto:
# significa que no quedó registro. No se puede concluir nada de esos casos.
CORTE_FOLIO_SUSTITUTO = "2026-06-23"


def _intentos_por_documento(db) -> dict:
    """{entidad_id: [(fecha, usuario, motivo), ...]} desde auditoria_log."""
    filas = db.execute(text(
        "select entidad_id, creado_en, usuario_email, detalle from auditoria_log "
        "where accion in ('CANCELAR_FACTURA','CANCELAR_PAGO') order by creado_en"
    )).fetchall()
    out = defaultdict(list)
    for eid, cuando, email, detalle in filas:
        motivo = ""
        try:
            motivo = (json.loads(detalle or "{}") or {}).get("motivo") or ""
        except Exception:  # noqa: BLE001
            pass
        out[eid].append((cuando, email, motivo))
    return out


def _relacion_sustituta_ok(db, doc, uuid_sust: str, ultimo_intento=None):
    """(ok, explicación) — replica la validación del motivo 01.

    ok=None significa "no se puede saber", que es distinto de "estaba mal".
    """
    if not uuid_sust:
        anterior_al_corte = (
            ultimo_intento is None
            or ultimo_intento.strftime("%Y-%m-%d") < CORTE_FOLIO_SUSTITUTO
        )
        if anterior_al_corte:
            return None, ("no quedó registro del folio sustituto: el sistema no lo "
                          f"guardaba antes del {CORTE_FOLIO_SUSTITUTO}")
        return False, "el motivo 01 se envió sin folio sustituto"
    sust = (
        db.query(Factura)
        .filter(Factura.cfdi_uuid.ilike(uuid_sust.strip()))
        .first()
    )
    if not sust:
        return None, f"la sustituta {uuid_sust[:8]}… no está en la base"
    etq = f"{sust.serie}-{sust.folio}"
    tipo = (sust.cfdi_relacionados_tipo or "").strip()
    rel = (sust.cfdi_relacionados or "").upper()
    propio = (doc.cfdi_uuid or "").upper()
    if not rel:
        return False, f"la sustituta {etq} no declara ningún CFDI relacionado"
    if tipo != "04":
        return False, f"la sustituta {etq} usa TipoRelacion '{tipo}' en vez de '04'"
    if propio not in rel:
        return False, f"la relación de la sustituta {etq} apunta a otro CFDI"
    return True, f"la sustituta {etq} declara la relación 04 correctamente"


def _tiene_acuse(doc) -> bool:
    try:
        acuse_svc.descargar_acuse_xml(doc, forzar=True)
        return True
    except Exception:  # noqa: BLE001
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="/data/auditoria/cancelaciones_no_aplicadas.csv")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        intentos = _intentos_por_documento(db)

        candidatos = []
        for doc in (
            db.query(Factura).options(joinedload(Factura.empresa), joinedload(Factura.cliente))
            .filter(Factura.estatus.in_(["TIMBRADA"]), Factura.cfdi_uuid.isnot(None)).all()
        ):
            if str(doc.id) in intentos or doc.motivo_cancelacion:
                candidatos.append(doc)
        for doc in (
            db.query(Pago).options(joinedload(Pago.empresa), joinedload(Pago.cliente))
            .filter(Pago.estatus == EstatusPago.TIMBRADO, Pago.uuid.isnot(None)).all()
        ):
            if str(doc.id) in intentos or doc.motivo_cancelacion:
                candidatos.append(doc)

        print(f"Analizando {len(candidatos)} comprobantes con cancelación pedida "
              "que siguen vigentes...\n", flush=True)

        filas = []
        for doc in candidatos:
            es_f = isinstance(doc, Factura)
            uuid_cfdi = (doc.cfdi_uuid if es_f else doc.uuid) or ""
            hist = intentos.get(str(doc.id), [])
            motivo = doc.motivo_cancelacion or (hist[-1][2] if hist else "")

            try:
                e, r, t = sat_svc.datos_consulta(doc)
                acuse = sat_svc.consultar_cfdi(rfc_emisor=e, rfc_receptor=r,
                                               total=t, uuid=uuid_cfdi)
            except Exception as exc:  # noqa: BLE001
                acuse = None

            hay_acuse = _tiene_acuse(doc)

            # ── causa probable ──────────────────────────────────────────────
            causa, detalle_causa = "", ""
            if acuse is None or not acuse.encontrado:
                causa = "No verificable en el SAT"
            elif acuse.cancelado_por_sat:
                causa = "Ya cancelada en el SAT (el sistema no se enteró)"
            elif acuse.en_proceso:
                causa = "En proceso — todavía puede prosperar"
            elif acuse.rechazado_por_receptor:
                causa = "El receptor rechazó la cancelación"
            elif motivo == "01":
                ok, expl = _relacion_sustituta_ok(
                    db, doc, doc.folio_fiscal_sustituto or "",
                    hist[-1][0] if hist else None,
                )
                if ok is False:
                    causa, detalle_causa = "Motivo 01 sin relación válida", expl
                elif ok is None:
                    causa, detalle_causa = (
                        "Motivo 01 — no se puede determinar la causa", expl)
                elif acuse.no_cancelable:
                    causa, detalle_causa = "No cancelable (otro CFDI la referencia)", expl
                else:
                    causa, detalle_causa = (
                        "La solicitud no quedó registrada en el SAT", expl)
            elif acuse.no_cancelable:
                causa = "No cancelable (otro CFDI la referencia)"
            else:
                causa = "La solicitud no quedó registrada en el SAT"

            if not hay_acuse and causa.startswith("La solicitud no"):
                detalle_causa = (detalle_causa + " · sin acuse sellado en el PAC").strip(" ·")

            filas.append({
                "tipo": "Factura" if es_f else "Pago",
                "folio": f"{doc.serie or ''}-{doc.folio}",
                "fecha_emision": (doc.fecha_emision.strftime("%Y-%m-%d")
                                  if doc.fecha_emision else ""),
                "empresa": doc.empresa.nombre_comercial or doc.empresa.nombre,
                "cliente": (doc.cliente.nombre_razon_social
                            or doc.cliente.nombre_comercial or ""),
                "total": f"{float(doc.total if es_f else (doc.monto or 0)):.2f}",
                "intentos": len(hist),
                "primer_intento": hist[0][0].strftime("%Y-%m-%d %H:%M") if hist else "",
                "ultimo_intento": hist[-1][0].strftime("%Y-%m-%d %H:%M") if hist else "",
                "solicito": hist[-1][1] if hist else "",
                "motivo": motivo,
                "folio_sustituto": doc.folio_fiscal_sustituto or "",
                "pac_code": doc.cancelacion_code or "",
                "estado_sat": (acuse.estado if acuse else "?"),
                "es_cancelable": (acuse.es_cancelable if acuse else ""),
                "acuse_en_pac": "sí" if hay_acuse else "no",
                "causa_probable": causa,
                "detalle": detalle_causa,
                "uuid": uuid_cfdi,
            })

        filas.sort(key=lambda f: (f["causa_probable"], f["fecha_emision"]))
        os.makedirs(os.path.dirname(args.salida), exist_ok=True)
        with open(args.salida, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
            w.writeheader(); w.writerows(filas)

        por_causa = defaultdict(list)
        for f in filas:
            por_causa[f["causa_probable"]].append(f)
        for causa, grupo in sorted(por_causa.items(), key=lambda kv: -len(kv[1])):
            print(f"── {causa} ({len(grupo)})")
            for f in grupo:
                print(f"    {f['folio']:10} {f['fecha_emision']}  ${float(f['total']):>10,.2f}  "
                      f"motivo {f['motivo'] or '—':2}  {f['intentos']} intento(s)  "
                      f"{f['empresa'][:20]}")
                if f["detalle"]:
                    print(f"               → {f['detalle']}")
            print()
        print(f"→ {args.salida}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
