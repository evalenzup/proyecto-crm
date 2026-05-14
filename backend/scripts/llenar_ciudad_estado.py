"""
Script: llenar_ciudad_estado.py

Rellena los campos ciudad/estado (dirección fiscal) y serv_ciudad/serv_estado
(dirección de servicio) de los clientes usando la API de SEPOMEX o un archivo
JSON de lookup pre-generado (recomendado para producción).

Flujo recomendado para producción (evita problemas de SSL/red):

  # 1. Generar lookup en DEV (donde la API funciona)
  docker exec backend-backend-1 python scripts/llenar_ciudad_estado.py --exportar-cp /tmp/cp_lookup.json

  # 2. Copiar al host y luego a producción
  docker cp backend-backend-1:/tmp/cp_lookup.json ./cp_lookup.json
  docker cp ./cp_lookup.json crm_prod-backend-1:/tmp/cp_lookup.json

  # 3. Ejecutar en producción usando el archivo local (sin llamadas externas)
  docker exec crm_prod-backend-1 python scripts/llenar_ciudad_estado.py --db app_prod --cp-file /tmp/cp_lookup.json --force

Parámetros:
  --dry-run          Solo muestra los primeros 20 resultados sin guardar
  --force            Actualiza aunque ya tengan ciudad/estado
  --batch N          Tamaño de lote para commits (default: 200)
  --solo-fiscal      Solo actualiza ciudad/estado de dirección fiscal
  --solo-servicio    Solo actualiza serv_ciudad/serv_estado de dirección de servicio
  --db NOMBRE        Base de datos (default: app | producción: app_prod)
  --exportar-cp FILE Consulta la API y guarda el lookup de CPs en un JSON (para producción)
  --cp-file FILE     Usa un JSON de lookup local en lugar de llamar a la API
"""

import sys
import time
import argparse
import urllib.request
import urllib.parse
import json
import psycopg2
from psycopg2.extras import execute_batch

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_CONFIG_BASE = dict(host="db", port=5432, user="postgres", password="postgres")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search?postalcode={cp}&country=MX&format=json&addressdetails=1&limit=1"
REQUEST_DELAY = 1.1   # Nominatim pide máx 1 req/seg


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def limpiar_cp(cp: str) -> str:
    """Extrae solo los dígitos del CP y lo rellena a 5 con ceros a la izquierda."""
    solo_digitos = "".join(c for c in cp if c.isdigit())
    return solo_digitos.zfill(5) if solo_digitos else ""


def lookup_cp(cp: str, cache: dict) -> tuple[str | None, str | None]:
    """
    Consulta Zippopotamus para un CP mexicano.
    Retorna (ciudad, estado) en mayúsculas, o (None, None) si no se encuentra.
    Usa caché en memoria para no repetir llamadas con el mismo CP.
    """
    cp = limpiar_cp(cp)
    if not cp or cp == "00000":
        return None, None

    if cp in cache:
        return cache[cp]

    url = NOMINATIM_URL.format(cp=cp)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "proyecto-crm/1.0 (netov1@gmail.com)"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())

        if not data:
            result = (None, None)
        else:
            address = data[0].get("address", {})
            ciudad = (
                address.get("city") or
                address.get("town") or
                address.get("municipality") or
                address.get("village") or
                address.get("county") or
                ""
            ).strip().upper()
            estado = address.get("state", "").strip().upper()

            # Nominatim a veces devuelve "MUNICIPIO DE ENSENADA" en lugar de "ENSENADA"
            if ciudad.startswith("MUNICIPIO DE "):
                ciudad = ciudad[len("MUNICIPIO DE "):]

            result = (ciudad or None, estado or None)

    except Exception as e:
        print(f"    ⚠ Error consultando CP {cp}: {e}")
        result = (None, None)

    cache[cp] = result
    time.sleep(REQUEST_DELAY)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_blank(val) -> bool:
    return not val or str(val).strip() == ""


def _flush(cur, conn, updates: list):
    """
    Aplica UPDATEs a la BD agrupando por combinación de campos,
    ya que no todos los registros actualizan los mismos campos.
    """
    # Agrupar por frozenset de campos (excluyendo 'id')
    grupos: dict = {}
    for u in updates:
        clave = frozenset(k for k in u if k != "id")
        grupos.setdefault(clave, []).append(u)

    total = 0
    for campos, lote in grupos.items():
        set_clause = ", ".join(f"{c} = %({c})s" for c in sorted(campos))
        execute_batch(
            cur,
            f"UPDATE clientes SET {set_clause} WHERE id = %(id)s::uuid",
            lote,
            page_size=200,
        )
        total += len(lote)

    conn.commit()
    print(f"    → {total} registros guardados.")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
