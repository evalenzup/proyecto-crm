"""
Diagnóstico de un comprobante cuyo estatus no coincide con el SAT.

Reúne en un solo lugar las cinco fuentes que hay que cruzar a mano para
entender qué pasó con una cancelación:

  1. El estatus y las columnas de cancelación del propio documento.
  2. Lo que el SAT reporta hoy (Estado, EsCancelable, EstatusCancelacion).
  3. La regla de los $1,000: por debajo de ese monto el SAT cancela sin pedir
     la aceptación del receptor, y por encima espera tres días hábiles.
  4. El rastro en la bitácora de auditoría: quién pidió qué y cuándo.
  5. El acuse sellado en el storage del PAC, cuya fecha dice cuándo el SAT
     recibió la solicitud — y cuya AUSENCIA dice que el trámite no pasó por
     Facturación Moderna.

Uso (dentro del contenedor):
  python scripts/diagnostico_cancelacion_sat.py A-57 A-1145
  python scripts/diagnostico_cancelacion_sat.py 0cc7cebd-f768-4ece-addf-2b8d8683f8db
"""
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.cancelacion_intento import CancelacionIntento
from app.models.factura import Factura
from app.models.pago import Pago
from app.services import acuse_cancelacion_service as acuse_svc
from app.services import sat_cfdi_service as sat_svc

# Umbral del SAT para cancelar sin aceptación del receptor (CFF, regla 2.7.1.35).
UMBRAL_SIN_ACEPTACION = 1000


def _buscar(db, clave: str) -> list:
    """
    Devuelve TODOS los comprobantes que empatan con la clave.

    Ojo: el folio es único por empresa y serie, no globalmente, así que un
    "A-59" puede existir en varias empresas a la vez. Devolver sólo el primero
    hace que el diagnóstico hable de un comprobante distinto al que se pidió.
    Para desambiguar, usa el UUID.
    """
    clave = clave.strip()
    if "-" in clave and len(clave) < 20:
        serie, _, folio = clave.partition("-")
        facturas = (
            db.query(Factura)
            .filter(Factura.serie == serie, Factura.folio == int(folio))
            .all()
            if folio.isdigit() else []
        )
        pagos = db.query(Pago).filter(Pago.serie == serie, Pago.folio == folio).all()
        return facturas + pagos
    doc = db.query(Factura).filter(Factura.cfdi_uuid.ilike(clave)).first()
    doc = doc or db.query(Pago).filter(Pago.uuid.ilike(clave)).first()
    return [doc] if doc else []


def _linea(txt=""):
    print(txt)


def diagnosticar(db, clave: str) -> None:
    docs = _buscar(db, clave)
    if not docs:
        _linea(f"✗ No encontré ningún comprobante con «{clave}»")
        return
    if len(docs) > 1:
        _linea(f"⚠ «{clave}» existe en {len(docs)} empresas (el folio es único por "
               "empresa, no global). Diagnostico todas:")
    for doc in docs:
        _diagnosticar_uno(db, doc)


