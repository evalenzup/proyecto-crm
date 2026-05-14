"""
Genera el archivo cp_lookup.json consultando la API de SEPOMEX desde el host (Mac).
Corre directamente en tu Mac donde SSL funciona correctamente.

Uso:
    python generar_cp_lookup.py
    python generar_cp_lookup.py --puerto 5433   # si prod está en otro puerto
"""

import json
import time
import argparse
import urllib.request
import urllib.error
import psycopg2

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search?postalcode={cp}&country=MX&format=json&addressdetails=1&limit=1"
REQUEST_DELAY = 1.1   # Nominatim pide máx 1 req/seg

def limpiar_cp(cp: str) -> str:
    solo_digitos = "".join(c for c in cp if c.isdigit())
    return solo_digitos.zfill(5) if solo_digitos else ""

def lookup_cp(cp: str) -> tuple:
    url = NOMINATIM_URL.format(cp=cp)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "proyecto-crm/1.0 (netov1@gmail.com)"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())

        if not data:
            return None, None

        address = data[0].get("address", {})
        # Nominatim usa distintos campos según el tamaño de la localidad
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

        return ciudad or None, estado or None

    except Exception as e:
        print(f"  ⚠ Error CP {cp}: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host",    default="localhost")
    parser.add_argument("--puerto",  type=int, default=5432)
    parser.add_argument("--db",      default="app")
    parser.add_argument("--user",    default="postgres")
    parser.add_argument("--password",default="postgres")
    parser.add_argument("--salida",  default="cp_lookup.json")
    args = parser.parse_args()

    # Obtener CPs únicos de la BD
    conn = psycopg2.connect(
        host=args.host, port=args.puerto, dbname=args.db,
        user=args.user, password=args.password
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT cp FROM (
            SELECT trim(codigo_postal)      AS cp FROM clientes
             WHERE codigo_postal IS NOT NULL AND trim(codigo_postal) != ''
            UNION
            SELECT trim(serv_codigo_postal) AS cp FROM clientes
             WHERE serv_codigo_postal IS NOT NULL AND trim(serv_codigo_postal) != ''
        ) t ORDER BY cp
    """)
    cps_raw = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    # Limpiar y deduplicar
    cps = sorted({limpiar_cp(cp) for cp in cps_raw if limpiar_cp(cp) and limpiar_cp(cp) != "00000"})
    total = len(cps)
    print(f"CPs únicos a resolver: {total}\n")

    cache = {}
    ok = fail = 0

    for i, cp in enumerate(cps, 1):
        ciudad, estado = lookup_cp(cp)
        cache[cp] = [ciudad, estado]
        time.sleep(REQUEST_DELAY)

        if ciudad:
            ok += 1
            print(f"  [{i:>4}/{total}] {cp} → {ciudad}, {estado}")
        else:
            fail += 1
            print(f"  [{i:>4}/{total}] {cp} → no encontrado")

    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*55}")
    print(f"  Resueltos correctamente : {ok}")
    print(f"  No encontrados          : {fail}")
    print(f"  Archivo guardado en     : {args.salida}")
    print(f"{'─'*55}")

if __name__ == "__main__":
    main()
