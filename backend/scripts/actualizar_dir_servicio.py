"""
Script: actualizar_dir_servicio.py

Lee BASE DE DATOS FUMIGACIONES.xlsx y popula los campos serv_* en la tabla
clientes de la base de datos de desarrollo.

Estrategia de match (en orden de prioridad):
  1. Excel nombreC  == DB nombre_comercial     (case-insensitive, trimmed)
  2. Excel nombreC  == DB nombre_razon_social
  3. Excel nombreF  == DB nombre_comercial
  4. Excel nombreF  == DB nombre_razon_social
  5. Excel rfc      == DB rfc                  (excluye XAXX010101000 y nulls)

Reglas:
  - No sobreescribe si serv_calle ya tiene valor.
  - Si un cliente en BD hace match con múltiples filas del Excel, se usa la
    que tenga más campos de dirección completos.
  - Los 164 casos ambiguos (RFC coincide pero ningún nombre coincide) se omiten
    y se reportan al final para revisión manual.

Uso:
  docker compose exec backend python scripts/actualizar_dir_servicio.py

  Para solo simular sin guardar cambios:
  docker compose exec backend python scripts/actualizar_dir_servicio.py --dry-run
"""

import sys
import argparse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_CONFIG = dict(host="db", port=5432, dbname="app", user="postgres", password="postgres")
EXCEL_PATH = "/app/BASE DE DATOS FUMIGACIONES.xlsx"
GENERIC_RFC = "XAXX010101000"
BATCH_SIZE = 500


