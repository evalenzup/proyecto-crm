"""
backup_drive.py
---------------
Respalda la base de datos y archivos críticos a Google Drive.

  - BD: pg_dump diario completo (la BD cambia cada día, el dump es pequeño)
  - Archivos: incremental basado en manifest — solo sube archivos nuevos
    o modificados desde el último backup exitoso.

Manifest: data/secrets/backup_manifest.json
  { "cfdis/archivo.xml": "2026-05-15T14:05:00", ... }
  Si el manifest no existe o se pierde, sube todo desde cero.

Uso manual:
    python scripts/backup_drive.py

Variables de entorno:
    BACKUP_DB_NAME       Base de datos (default: app)
    BACKUP_DB_USER       Usuario PostgreSQL (default: postgres)
    BACKUP_DB_HOST       Host (default: db)
    BACKUP_DB_PORT       Puerto (default: 5432)
    BACKUP_DRIVE_FOLDER  ID carpeta Drive
    BACKUP_TOKEN_FILE    Ruta token OAuth2 (default: /app/data/secrets/drive_token.json)
    BACKUP_KEEP          Backups de BD a conservar en Drive (default: 30)
"""

import json
import os
import subprocess
import sys
import gzip
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

DB_NAME      = os.getenv("BACKUP_DB_NAME",      "app")
DB_USER      = os.getenv("BACKUP_DB_USER",      "postgres")
DB_HOST      = os.getenv("BACKUP_DB_HOST",      "db")
DB_PORT      = os.getenv("BACKUP_DB_PORT",      "5432")
DRIVE_FOLDER = os.getenv("BACKUP_DRIVE_FOLDER", "1Q-ASbDZA2AMUQGh1bq78B8Fng2Zhyzzr")
TOKEN_FILE   = os.getenv("BACKUP_TOKEN_FILE",   "/app/data/secrets/drive_token.json")
KEEP_LAST    = int(os.getenv("BACKUP_KEEP",     "30"))

TMP_DIR      = Path("/tmp/backups")
DATA_DIR     = Path("/app/data")
MANIFEST     = DATA_DIR / "secrets" / "backup_manifest.json"

# Subcarpetas a respaldar (excluye secrets y logs)
DATA_INCLUDE = [
    "certificados",
    "cfdis",
    "logos",
    "tecnicos_fotos",
    "presupuestos_evidencia",
    "pagos_comprobantes",
]

# ── Helpers generales ─────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def file_mtime(path: Path) -> str:
    """Devuelve la fecha de modificación como string ISO."""
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S")


# ── Manifest ──────────────────────────────────────────────────────────────────

def load_manifest() -> dict:
    """Carga el manifest existente o devuelve uno vacío."""
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except Exception:
            log("Manifest corrupto — se reconstruirá desde cero")
    return {}


def save_manifest(manifest: dict):
    """Guarda el manifest actualizado."""
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


# ── Google Drive ──────────────────────────────────────────────────────────────

def drive_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not Path(TOKEN_FILE).exists():
        raise FileNotFoundError(
            f"No se encontró el token OAuth2 en {TOKEN_FILE}. "
            "Ejecuta scripts/setup_drive_auth.py en tu Mac para generarlo."
        )

    token_data = json.loads(Path(TOKEN_FILE).read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )
    if not creds.valid:
        creds.refresh(Request())
        token_data["token"] = creds.token
        Path(TOKEN_FILE).write_text(json.dumps(token_data, indent=2))
        log("Token OAuth2 refrescado")

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_to_drive(service, file_path: Path, folder_id: str, mimetype: str) -> str:
    from googleapiclient.http import MediaFileUpload

    log(f"Subiendo → {file_path.name}")
    media = MediaFileUpload(str(file_path), mimetype=mimetype, resumable=True)
    uploaded = service.files().create(
        body={"name": file_path.name, "parents": [folder_id]},
        media_body=media,
        fields="id,name,size",
    ).execute()
    size_mb = int(uploaded.get("size", 0)) / 1_048_576
    log(f"  ✓ {uploaded['name']} ({size_mb:.2f} MB)")
    return uploaded["id"]


