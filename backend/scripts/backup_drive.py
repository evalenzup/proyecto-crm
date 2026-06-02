"""
backup_drive.py
---------------
Genera un pg_dump de la base de datos y lo sube a Google Drive.
Mantiene solo los últimos N backups en Drive (rotación automática).

Uso manual:
    python scripts/backup_drive.py

Variables de entorno requeridas (o defaults):
    BACKUP_DB_NAME       Base de datos a respaldar (default: app)
    BACKUP_DB_USER       Usuario PostgreSQL (default: postgres)
    BACKUP_DB_HOST       Host de PostgreSQL (default: db)
    BACKUP_DB_PORT       Puerto (default: 5432)
    BACKUP_DRIVE_FOLDER  ID de carpeta en Drive
    BACKUP_CREDENTIALS   Ruta al JSON de service account
    BACKUP_KEEP          Número de backups a conservar (default: 30)
"""

import os
import subprocess
import sys
import gzip
import shutil
from datetime import datetime
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

DB_NAME       = os.getenv("BACKUP_DB_NAME",      "app")
DB_USER       = os.getenv("BACKUP_DB_USER",      "postgres")
DB_HOST       = os.getenv("BACKUP_DB_HOST",      "db")
DB_PORT       = os.getenv("BACKUP_DB_PORT",      "5432")
DRIVE_FOLDER  = os.getenv("BACKUP_DRIVE_FOLDER", "1Q-ASbDZA2AMUQGh1bq78B8Fng2Zhyzzr")
TOKEN_FILE    = os.getenv("BACKUP_TOKEN_FILE",   "/app/data/secrets/drive_token.json")
KEEP_LAST     = int(os.getenv("BACKUP_KEEP",     "30"))
TMP_DIR       = Path("/tmp/backups")
DATA_DIR      = Path("/app/data")

# Subcarpetas de data/ a respaldar (excluye secrets y logs)
DATA_INCLUDE  = ["certificados", "cfdis", "logos", "tecnicos_fotos",
                 "presupuestos_evidencia", "pagos_comprobantes"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def drive_service():
    import json
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

    # Refrescar si expiró
    if not creds.valid:
        creds.refresh(Request())
        # Guardar token actualizado
        token_data["token"] = creds.token
        Path(TOKEN_FILE).write_text(json.dumps(token_data, indent=2))
        log("Token OAuth2 refrescado")

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def dump_database(output_path: Path) -> Path:
    """Ejecuta pg_dump y comprime el resultado en .gz"""
    dump_path = output_path.with_suffix(".sql")
    log(f"Ejecutando pg_dump → {dump_path.name}")

    result = subprocess.run(
        ["pg_dump", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, DB_NAME],
        capture_output=True,
        env={**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres")},
    )
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump falló: {result.stderr.decode()}")

    dump_path.write_bytes(result.stdout)

    gz_path = Path(str(dump_path) + ".gz")
    log(f"Comprimiendo → {gz_path.name}")
    with open(dump_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    dump_path.unlink()

    size_mb = gz_path.stat().st_size / 1_048_576
    log(f"Archivo listo: {gz_path.name} ({size_mb:.2f} MB)")
    return gz_path


def upload_to_drive(service, file_path: Path, folder_id: str) -> str:
    from googleapiclient.http import MediaFileUpload

    log(f"Subiendo a Google Drive (carpeta: {folder_id})")
    media = MediaFileUpload(str(file_path), mimetype="application/gzip", resumable=True)
    file_metadata = {"name": file_path.name, "parents": [folder_id]}

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name,size",
    ).execute()

    log(f"Subido correctamente: {uploaded['name']} (id={uploaded['id']})")
    return uploaded["id"]


def compress_data_folder(output_path: Path) -> Path:
    """Comprime las subcarpetas críticas de /app/data en un tar.gz"""
    import tarfile

    gz_path = Path(str(output_path) + ".tar.gz")
    log(f"Comprimiendo carpeta data/ → {gz_path.name}")

    with tarfile.open(gz_path, "w:gz") as tar:
        for folder_name in DATA_INCLUDE:
            folder_path = DATA_DIR / folder_name
            if folder_path.exists():
                tar.add(str(folder_path), arcname=folder_name)
                count = sum(1 for _ in folder_path.rglob("*") if _.is_file())
                log(f"  + {folder_name}/ ({count} archivos)")
            else:
                log(f"  - {folder_name}/ (no existe, omitido)")

    size_mb = gz_path.stat().st_size / 1_048_576
    log(f"Archivo data listo: {gz_path.name} ({size_mb:.2f} MB)")
    return gz_path


def rotate_old_backups(service, folder_id: str, keep: int):
    """Elimina backups antiguos en Drive, conservando solo los últimos `keep`."""
    log(f"Revisando backups en Drive (conservar últimos {keep})")

    result = service.files().list(
        q=f"'{folder_id}' in parents and name contains 'backup_' and trashed=false",
        orderBy="createdTime desc",
        fields="files(id, name, createdTime)",
        pageSize=200,
    ).execute()

    files = result.get("files", [])
    log(f"Backups existentes en Drive: {len(files)}")

    to_delete = files[keep:]
    for f in to_delete:
        service.files().delete(fileId=f["id"]).execute()
        log(f"Eliminado (rotación): {f['name']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("=== Inicio de backup ===")
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = TMP_DIR / f"backup_db_{DB_NAME}_{timestamp}.sql"
    data_file = TMP_DIR / f"backup_data_{timestamp}"
    gz_db     = Path(str(dump_file) + ".gz")
    gz_data   = Path(str(data_file) + ".tar.gz")

    try:
        svc = drive_service()

        # 1. Backup de base de datos
        log("--- Base de datos ---")
        gz_db = dump_database(dump_file)
        upload_to_drive(svc, gz_db, DRIVE_FOLDER)
        rotate_old_backups(svc, DRIVE_FOLDER, KEEP_LAST)

        # 2. Backup de archivos (certificados, cfdis, logos, etc.)
        log("--- Archivos data/ ---")
        gz_data = compress_data_folder(data_file)
        upload_to_drive(svc, gz_data, DRIVE_FOLDER)

        log("=== Backup completado exitosamente ===")

    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

    finally:
        for f in [gz_db, gz_data]:
            if f.exists():
                f.unlink()
        log("Archivos temporales eliminados")


if __name__ == "__main__":
    main()