def _diagnosticar_uno(db, doc) -> None:
    es_factura = isinstance(doc, Factura)
    uuid_cfdi = (doc.cfdi_uuid if es_factura else doc.uuid) or ""
    estatus = getattr(doc.estatus, "value", doc.estatus)
    etiqueta = f"{doc.serie or ''}-{doc.folio}"
    total = float(doc.total if es_factura else (doc.cfdi_total or doc.monto) or 0)

    _linea("═" * 72)
    _linea(f"  {'FACTURA' if es_factura else 'COMPLEMENTO DE PAGO'} {etiqueta}"
           f"   ${total:,.2f}   {doc.empresa.nombre_comercial or doc.empresa.nombre}")
    _linea(f"  Cliente: {doc.cliente.nombre_razon_social or doc.cliente.nombre_comercial}")
    _linea(f"  UUID: {uuid_cfdi}")
    _linea("═" * 72)

    # ── 1 y 2: sistema contra SAT ───────────────────────────────────────────
    try:
        e, r, t = sat_svc.datos_consulta(doc)
        acuse = sat_svc.consultar_cfdi(rfc_emisor=e, rfc_receptor=r, total=t, uuid=uuid_cfdi)
    except Exception as exc:  # noqa: BLE001
        _linea(f"  No se pudo consultar el SAT: {exc}")
        return

    _linea(f"  En el sistema : {estatus}")
    _linea(f"  En el SAT     : {acuse.estado}"
           + (f" — {acuse.estatus_cancelacion}" if acuse.estatus_cancelacion else ""))
    _linea(f"  EsCancelable  : {acuse.es_cancelable}")

    # ── 3: la regla de los $1,000 ───────────────────────────────────────────
    if total <= UMBRAL_SIN_ACEPTACION:
        _linea(f"  · Monto ≤ ${UMBRAL_SIN_ACEPTACION:,}: el SAT cancela sin pedir "
               "aceptación del receptor.")
    else:
        _linea(f"  · Monto > ${UMBRAL_SIN_ACEPTACION:,}: requiere aceptación del "
               "receptor, o tres días hábiles de silencio.")

    # ── Columnas de cancelación del documento ───────────────────────────────
    _linea()
    _linea("  ── Lo que guarda el documento ─────────────────────────────────")
    campos = [
        ("motivo", getattr(doc, "motivo_cancelacion", None)),
        ("folio sustituto", getattr(doc, "folio_fiscal_sustituto", None)),
        ("código del PAC", getattr(doc, "cancelacion_code", None)),
        ("mensaje del PAC", getattr(doc, "cancelacion_message", None)),
        ("fecha de solicitud", getattr(doc, "fecha_solicitud_cancelacion", None)),
        ("acuse archivado", getattr(doc, "cancelacion_acuse_path", None)),
    ]
    if not any(v for _, v in campos):
        _linea("    (vacío) — nunca se pidió la cancelación desde el sistema")
    else:
        for k, v in campos:
            if v:
                _linea(f"    {k}: {str(v)[:100]}")

    # ── 4: rastro de auditoría ──────────────────────────────────────────────
    _linea()
    _linea("  ── Rastro de auditoría ────────────────────────────────────────")
    filas = db.execute(
        __import__("sqlalchemy").text(
            "select accion, usuario_email, creado_en, detalle::text "
            "from auditoria_log where entidad_id = :eid order by creado_en"
        ),
        {"eid": str(doc.id)},
    ).fetchall()
    if not filas:
        _linea("    (sin registros)")
    for accion, email, cuando, detalle in filas:
        _linea(f"    {cuando:%Y-%m-%d %H:%M}  {accion:22} {email or ''}")
        if accion in ("CANCELAR_FACTURA", "CANCELAR_PAGO", "VERIFICAR_SAT",
                      "REVERTIR_CANCELACION", "REGISTRAR_CANCELACION_PORTAL"):
            _linea(f"        {detalle}")

    # ── Bitácora de intentos ────────────────────────────────────────────────
    intentos = (
        db.query(CancelacionIntento)
        .filter(CancelacionIntento.documento_id == doc.id)
        .order_by(CancelacionIntento.fecha_envio)
        .all()
    )
    if intentos:
        _linea()
        _linea("  ── Bitácora de intentos ───────────────────────────────────────")
        for i in intentos:
            _linea(f"    {i.fecha_envio:%Y-%m-%d %H:%M}  origen={i.origen} "
                   f"pac={i.pac_code} sat_registro={i.sat_registro_solicitud} "
                   f"resultado={i.resultado or 'abierto'}")

    # ── 5: acuse sellado en el PAC ──────────────────────────────────────────
    _linea()
    _linea("  ── Acuse sellado en el storage del PAC ────────────────────────")
    try:
        xml = acuse_svc.descargar_acuse_xml(doc, forzar=True).decode("utf-8", "ignore")
        fecha = re.search(r'Fecha="([^"]+)"', xml)
        est = re.search(r"<EstatusUUID>([^<]*)<", xml)
        _linea(f"    Sellado por el SAT el {fecha.group(1)[:19] if fecha else '?'} "
               f"— EstatusUUID {est.group(1) if est else '?'}")
        _linea("    ⇒ la solicitud SÍ salió por Facturación Moderna en esa fecha.")
    except Exception as exc:  # noqa: BLE001
        _linea(f"    No hay acuse ({str(exc)[:70]})")
        _linea("    ⇒ el trámite NO pasó por Facturación Moderna. Si el SAT sí")
        _linea("      reporta la cancelación, se hizo por otra vía (portal del SAT")
        _linea("      o el portal del PAC) y la fecha sólo se ve ahí.")

    # ── Veredicto ───────────────────────────────────────────────────────────
    _linea()
    _linea("  ── Veredicto ──────────────────────────────────────────────────")
    if acuse.cancelado_por_sat and estatus not in ("CANCELADA", "CANCELADO"):
        _linea("    El SAT ya lo canceló y el sistema no se enteró. Corregir con")
        _linea("    «Verificar con SAT» en la pantalla del comprobante.")
    elif acuse.en_proceso and estatus not in ("EN_CANCELACION",):
        _linea("    Hay una solicitud viva en el SAT esperando al receptor, y el")
        _linea("    sistema no la tiene registrada. «Verificar con SAT» la sincroniza.")
    elif not acuse.cancelado_por_sat and estatus in ("CANCELADA", "CANCELADO"):
        _linea("    El sistema lo da por cancelado pero el SAT lo tiene VIGENTE:")
        _linea("    el trámite no prosperó. Hay que volver a solicitarlo.")
    else:
        _linea("    Sistema y SAT coinciden.")
    _linea()


def main() -> None:
    claves = sys.argv[1:]
    if not claves:
        print(__doc__)
        sys.exit(1)
    db = SessionLocal()
    try:
        for c in claves:
            diagnosticar(db, c)
    finally:
        db.close()


if __name__ == "__main__":
    main()