def rotate_old_db_backups(service, folder_id: str, keep: int):
    """Conserva solo los últimos N backups de BD en Drive."""
    result = service.files().list(
        q=f"'{folder_id}' in parents and name contains 'backup_db_' and trashed=false",
        orderBy="createdTime desc",
        fields="files(id, name)",
        pageSize=200,
    ).execute()
    files = result.get("files", [])
    to_delete = files[keep:]
    for f in to_delete:
        service.files().delete(fileId=f["id"]).execute()
        log(f"  Eliminado (rotación): {f['name']}")
    if to_delete:
        log(f"  {len(to_delete)} backup(s) antiguo(s) eliminados")


# ── Backup BD ─────────────────────────────────────────────────────────────────

def backup_database(service, timestamp: str):
    """pg_dump completo diario — la BD cambia cada día y el dump es pequeño."""
    log("--- Base de datos ---")
    dump_path = TMP_DIR / f"backup_db_{DB_NAME}_{timestamp}.sql"
    gz_path   = Path(str(dump_path) + ".gz")

    try:
        result = subprocess.run(
            ["pg_dump", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, DB_NAME],
            capture_output=True,
            env={**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres")},
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump falló: {result.stderr.decode()}")

        dump_path.write_bytes(result.stdout)

        with open(dump_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        size_mb = gz_path.stat().st_size / 1_048_576
        log(f"pg_dump listo: {gz_path.name} ({size_mb:.2f} MB)")

        upload_to_drive(service, gz_path, DRIVE_FOLDER, "application/gzip")
        rotate_old_db_backups(service, DRIVE_FOLDER, KEEP_LAST)

    finally:
        if dump_path.exists(): dump_path.unlink()
        if gz_path.exists():   gz_path.unlink()


# ── Backup incremental de archivos ────────────────────────────────────────────

def backup_data_files(service, timestamp: str):
    """Sube solo archivos nuevos o modificados desde el último backup."""
    log("--- Archivos data/ (incremental) ---")

    manifest    = load_manifest()
    new_manifest = dict(manifest)  # copia — solo se actualiza si el upload es exitoso
    pending     = []  # lista de (Path absoluta, clave relativa)

    # Detectar archivos nuevos o modificados
    for folder_name in DATA_INCLUDE:
        folder_path = DATA_DIR / folder_name
        if not folder_path.exists():
            continue
        for file_path in sorted(folder_path.rglob("*")):
            if not file_path.is_file():
                continue
            key   = f"{folder_name}/{file_path.relative_to(folder_path)}"
            mtime = file_mtime(file_path)
            if manifest.get(key) != mtime:
                pending.append((file_path, key, mtime))

    if not pending:
        log("Sin archivos nuevos o modificados — nada que subir")
        return

    log(f"{len(pending)} archivo(s) nuevo(s) o modificado(s) detectado(s)")

    # Empaquetar solo los archivos pendientes
    gz_path = TMP_DIR / f"backup_data_{timestamp}.tar.gz"
    try:
        with tarfile.open(gz_path, "w:gz") as tar:
            for file_path, key, _ in pending:
                tar.add(str(file_path), arcname=key)

        size_mb = gz_path.stat().st_size / 1_048_576
        log(f"Paquete incremental: {gz_path.name} ({size_mb:.2f} MB)")

        # Subir a Drive
        upload_to_drive(service, gz_path, DRIVE_FOLDER, "application/gzip")

        # Solo actualizar el manifest si el upload fue exitoso
        for _, key, mtime in pending:
            new_manifest[key] = mtime
        save_manifest(new_manifest)
        log(f"Manifest actualizado ({len(new_manifest)} archivos registrados)")

    finally:
        if gz_path.exists():
            gz_path.unlink()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("=== Inicio de backup ===")
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        svc = drive_service()
        backup_database(svc, timestamp)
        backup_data_files(svc, timestamp)
        log("=== Backup completado exitosamente ===")
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