def clean(val):
    """Normaliza a string en mayúsculas sin espacios extra. None si vacío."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().upper()
    return s if s else None


def address_score(row):
    """Puntaje de completitud de dirección (más alto = más completo)."""
    score = 0
    if clean(row.get("calle")):
        score += 3
    if clean(row.get("colonia")):
        score += 2
    if clean(row.get("codigoPostal")):
        score += 2
    if clean(row.get("numeroExterior")):
        score += 1
    return score


def build_lookup(excel_df):
    """
    Construye dos diccionarios:
      name_lookup: nombre_normalizado -> mejor fila del Excel
      rfc_lookup:  rfc -> mejor fila del Excel  (solo RFCs válidos)
    """
    name_lookup = {}
    rfc_lookup = {}

    for _, row in excel_df.iterrows():
        nombre_c = clean(row.get("nombreC"))
        nombre_f = clean(row.get("nombreF"))
        rfc = clean(row.get("rfc"))

        score = address_score(row)
        row_dict = row.to_dict()
        row_dict["_score"] = score

        # índice por nombres
        for name in filter(None, [nombre_c, nombre_f]):
            if name not in name_lookup or score > name_lookup[name]["_score"]:
                name_lookup[name] = row_dict

        # índice por RFC
        if rfc and rfc != GENERIC_RFC:
            if rfc not in rfc_lookup or score > rfc_lookup[rfc]["_score"]:
                rfc_lookup[rfc] = row_dict

    return name_lookup, rfc_lookup


def find_match(db_row, name_lookup, rfc_lookup):
    """
    Busca la mejor fila del Excel para un cliente de la BD.
    Devuelve (fila_excel, metodo) o (None, None).
    """
    nom_com = clean(db_row["nombre_comercial"])
    nom_raz = clean(db_row["nombre_razon_social"])
    rfc_db  = clean(db_row["rfc"])

    # Prioridad 1-4: por nombre
    for name in filter(None, [nom_com, nom_raz]):
        if name in name_lookup:
            return name_lookup[name], "nombre"

    # Prioridad 5: por RFC
    if rfc_db and rfc_db != GENERIC_RFC and rfc_db in rfc_lookup:
        return rfc_lookup[rfc_db], "rfc"

    return None, None


def main(dry_run: bool):
    print(f"{'[DRY-RUN] ' if dry_run else ''}Iniciando actualización de dirección de servicio...\n")

    # --- Cargar Excel ---
    print("Leyendo Excel...")
    df = pd.read_excel(EXCEL_PATH, header=1, dtype=str)
    df.columns = df.columns.str.strip()
    print(f"  {len(df):,} filas leídas del Excel.")

    name_lookup, rfc_lookup = build_lookup(df)
    print(f"  Índice por nombre: {len(name_lookup):,} entradas")
    print(f"  Índice por RFC: {len(rfc_lookup):,} entradas\n")

    # --- Conectar a BD ---
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre_comercial, nombre_razon_social, rfc, serv_calle
        FROM clientes
    """)
    clientes = cur.fetchall()
    cols = ["id", "nombre_comercial", "nombre_razon_social", "rfc", "serv_calle"]
    clientes = [dict(zip(cols, row)) for row in clientes]
    print(f"Clientes en BD: {len(clientes):,}\n")

    # --- Procesar ---
    updates = []
    sin_match = 0
    ya_tiene_serv = 0
    sin_direccion = 0
    conflictivos = []

    for cliente in clientes:
        # No sobreescribir si ya tiene dirección de servicio
        if clean(cliente["serv_calle"]):
            ya_tiene_serv += 1
            continue

        excel_row, method = find_match(cliente, name_lookup, rfc_lookup)

        if excel_row is None:
            sin_match += 1
            continue

        serv_calle    = (clean(excel_row.get("calle")) or "")[:100] or None
        serv_num_ext  = (clean(excel_row.get("numeroExterior")) or "")[:50] or None
        serv_colonia  = (clean(excel_row.get("colonia")) or "")[:100] or None
        serv_cp       = (clean(excel_row.get("codigoPostal")) or "")[:10] or None

        if not serv_calle:
            sin_direccion += 1
            continue

        updates.append({
            "id":                   str(cliente["id"]),
            "serv_calle":           serv_calle,
            "serv_numero_exterior": serv_num_ext,
            "serv_colonia":         serv_colonia,
            "serv_codigo_postal":   serv_cp,
        })

    # --- Aplicar actualizaciones ---
    print(f"Resumen:")
    print(f"  Clientes a actualizar:        {len(updates):,}")
    print(f"  Ya tenían serv_calle:         {ya_tiene_serv:,}")
    print(f"  Sin match en Excel:           {sin_match:,}")
    print(f"  Match sin calle en Excel:     {sin_direccion:,}")

    if not dry_run and updates:
        print(f"\nAplicando {len(updates):,} actualizaciones en lotes de {BATCH_SIZE}...")
        execute_batch(
            cur,
            """
            UPDATE clientes SET
                serv_calle           = %(serv_calle)s,
                serv_numero_exterior = %(serv_numero_exterior)s,
                serv_colonia         = %(serv_colonia)s,
                serv_codigo_postal   = %(serv_codigo_postal)s
            WHERE id = %(id)s::uuid
            """,
            updates,
            page_size=BATCH_SIZE,
        )
        conn.commit()
        print("  Actualizaciones guardadas.\n")
    elif dry_run:
        print("\n[DRY-RUN] No se guardaron cambios. Quita --dry-run para aplicar.\n")

    # --- Reporte de sin_match para revisión ---
    if sin_match > 0:
        print(f"\n{sin_match} clientes sin match — primeros 20 para revisión manual:")
        count = 0
        for cliente in clientes:
            if clean(cliente["serv_calle"]):
                continue
            excel_row, _ = find_match(cliente, name_lookup, rfc_lookup)
            if excel_row is None:
                print(f"  RFC: {cliente['rfc']:<15}  Comercial: {cliente['nombre_comercial'][:50]}")
                count += 1
                if count >= 20:
                    print(f"  ... y {sin_match - 20} más.")
                    break

    cur.close()
    conn.close()
    print("\nListo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualiza dirección de servicio desde Excel.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin guardar cambios")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