def procesar(
    cur,
    conn,
    modo: str,          # "fiscal", "servicio" o "ambos"
    dry_run: bool,
    force: bool,
    batch_size: int,
    cache: dict,
):
    """
    Consulta clientes, resuelve CPs y actualiza ciudad/estado.
    modo: "fiscal" | "servicio" | "ambos"
    """

    hacer_fiscal   = modo in ("fiscal", "ambos")
    hacer_servicio = modo in ("servicio", "ambos")

    # ---- Construir WHERE según modo y --force --------------------------------
    condiciones = []

    if hacer_fiscal:
        if not force:
            condiciones.append(
                "(ciudad IS NULL OR ciudad = '' OR estado IS NULL OR estado = '')"
            )
        condiciones.append(
            "codigo_postal IS NOT NULL AND trim(codigo_postal) != ''"
        )

    if hacer_servicio:
        if not force:
            condiciones.append(
                "(serv_ciudad IS NULL OR serv_ciudad = '' "
                "OR serv_estado IS NULL OR serv_estado = '')"
            )
        condiciones.append(
            "serv_codigo_postal IS NOT NULL AND trim(serv_codigo_postal) != ''"
        )

    where = " AND ".join(f"({c})" for c in condiciones) if condiciones else "TRUE"

    cur.execute(f"""
        SELECT id::text, nombre_comercial,
               codigo_postal, ciudad, estado,
               serv_codigo_postal, serv_ciudad, serv_estado
        FROM clientes
        WHERE {where}
        ORDER BY nombre_comercial
    """)
    rows = cur.fetchall()
    cols = ["id", "nombre_comercial",
            "codigo_postal", "ciudad", "estado",
            "serv_codigo_postal", "serv_ciudad", "serv_estado"]
    clientes = [dict(zip(cols, r)) for r in rows]

    total = len(clientes)
    limite = 20 if dry_run else total

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Clientes a procesar: {total:,}")
    if dry_run:
        print(f"Mostrando primeros {limite} sin guardar.\n")

    updates  = []
    ok = sin_cp = no_encontrado = 0

    for i, c in enumerate(clientes[:limite], 1):
        nombre  = c["nombre_comercial"][:42]
        cambios = {"id": c["id"]}
        lineas  = []

        # --- Dirección fiscal ---
        if hacer_fiscal:
            cp_raw = c.get("codigo_postal", "")
            if is_blank(cp_raw):
                lineas.append("fiscal: sin CP")
                sin_cp += 1
            else:
                cp_limpio = limpiar_cp(cp_raw)
                if cp_raw.strip() != cp_limpio:
                    cambios["codigo_postal"] = cp_limpio
                    lineas.append(f"fiscal: CP corregido '{cp_raw.strip()}' → '{cp_limpio}'")
                ciudad, estado = lookup_cp(cp_limpio, cache)
                if ciudad or estado:
                    cambios["ciudad"] = ciudad
                    cambios["estado"] = estado
                    lineas.append(f"fiscal: {ciudad}, {estado} (CP {cp_limpio})")
                    ok += 1
                else:
                    lineas.append(f"fiscal: CP {cp_limpio} no encontrado")
                    no_encontrado += 1

        # --- Dirección de servicio ---
        if hacer_servicio:
            serv_cp_raw = c.get("serv_codigo_postal", "")
            if is_blank(serv_cp_raw):
                lineas.append("servicio: sin CP")
            else:
                serv_cp_limpio = limpiar_cp(serv_cp_raw)
                if serv_cp_raw.strip() != serv_cp_limpio:
                    cambios["serv_codigo_postal"] = serv_cp_limpio
                    lineas.append(f"servicio: CP corregido '{serv_cp_raw.strip()}' → '{serv_cp_limpio}'")
                ciudad, estado = lookup_cp(serv_cp_limpio, cache)
                if ciudad or estado:
                    cambios["serv_ciudad"] = ciudad
                    cambios["serv_estado"] = estado
                    lineas.append(f"servicio: {ciudad}, {estado} (CP {serv_cp_limpio})")
                else:
                    lineas.append(f"servicio: CP {serv_cp_limpio} no encontrado")

        detalle = " | ".join(lineas)
        print(f"  [{i:>5}/{limite}] {nombre:<43} {detalle}")

        # Solo agregar al batch si hay campos reales a actualizar (más allá del id)
        campos_a_actualizar = [k for k in cambios if k != "id"]
        if not dry_run and campos_a_actualizar:
            updates.append(cambios)

        # Guardar lote
        if not dry_run and len(updates) >= batch_size:
            _flush(cur, conn, updates)
            updates.clear()

    # Guardar restantes
    if not dry_run and updates:
        _flush(cur, conn, updates)

    # Resumen
    print(f"\n{'─'*65}")
    print(f"  Actualizados correctamente : {ok:,}")
    print(f"  CP no encontrado en API    : {no_encontrado:,}")
    print(f"  Sin código postal          : {sin_cp:,}")
    print(f"  CPs únicos consultados     : {len(cache):,}")
    if dry_run:
        print(f"\n[DRY-RUN] Sin cambios guardados. Quita --dry-run para aplicar.")
    print(f"{'─'*65}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Rellena ciudad/estado de clientes desde código postal (México)"
    )
    parser.add_argument("--dry-run",       action="store_true",
                        help="Muestra resultados sin guardar")
    parser.add_argument("--force",         action="store_true",
                        help="Actualiza aunque ya tengan ciudad/estado")
    parser.add_argument("--batch",         type=int, default=200,
                        help="Tamaño de lote para commits (default: 200)")
    parser.add_argument("--solo-fiscal",   action="store_true",
                        help="Solo actualiza dirección fiscal")
    parser.add_argument("--solo-servicio", action="store_true",
                        help="Solo actualiza dirección de servicio")
    parser.add_argument("--db",            type=str, default="app",
                        help="Nombre de la base de datos (default: app, prod: app_prod)")
    parser.add_argument("--exportar-cp",   type=str, default=None, metavar="FILE",
                        help="Consulta la API y guarda el lookup en un JSON (para usar en producción)")
    parser.add_argument("--cp-file",       type=str, default=None, metavar="FILE",
                        help="Usa un JSON de lookup local en lugar de llamar a la API")
    args = parser.parse_args()

    if args.solo_fiscal and args.solo_servicio:
        print("ERROR: No puedes usar --solo-fiscal y --solo-servicio al mismo tiempo.")
        sys.exit(1)

    if args.solo_fiscal:
        modo = "fiscal"
    elif args.solo_servicio:
        modo = "servicio"
    else:
        modo = "ambos"

    # Cargar caché desde archivo local si se especificó
    cache: dict = {}
    if args.cp_file:
        try:
            with open(args.cp_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            print(f"Lookup cargado desde {args.cp_file}: {len(cache):,} CPs")
        except Exception as e:
            print(f"ERROR: No se pudo leer {args.cp_file}: {e}")
            sys.exit(1)

    conn = psycopg2.connect(**DB_CONFIG_BASE, dbname=args.db)
    cur  = conn.cursor()

    try:
        # Modo exportar: generar JSON con todos los CPs únicos de la BD
        if args.exportar_cp:
            exportar_lookup(cur, args.exportar_cp, cache)
        else:
            procesar(
                cur=cur, conn=conn,
                modo=modo,
                dry_run=args.dry_run,
                force=args.force,
                batch_size=args.batch,
                cache=cache,
            )
    finally:
        cur.close()
        conn.close()


def exportar_lookup(cur, filepath: str, cache: dict):
    """Consulta todos los CPs únicos de la BD, los resuelve via API y guarda el resultado en JSON."""
    cur.execute("""
        SELECT DISTINCT cp FROM (
            SELECT trim(codigo_postal)     AS cp FROM clientes WHERE codigo_postal IS NOT NULL AND trim(codigo_postal) != ''
            UNION
            SELECT trim(serv_codigo_postal) AS cp FROM clientes WHERE serv_codigo_postal IS NOT NULL AND trim(serv_codigo_postal) != ''
        ) t
        ORDER BY cp
    """)
    cps = [row[0] for row in cur.fetchall()]
    total = len(cps)
    print(f"Exportando lookup para {total} CPs únicos → {filepath}")

    for i, cp_raw in enumerate(cps, 1):
        cp = limpiar_cp(cp_raw)
        if not cp or cp == "00000" or cp in cache:
            continue
        ciudad, estado = lookup_cp(cp, cache)
        status = f"{ciudad}, {estado}" if ciudad else "no encontrado"
        print(f"  [{i:>4}/{total}] CP {cp} → {status}")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"\nLookup guardado en {filepath} ({len(cache)} CPs resueltos)")


if __name__ == "__main__":
    main()
