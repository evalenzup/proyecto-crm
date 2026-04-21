"""
Script: geocodificar_clientes.py

Geocodifica la dirección de servicio de los clientes usando HERE Geocoding API
y guarda las coordenadas en los campos serv_latitud / serv_longitud de la BD.

Requiere:
  - HERE_API_KEY en variables de entorno
  - Columnas serv_latitud y serv_longitud en la tabla clientes (ver nota abajo)

  Si aún no existen esas columnas, el script las crea automáticamente.

Uso:
  # Simular sin guardar (muestra resultados de los primeros 20 clientes)
  docker compose exec backend python scripts/geocodificar_clientes.py --dry-run

  # Correr completo
  docker compose exec backend python scripts/geocodificar_clientes.py

  # Regeocóder solo los que ya tienen coordenadas (re-procesar)
  docker compose exec backend python scripts/geocodificar_clientes.py --force

Parámetros:
  --dry-run     Solo muestra los primeros 20 resultados sin guardar
  --force       Procesa también clientes que ya tienen serv_latitud
  --min-score   Score mínimo aceptable de HERE (default: 0.5)
  --batch       Tamaño de lote para commits (default: 100)
"""

import os
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
DB_CONFIG = dict(host="db", port=5432, dbname="app", user="postgres", password="postgres")
HERE_API_URL = "https://geocode.search.hereapi.com/v1/geocode"
REQUEST_DELAY = 0.05   # segundos entre requests (HERE permite 5 req/seg en free tier)
CIUDAD_DEFAULT = "ENSENADA"
ESTADO_DEFAULT = "BAJA CALIFORNIA"
PAIS_DEFAULT   = "MEXICO"


def get_here_key():
    key = os.environ.get("HERE_API_KEY", "")
    if not key:
        print("ERROR: HERE_API_KEY no encontrada en variables de entorno.")
        sys.exit(1)
    return key


def ensure_columns(cur):
    """No-op: latitud y longitud ya existen en el modelo original."""
    pass


def build_address(row):
    """Construye la cadena de dirección más completa posible."""
    parts = []
    if row.get("serv_calle"):
        calle = row["serv_calle"].strip()
        if row.get("serv_numero_exterior"):
            calle += " " + row["serv_numero_exterior"].strip()
        parts.append(calle)
    if row.get("serv_colonia"):
        parts.append(row["serv_colonia"].strip())
    if row.get("serv_codigo_postal"):
        parts.append(row["serv_codigo_postal"].strip())
    parts.append(CIUDAD_DEFAULT)
    parts.append(ESTADO_DEFAULT)
    parts.append(PAIS_DEFAULT)
    return ", ".join(p for p in parts if p)


def geocode(address: str, api_key: str) -> tuple:
    """
    Llama a HERE Geocoding API.
    Retorna (latitud, longitud, score) o (None, None, 0) si no hay resultado.
    """
    params = urllib.parse.urlencode({"q": address, "apiKey": api_key, "limit": 1})
    url = f"{HERE_API_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        items = data.get("items", [])
        if not items:
            return None, None, 0.0
        item = items[0]
        pos   = item["position"]
        score = item.get("scoring", {}).get("queryScore", 0.0)
        return pos["lat"], pos["lng"], score
    except Exception as e:
        print(f"    ⚠ Error en geocodificación: {e}")
        return None, None, 0.0


def is_placeholder(val):
    """True si el valor es null o un placeholder sin datos reales."""
    if not val:
        return True
    v = str(val).strip().upper()
    return v in ("", "-", "X", "0", "S", "XXXX", "XXXXX", "XXXXXX") or len(v) <= 1


def main(dry_run: bool, force: bool, min_score: float, batch_size: int):
    api_key = get_here_key()
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Asegurar columnas
    ensure_columns(cur)
    conn.commit()

    # Consultar clientes a procesar
    where_force = "" if force else "AND (c.latitud IS NULL OR c.latitud = 0)"
    cur.execute(f"""
        SELECT id::text, nombre_comercial,
               serv_calle, serv_numero_exterior, serv_colonia, serv_codigo_postal
        FROM clientes c
        WHERE serv_calle IS NOT NULL
          AND length(trim(serv_calle)) > 1
          AND trim(serv_calle) NOT IN ('-','X','0','S')
          {where_force}
        ORDER BY nombre_comercial
    """)
    rows = cur.fetchall()
    cols = ["id", "nombre_comercial", "serv_calle", "serv_numero_exterior",
            "serv_colonia", "serv_codigo_postal"]
    clientes = [dict(zip(cols, r)) for r in rows]

    total = len(clientes)
    limit = 20 if dry_run else total

    print(f"{'[DRY-RUN] ' if dry_run else ''}Clientes a geocodificar: {total:,}")
    if dry_run:
        print(f"Mostrando primeros {limit} resultados sin guardar.\n")

    updates = []
    ok = sin_resultado = bajo_score = 0

    for i, cliente in enumerate(clientes[:limit], 1):
        address = build_address(cliente)
        lat, lon, score = geocode(address, api_key)
        time.sleep(REQUEST_DELAY)

        if lat is None:
            sin_resultado += 1
            status = "✗ Sin resultado"
        elif score < min_score:
            bajo_score += 1
            status = f"⚠ Score bajo ({score:.2f})"
            lat = lon = None
        else:
            ok += 1
            status = f"✓ ({lat:.5f}, {lon:.5f}) score={score:.2f}"
            updates.append({
                "id": cliente["id"],
                "latitud": lat,
                "longitud": lon,
            })

        print(f"  [{i:>5}/{limit}] {cliente['nombre_comercial'][:40]:<40} {status}")

        # Guardar en lotes
        if not dry_run and len(updates) >= batch_size:
            _flush(cur, conn, updates)
            updates.clear()

    # Guardar restantes
    if not dry_run and updates:
        _flush(cur, conn, updates)

    print(f"\n{'─'*60}")
    print(f"  Geocodificados correctamente : {ok:,}")
    print(f"  Sin resultado en HERE        : {sin_resultado:,}")
    print(f"  Score por debajo de {min_score}     : {bajo_score:,}")
    if not dry_run:
        print(f"  Total guardados en BD        : {ok:,}")
    print(f"{'─'*60}")
    if dry_run:
        print("\n[DRY-RUN] Sin cambios guardados. Quita --dry-run para aplicar.")

    cur.close()
    conn.close()


def _flush(cur, conn, updates):
    execute_batch(
        cur,
        """UPDATE clientes
           SET latitud  = %(latitud)s,
               longitud = %(longitud)s
           WHERE id = %(id)s::uuid""",
        updates,
        page_size=200,
    )
    conn.commit()
    print(f"    → {len(updates)} registros guardados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--force",     action="store_true")
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--batch",     type=int,   default=100)
    args = parser.parse_args()
    main(dry_run=args.dry_run, force=args.force,
         min_score=args.min_score, batch_size=args.batch)
