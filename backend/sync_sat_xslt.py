#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sync_sat_xslt.py
Descarga hojas XSLT del SAT y construye el mirror local en:
  data/sat/sitio_internet/cfd/...
Además deja una copia "short" (solo nombre) en data/sat/ para el fallback.

Uso:
  python sync_sat_xslt.py
Opcional:
  SAT_BASE=/otra/ruta python sync_sat_xslt.py
"""

from __future__ import annotations
import os
import sys
import time
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urljoin

try:
    import requests
except Exception:
    print("Instala requests: pip install requests")
    sys.exit(1)

SAT_HOST = "http://www.sat.gob.mx/"
BASE_ENV  = os.environ.get("SAT_BASE", "data/sat")
BASE_DIR  = Path(BASE_ENV).resolve()
LONG_ROOT = BASE_DIR / "sitio_internet" / "cfd"  # raíz del mirror
SHORT_DIR = BASE_DIR                               # copias “short”

# Manifest: { url_path_relativo: ruta_relativa_destino_bajo LONG_ROOT }
# (todas estas rutas aparecen en los includes del XSLT 2.0 o son muy comunes)
MANIFEST: Dict[str, str] = {
    # Cadena Original
    "sitio_internet/cfd/4/cadenaoriginal_4_0.xslt": "4/cadenaoriginal_4_0.xslt",
    "sitio_internet/cfd/2/cadenaoriginal_2_0/utilerias.xslt": "2/cadenaoriginal_2_0/utilerias.xslt",

    # TFD 1.1 (cadena original del timbre)
    # Hay distintas ubicaciones publicadas históricamente; añadimos 2 opciones:
    "sitio_internet/cfd/tfd/1.1/cadenaoriginal_TFD_1_1.xslt": "tfd/1.1/cadenaoriginal_TFD_1_1.xslt",
    "sitio_internet/cfd/tfd/1_1/cadenaoriginal_TFD_1_1.xslt": "tfd/1_1/cadenaoriginal_TFD_1_1.xslt",

    # Complementos (los que te salieron en logs)
    "sitio_internet/cfd/donat/donat11.xslt": "donat/donat11.xslt",
    "sitio_internet/cfd/divisas/divisas.xslt": "divisas/divisas.xslt",
    "sitio_internet/cfd/implocal/implocal.xslt": "implocal/implocal.xslt",
    "sitio_internet/cfd/leyendasFiscales/leyendasFisc.xslt": "leyendasFiscales/leyendasFisc.xslt",
    "sitio_internet/cfd/pfic/pfic.xslt": "pfic/pfic.xslt",
    "sitio_internet/cfd/TuristaPasajeroExtranjero/TuristaPasajeroExtranjero.xslt": "TuristaPasajeroExtranjero/TuristaPasajeroExtranjero.xslt",
    "sitio_internet/cfd/nomina/nomina12.xslt": "nomina/nomina12.xslt",
    "sitio_internet/cfd/cfdiregistrofiscal/cfdiregistrofiscal.xslt": "cfdiregistrofiscal/cfdiregistrofiscal.xslt",
    "sitio_internet/cfd/pagoenespecie/pagoenespecie.xslt": "pagoenespecie/pagoenespecie.xslt",
    "sitio_internet/cfd/aerolineas/aerolineas.xslt": "aerolineas/aerolineas.xslt",
    "sitio_internet/cfd/valesdedespensa/valesdedespensa.xslt": "valesdedespensa/valesdedespensa.xslt",
    "sitio_internet/cfd/notariospublicos/notariospublicos.xslt": "notariospublicos/notariospublicos.xslt",
    "sitio_internet/cfd/vehiculousado/vehiculousado.xslt": "vehiculousado/vehiculousado.xslt",
    "sitio_internet/cfd/servicioparcialconstruccion/servicioparcialconstruccion.xslt": "servicioparcialconstruccion/servicioparcialconstruccion.xslt",
    "sitio_internet/cfd/renovacionysustitucionvehiculos/renovacionysustitucionvehiculos.xslt": "renovacionysustitucionvehiculos/renovacionysustitucionvehiculos.xslt",
    "sitio_internet/cfd/certificadodestruccion/certificadodedestruccion.xslt": "certificadodestruccion/certificadodedestruccion.xslt",
    "sitio_internet/cfd/arteantiguedades/obrasarteantiguedades.xslt": "arteantiguedades/obrasarteantiguedades.xslt",
    "sitio_internet/cfd/ComercioExterior11/ComercioExterior11.xslt": "ComercioExterior11/ComercioExterior11.xslt",
    "sitio_internet/cfd/ComercioExterior20/ComercioExterior20.xslt": "ComercioExterior20/ComercioExterior20.xslt",
    "sitio_internet/cfd/ine/ine11.xslt": "ine/ine11.xslt",
    "sitio_internet/cfd/iedu/iedu.xslt": "iedu/iedu.xslt",
    "sitio_internet/cfd/ventavehiculos/ventavehiculos11.xslt": "ventavehiculos/ventavehiculos11.xslt",
    "sitio_internet/cfd/detallista/detallista.xslt": "detallista/detallista.xslt",
    "sitio_internet/cfd/EstadoDeCuentaCombustible/ecc12.xslt": "EstadoDeCuentaCombustible/ecc12.xslt",
    "sitio_internet/cfd/consumodecombustibles/consumodeCombustibles11.xslt": "consumodecombustibles/consumodeCombustibles11.xslt",
    "sitio_internet/cfd/GastosHidrocarburos10/GastosHidrocarburos10.xslt": "GastosHidrocarburos10/GastosHidrocarburos10.xslt",
    "sitio_internet/cfd/IngresosHidrocarburos10/IngresosHidrocarburos.xslt": "IngresosHidrocarburos10/IngresosHidrocarburos.xslt",
    "sitio_internet/cfd/CartaPorte/CartaPorte20.xslt": "CartaPorte/CartaPorte20.xslt",
    "sitio_internet/cfd/CartaPorte/CartaPorte30.xslt": "CartaPorte/CartaPorte30.xslt",
    "sitio_internet/cfd/CartaPorte/CartaPorte31.xslt": "CartaPorte/CartaPorte31.xslt",
    "sitio_internet/cfd/Pagos/Pagos20.xslt": "Pagos/Pagos20.xslt",
}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "sat-xslt-sync/1.0"})

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def download(url: str, dest: Path, retries: int = 2, timeout: int = 20) -> Tuple[bool, str]:
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            with SESSION.get(url, stream=True, timeout=timeout) as r:
                if r.status_code != 200:
                    return False, f"HTTP {r.status_code}"
                ensure_dir(dest.parent)
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 14):
                        if chunk:
                            f.write(chunk)
            tmp.replace(dest)
            return True, "OK"
        except Exception as e:
            if attempt == retries:
                return False, f"{type(e).__name__}: {e}"
            time.sleep(1.0)
    return False, "unknown"

def copy_short(dest_long: Path):
    """Copia también al SHORT_DIR con el puro nombre del archivo si no existe o cambió."""
    short = SHORT_DIR / dest_long.name
    try:
        ensure_dir(short.parent)
        if short.exists():
            if sha256_of(short) == sha256_of(dest_long):
                return
        shutil.copy2(dest_long, short)
    except Exception:
        pass

def main() -> int:
    print(f"Mirror base: {BASE_DIR}")
    print(f"Long root  : {LONG_ROOT}")
    print(f"Short dir  : {SHORT_DIR}")
    ensure_dir(LONG_ROOT)
    ensure_dir(SHORT_DIR)

    ok = 0
    fail = 0

    for rel_url, rel_dest in MANIFEST.items():
        url  = urljoin(SAT_HOST, rel_url)
        dest = LONG_ROOT / rel_dest
        print(f"- {url} -> {dest}")
        success, msg = download(url, dest)
        if success:
            try:
                size = dest.stat().st_size
                hashp = sha256_of(dest)
                print(f"  ✓ descargado  ({size} bytes, sha256:{hashp})")
            except Exception:
                print("  ✓ descargado")
            copy_short(dest)
            ok += 1
        else:
            print(f"  ✗ error: {msg}")
            fail += 1

    print("\nResumen:")
    print(f"  OK   : {ok}")
    print(f"  ERROR: {fail}")
    print(f"\nSugerencia: si falta algún archivo adicional, agrégalo al MANIFEST.")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())