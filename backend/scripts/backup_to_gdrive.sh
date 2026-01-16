#!/bin/bash

# ==============================================================================
# SCRIPT DE RESPALDO AUTOMÁTICO A GOOGLE DRIVE
# Requiere: docker, gzip, rclone configured
# ==============================================================================

# CONFIGURACIÓN
# ------------------------------------------------------------------------------
# Nombre del contenedor de la base de datos de producción
CONTAINER_NAME="crm_prod-db-1"

# Usuario y base de datos dentro del contenedor
DB_USER="postgres"
DB_NAME="app_prod"

# Configuración de Rclone
# "gdrive_backup" debe coincidir con el nombre que le diste al remoto en `rclone config`
RCLONE_REMOTE="gdrive_backup"
RCLONE_FOLDER="Backups_CRM"

# Directorio temporal local para guardar el dump antes de subir
LOCAL_BACKUP_DIR="/tmp/pg_backups"
mkdir -p "$LOCAL_BACKUP_DIR"

# Fecha para el nombre del archivo
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
FILENAME="backup_${DB_NAME}_${DATE}.sql.gz"
FULL_PATH="$LOCAL_BACKUP_DIR/$FILENAME"

# ==============================================================================

echo "[$(date)] Iniciando respaldo de $CONTAINER_NAME..."

# 1. VERIFICAR SI EL CONTENEDOR ESTÁ CORRIENDO
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Error: El contenedor '$CONTAINER_NAME' no está corriendo."
    exit 1
fi

# 2. GENERAR DUMP Y COMPRIMIR
# Usamos pipe | para no gastar espacio en disco con el .sql sin comprimir
echo "   - Extrayendo y comprimiendo base de datos..."
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" --clean --if-exists "$DB_NAME" | gzip > "$FULL_PATH"

if [ $? -ne 0 ]; then
    echo "❌ Error al generar el dump."
    rm -f "$FULL_PATH"
    exit 1
fi

SIZE=$(du -h "$FULL_PATH" | cut -f1)
echo "   ✅ Respaldo local creado: $FILENAME ($SIZE)"

# 3. SUBIR A GOOGLE DRIVE
echo "   - Subiendo a Google Drive ($RCLONE_REMOTE:$RCLONE_FOLDER)..."

rclone copy "$FULL_PATH" "$RCLONE_REMOTE:$RCLONE_FOLDER"

if [ $? -eq 0 ]; then
    echo "   ✅ Subida exitosa."
    # Eliminar el archivo local para no llenar el disco
    rm "$FULL_PATH"
    echo "   - Archivo local eliminado."
else
    echo "❌ Error al subir a Google Drive. El archivo local se mantiene en $FULL_PATH"
    exit 1
fi

# 4. LIMPIEZA DE ANTIGUOS (Retención de 30 días)
echo "   - Limpiando respaldos antiguos en Drive (> 30 días)..."
rclone delete "$RCLONE_REMOTE:$RCLONE_FOLDER" --min-age 30d

echo "[$(date)] Proceso finalizado correctamente."
echo "------------------------------------------------------------------------------"
