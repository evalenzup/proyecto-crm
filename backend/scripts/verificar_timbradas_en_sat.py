#!/usr/bin/env python3
"""
verificar_timbradas_en_sat.py
─────────────────────────────
Verifica contra el SAT todas las facturas con estatus TIMBRADA (o EN_CANCELACION)
que tengan cfdi_uuid, y actualiza el estatus si el SAT reporta que están canceladas.

USO:
    cd backend/
    python scripts/verificar_timbradas_en_sat.py

    # Verificar un mes específico (formato YYYY-MM):
    python scripts/verificar_timbradas_en_sat.py --mes 2026-03
    python scripts/verificar_timbradas_en_sat.py --mes 2025-12

    # Solo mostrar qué cambiaría, sin escribir en BD:
    python scripts/verificar_timbradas_en_sat.py --dry-run

    # Incluir también EN_CANCELACION (ya lo hace el cron, pero útil para recovery):
    python scripts/verificar_timbradas_en_sat.py --include-en-cancelacion

    # Limitar a una empresa específica:
    python scripts/verificar_timbradas_en_sat.py --empresa-id <UUID>

    # Combinar parámetros:
    python scripts/verificar_timbradas_en_sat.py --mes 2026-01 --dry-run --empresa-id <UUID>

    # ── Casos especiales ──────────────────────────────────────────────────────

    # Forzar CANCELADA por UUID (cuando tienes el acuse oficial pero el SAT
    # devuelve N-601 por discrepancia de total u otro dato):
    python scripts/verificar_timbradas_en_sat.py --forzar-cancelada 37383E88-8ABA-4775-AC92-7D2E70DA42F1
    python scripts/verificar_timbradas_en_sat.py --forzar-cancelada UUID1 --forzar-cancelada UUID2
    python scripts/verificar_timbradas_en_sat.py --forzar-cancelada UUID --dry-run

    # Verificar (o forzar) un UUID puntual sin procesar todo el mes:
    python scripts/verificar_timbradas_en_sat.py --uuid 37383E88-8ABA-4775-AC92-7D2E70DA42F1

    # ── N-601: buscar el total correcto ───────────────────────────────────────

    # Cuando el SAT devuelve N-601 (total no coincide), probar centavos
    # cercanos hasta encontrar el que el SAT sí reconoce, obteniendo el estado real:
    python scripts/verificar_timbradas_en_sat.py --mes 2026-04 --corregir-n601

    # Ampliar la tolerancia de búsqueda (default ±1.00 en pasos de 0.01):
    python scripts/verificar_timbradas_en_sat.py --mes 2026-04 --corregir-n601 --tolerancia 2.00

    # Solo para un UUID puntual:
    python scripts/verificar_timbradas_en_sat.py --uuid 37383E88-8ABA-4775-AC92-7D2E70DA42F1 --corregir-n601

REQUISITOS:
    - Ejecutar desde backend/ para que el PYTHONPATH resuelva los módulos de app.
    - El archivo .env debe estar en backend/ (o DATABASE_URL en el entorno).

NOTA sobre N-601:
    El web service del SAT requiere que RFC_emisor + RFC_receptor + total + UUID
    coincidan exactamente. Si el total en BD difiere del timbrado, el SAT responde
    N-601. Con --corregir-n601 el script prueba totales en el rango
    [total_bd - tolerancia, total_bd + tolerancia] en pasos de 0.01 hasta que el
    SAT responda, revelando el estado real. Si encuentra el total correcto, lo
    corrige en BD junto con el estatus.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from uuid import UUID
import calendar

# ── Asegurar que el directorio raíz del proyecto esté en el path ──────────────
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.factura import Factura
from app.services import sat_cfdi_service as sat_svc

# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Verifica facturas TIMBRADAS contra el SAT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Consulta el SAT pero NO escribe cambios en la BD",
    )
    parser.add_argument(
        "--include-en-cancelacion",
        action="store_true",
        help="Incluir también facturas EN_CANCELACION (además de TIMBRADAS)",
    )
    parser.add_argument(
        "--empresa-id",
        type=str,
        default=None,
        help="Filtrar por empresa_id (UUID). Omitir para todas las empresas.",
    )
    parser.add_argument(
        "--mes",
        type=str,
        default=None,
        metavar="YYYY-MM",
        help=(
            "Mes a verificar en formato YYYY-MM (ej: 2026-03). "
            "Por defecto se usa el mes actual."
        ),
    )
    parser.add_argument(
        "--uuid",
        type=str,
        action="append",
        default=[],
        metavar="UUID",
        help=(
            "Verificar uno o varios CFDIs por UUID, ignorando el filtro de mes. "
            "Puede repetirse: --uuid UUID1 --uuid UUID2 ..."
        ),
    )
    parser.add_argument(
        "--forzar-cancelada",
        type=str,
        action="append",
        default=[],
        metavar="UUID",
        help=(
            "Marcar la factura con ese UUID como CANCELADA directamente, "
            "sin consultar el SAT. Usar cuando tienes el acuse oficial pero "
            "el SAT devuelve N-601. Puede repetirse para múltiples UUIDs."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar los parámetros exactos que se envían al SAT (RFC, total, expresionImpresa).",
    )
    parser.add_argument(
        "--rfc-receptor",
        type=str,
        default=None,
        metavar="RFC",
        help=(
            "Sobreescribir el RFC receptor para la consulta al SAT. "
            "Útil cuando la BD tiene el RFC real del cliente pero el CFDI "
            "fue timbrado con XAXX010101000 (público en general)."
        ),
    )
    parser.add_argument(
        "--rfc-emisor",
        type=str,
        default=None,
        metavar="RFC",
        help="Sobreescribir el RFC emisor para la consulta al SAT.",
    )
    parser.add_argument(
        "--corregir-n601",
        action="store_true",
        help=(
            "Cuando el SAT devuelve N-601, probar totales cercanos (±tolerancia "
            "en pasos de $0.01) para encontrar el total real y obtener el estado "
            "verdadero. Si lo encuentra, corrige total y estatus en la BD."
        ),
    )
    parser.add_argument(
        "--tolerancia",
        type=float,
        default=1.00,
        metavar="PESOS",
        help=(
            "Rango máximo de búsqueda para --corregir-n601, en pesos (default: 1.00). "
            "Con 1.00 se prueban hasta 200 candidatos (±100 centavos)."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Segundos de espera entre consultas al SAT (default: 0.5)",
    )
    return parser.parse_args()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _buscar_total_correcto(
    rfc_emisor: str,
    rfc_receptor: str,
    uuid: str,
    total_bd: float,
    tolerancia: float = 1.00,
    delay: float = 0.3,
):
    """
    Cuando el SAT responde N-601, el total en BD no coincide con el timbrado.
    Esta función prueba candidatos en el rango [total_bd - tolerancia, total_bd + tolerancia]
    en pasos de $0.01, alternando hacia arriba y hacia abajo desde el valor base,
    para minimizar llamadas en el caso más frecuente (discrepancia de 1-2 centavos).

    Retorna (total_correcto: float, acuse: AcuseSAT) si el SAT responde,
    o (None, None) si agota todos los candidatos sin éxito.
    """
    import decimal

    base = decimal.Decimal(str(total_bd)).quantize(decimal.Decimal("0.01"))
    paso = decimal.Decimal("0.01")
    max_pasos = int(round(decimal.Decimal(str(tolerancia)) / paso))

    # Orden: +0.01, -0.01, +0.02, -0.02, ... para encontrar rápido diferencias pequeñas
    candidatos = []
    for n in range(1, max_pasos + 1):
        candidatos.append(base + paso * n)
        candidatos.append(base - paso * n)

    for candidato in candidatos:
        if candidato <= 0:
            continue
        try:
            acuse = sat_svc.consultar_cfdi(
                rfc_emisor=rfc_emisor,
                rfc_receptor=rfc_receptor,
                total=float(candidato),
                uuid=uuid,
            )
            if acuse.encontrado:
                return float(candidato), acuse
        except RuntimeError:
            pass
        time.sleep(delay)

    return None, None


def _forzar_canceladas(db, uuids: list[str], dry_run: bool) -> None:
    """
    Marca directamente como CANCELADA cada factura cuyo cfdi_uuid esté en la lista.
    Usar cuando el SAT devuelve N-601 (discrepancia de total u otro dato) pero se
    tiene el acuse oficial de cancelación.
    """
    print(f"\n{'─'*80}")
    print(f"{'[DRY-RUN] ' if dry_run else ''}FORZANDO CANCELACIÓN para {len(uuids)} UUID(s):\n")

    forzadas = 0
    no_halladas = 0

    for raw_uuid in uuids:
        raw_uuid = raw_uuid.strip().upper()
        factura = db.query(Factura).filter(
            Factura.cfdi_uuid.ilike(raw_uuid)
        ).first()

        if not factura:
            print(f"  {raw_uuid}  →  ⚠ No encontrada en BD (UUID no existe o ya sin cfdi_uuid)")
            no_halladas += 1
            continue

        folio = (
            f"{factura.serie or ''}-{factura.folio or ''}"
            if getattr(factura, "serie", None)
            else str(getattr(factura, "folio", factura.id))
        )
        estatus_anterior = factura.estatus

        if estatus_anterior == "CANCELADA":
            print(f"  {folio:<20} UUID: {raw_uuid}  →  Ya estaba CANCELADA (sin cambio)")
            continue

        if dry_run:
            print(f"  {folio:<20} UUID: {raw_uuid}  →  [DRY-RUN] {estatus_anterior} → CANCELADA")
        else:
            factura.estatus = "CANCELADA"
            factura.fecha_solicitud_cancelacion = None
            db.add(factura)
            db.commit()
            print(f"  {folio:<20} UUID: {raw_uuid}  →  ACTUALIZADA: {estatus_anterior} → CANCELADA ✓")
        forzadas += 1

    print(f"\n  Forzadas : {forzadas}")
    if no_halladas:
        print(f"  No halladas en BD: {no_halladas}")
    if dry_run:
        print("  (DRY-RUN — no se escribieron cambios)")
    print()


def main():
    args = parse_args()

    db = SessionLocal()
    try:
        # ── Modo --forzar-cancelada: no consulta el SAT, actualiza directo ────
        if args.forzar_cancelada:
            _forzar_canceladas(db, args.forzar_cancelada, dry_run=args.dry_run)
            return

        # ── Construir query ───────────────────────────────────────────────────
        statuses = ["TIMBRADA"]
        if args.include_en_cancelacion:
            statuses.append("EN_CANCELACION")

        # ── Modo --uuid: verificar uno o varios CFDIs por UUID ───────────────
        if args.uuid:
            facturas = []
            for raw_uuid in args.uuid:
                raw_uuid = raw_uuid.strip().upper()
                factura = db.query(Factura).filter(
                    Factura.cfdi_uuid.ilike(raw_uuid)
                ).first()
                if not factura:
                    print(f"ADVERTENCIA: No se encontró factura con cfdi_uuid = {raw_uuid} (ignorada)")
                    continue
                facturas.append(factura)
            if not facturas:
                print("ERROR: Ningún UUID encontrado en BD.")
                sys.exit(1)
            print(f"Modo UUID puntual: {len(facturas)} factura(s)\n")

        else:
            # ── Calcular rango del mes ────────────────────────────────────────
            if args.mes:
                try:
                    año, mes = args.mes.split("-")
                    año, mes = int(año), int(mes)
                    if not (1 <= mes <= 12):
                        raise ValueError
                except ValueError:
                    print(f"ERROR: --mes '{args.mes}' no tiene el formato correcto. Use YYYY-MM (ej: 2026-03).")
                    sys.exit(1)
                ultimo_dia = calendar.monthrange(año, mes)[1]
                inicio_mes = datetime(año, mes, 1, 0, 0, 0)
                fin_mes    = datetime(año, mes, ultimo_dia, 23, 59, 59, 999999)
                etiqueta_rango = f"mes solicitado ({args.mes})"
            else:
                hoy = utcnow()
                inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                fin_mes    = hoy.replace(day=ultimo_dia, hour=23, minute=59, second=59, microsecond=999999)
                etiqueta_rango = "mes en curso"

            print(f"Rango: {inicio_mes.strftime('%Y-%m-%d')} al {fin_mes.strftime('%Y-%m-%d')} ({etiqueta_rango})")

            query = db.query(Factura).filter(
                Factura.estatus.in_(statuses),
                Factura.cfdi_uuid.isnot(None),
                Factura.fecha_emision >= inicio_mes,
                Factura.fecha_emision <= fin_mes,
            )

            if args.empresa_id:
                try:
                    emp_uuid = UUID(args.empresa_id)
                except ValueError:
                    print(f"ERROR: --empresa-id '{args.empresa_id}' no es un UUID válido.")
                    sys.exit(1)
                query = query.filter(Factura.empresa_id == emp_uuid)

            facturas = query.order_by(Factura.fecha_emision).all()

        total = len(facturas)
        if total == 0:
            print("No se encontraron facturas para verificar.")
            return

        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Verificando {total} factura(s) contra el SAT...\n")
        print(f"{'─'*80}")

        # Contadores
        sin_cambio     = 0
        canceladas     = 0
        revertidas     = 0    # EN_CANCELACION → TIMBRADA (por rechazo o vencimiento 72h)
        en_proceso     = 0
        errores        = 0
        no_encontradas = 0
        n601_sin_resolver = 0

        for i, factura in enumerate(facturas, start=1):
            rfc_emisor   = (args.rfc_emisor  or getattr(getattr(factura, "empresa", None), "rfc", None) or "").strip().upper()
            rfc_receptor = (args.rfc_receptor or getattr(getattr(factura, "cliente", None), "rfc", None) or "").strip().upper()
            total_factura = float(factura.total or 0)

            folio_display = (
                f"{factura.serie or ''}-{factura.folio or ''}"
                if getattr(factura, "serie", None)
                else str(getattr(factura, "folio", factura.id))
            )
            print(
                f"[{i:>4}/{total}] {folio_display:<20} "
                f"UUID: {factura.cfdi_uuid}  "
                f"Estatus actual: {factura.estatus}",
                end="  →  ",
                flush=True,
            )

            if args.verbose:
                from app.services.sat_cfdi_service import _build_expresion
                expr = _build_expresion(rfc_emisor, rfc_receptor, total_factura, factura.cfdi_uuid)
                print(f"\n  [VERBOSE] RFC emisor  : {rfc_emisor!r}")
                print(f"  [VERBOSE] RFC receptor: {rfc_receptor!r}")
                print(f"  [VERBOSE] Total       : {total_factura}")
                print(f"  [VERBOSE] expresion   : {expr}")
                print("  →  ", end="", flush=True)

            # ── Consultar SAT ─────────────────────────────────────────────────
            try:
                acuse = sat_svc.consultar_cfdi(
                    rfc_emisor=rfc_emisor,
                    rfc_receptor=rfc_receptor,
                    total=total_factura,
                    uuid=factura.cfdi_uuid,
                )
            except RuntimeError as e:
                print(f"ERROR SAT: {e}")
                errores += 1
                time.sleep(args.delay)
                continue

            # ── Determinar nuevo estatus (lógica canónica centralizada) ──────────
            estatus_anterior = factura.estatus

            if not acuse.encontrado:
                es_n601 = "601" in acuse.codigo_estatus

                if es_n601 and args.corregir_n601:
                    # ── Buscar el total correcto probando centavos cercanos ────
                    print(
                        f"N-601 (total BD=${total_factura:.2f}) — buscando total correcto "
                        f"(±${args.tolerancia:.2f})...",
                        flush=True,
                    )
                    total_correcto, acuse_correcto = _buscar_total_correcto(
                        rfc_emisor=rfc_emisor.strip().upper(),
                        rfc_receptor=rfc_receptor.strip().upper(),
                        uuid=factura.cfdi_uuid,
                        total_bd=total_factura,
                        tolerancia=args.tolerancia,
                        delay=args.delay,
                    )

                    if acuse_correcto is None:
                        print(
                            f"           → No se encontró total en ±${args.tolerancia:.2f}. "
                            "Requiere revisión manual o ampliar --tolerancia."
                        )
                        n601_sin_resolver += 1
                        continue

                    # Tenemos el total correcto y el acuse real del SAT
                    diff = total_correcto - total_factura
                    print(
                        f"           → Total correcto: ${total_correcto:.2f} "
                        f"(diferencia: {'+' if diff >= 0 else ''}{diff:.2f})",
                        flush=True,
                    )

                    # Aplicar el acuse usando la lógica canónica
                    nuevo_estatus, cambio = sat_svc.aplicar_acuse_sat(
                        factura, acuse_correcto, ahora=utcnow()
                    )
                    sat_info = f"SAT={acuse_correcto.estado}/{acuse_correcto.estatus_cancelacion or 'sin estatus'}"

                    if not cambio and abs(diff) < 0.001:
                        print(f"           → Sin cambio de estatus  ({sat_info})")
                        sin_cambio += 1
                    else:
                        if args.dry_run:
                            cambios = []
                            if cambio:
                                cambios.append(f"estatus {estatus_anterior} → {nuevo_estatus}")
                            if abs(diff) >= 0.001:
                                cambios.append(f"total ${total_factura:.2f} → ${total_correcto:.2f}")
                            print(f"           → [DRY-RUN] Se corregiría: {', '.join(cambios)}  ({sat_info})")
                        else:
                            cambios = []
                            if abs(diff) >= 0.001:
                                factura.total = total_correcto
                                cambios.append(f"total ${total_factura:.2f} → ${total_correcto:.2f}")
                            if cambio:
                                cambios.append(f"estatus {estatus_anterior} → {nuevo_estatus}")
                                if nuevo_estatus == "CANCELADA":
                                    canceladas += 1
                                elif nuevo_estatus == "EN_CANCELACION":
                                    en_proceso += 1
                                elif nuevo_estatus == "TIMBRADA" and estatus_anterior == "EN_CANCELACION":
                                    revertidas += 1
                            db.add(factura)
                            db.commit()
                            print(f"           → CORREGIDA: {', '.join(cambios)}  ({sat_info})")
                        if cambio and nuevo_estatus not in ("CANCELADA", "EN_CANCELACION", "TIMBRADA"):
                            sin_cambio += 1
                else:
                    hint = ""
                    if es_n601:
                        hint = " ⚠ Usa --corregir-n601 para buscar el total real automáticamente."
                    print(f"NO ENCONTRADO en SAT ({acuse.codigo_estatus}){hint}")
                    no_encontradas += 1

                time.sleep(args.delay)
                continue

            # aplicar_acuse_sat muta factura.estatus y fecha_solicitud_cancelacion
            # y devuelve (nuevo_estatus, hubo_cambio)
            nuevo_estatus, cambio = sat_svc.aplicar_acuse_sat(factura, acuse, ahora=utcnow())

            # ── Resultado ─────────────────────────────────────────────────────
            sat_info = f"SAT={acuse.estado}/{acuse.estatus_cancelacion or 'sin estatus'}"

            if not cambio:
                print(f"Sin cambio  ({sat_info})")
                sin_cambio += 1
            else:
                tag = ""
                if nuevo_estatus == "CANCELADA":
                    tag = "CANCELADA ✓"
                    canceladas += 1
                elif nuevo_estatus == "TIMBRADA" and estatus_anterior == "EN_CANCELACION":
                    tag = "REVERTIDA a TIMBRADA (receptor rechazó)"
                    revertidas += 1
                elif nuevo_estatus == "EN_CANCELACION":
                    tag = "EN_CANCELACION"
                    en_proceso += 1

                if args.dry_run:
                    print(f"[DRY-RUN] {estatus_anterior} → {nuevo_estatus}  {tag}  ({sat_info})")
                else:
                    # Los campos ya fueron mutados por aplicar_acuse_sat
                    db.add(factura)
                    db.commit()
                    print(f"ACTUALIZADA: {estatus_anterior} → {nuevo_estatus}  {tag}  ({sat_info})")

            time.sleep(args.delay)

        # ── Resumen ───────────────────────────────────────────────────────────
        print(f"\n{'─'*80}")
        print(f"RESUMEN {'(DRY-RUN — sin cambios en BD)' if args.dry_run else ''}:")
        print(f"  Total procesadas        : {total}")
        print(f"  Sin cambio              : {sin_cambio}")
        print(f"  → CANCELADA             : {canceladas}")
        print(f"  → EN_CANCELACION        : {en_proceso}")
        print(f"  → Revertidas a TIMBRADA : {revertidas}")
        print(f"  No encontradas SAT      : {no_encontradas}")
        if args.corregir_n601:
            print(f"  N-601 sin resolver      : {n601_sin_resolver}")
        print(f"  Errores SAT             : {errores}")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
