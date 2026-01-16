#!/bin/bash

# Configuration
PROD_CONTAINER="crm_prod-db-1"
DEV_CONTAINER="backend-db-1"
PROD_DB_USER="postgres"
PROD_DB_NAME="app_prod"
DEV_DB_USER="postgres"
DEV_DB_NAME="app"

echo "==================================================="
echo "   CLONAR BD: LOCAL PRODUCCIÓN -> LOCAL DESARROLLO"
echo "==================================================="
echo "Contenedor Origen (Prod): $PROD_CONTAINER"
echo "Contenedor Destino (Dev): $DEV_CONTAINER"
echo ""
echo "ADVERTENCIA: Se borrarán TODOS los datos en la base de Desarrollo '$DEV_DB_NAME'."
echo "---------------------------------------------------"
read -p "¿Estás seguro de continuar? (s/N): " CONFIRM
if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
    echo "Operación cancelada."
    exit 1
fi

echo ""
echo "1. Comprobando contenedores..."

if ! docker ps | grep -q "$PROD_CONTAINER"; then
    echo "❌ Error: El contenedor de Producción '$PROD_CONTAINER' no está corriendo."
    exit 1
fi

if ! docker ps | grep -q "$DEV_CONTAINER"; then
    echo "❌ Error: El contenedor de Desarrollo '$DEV_CONTAINER' no está corriendo."
    exit 1
fi

echo "✅ Contenedores activos."

echo "2. Iniciando Clonación (Pipe Directo)..."
echo "   Dump -> Restore en progreso..."

# Command Explanation:
# 1. docker exec PROD pg_dump ... : Dumps the prod DB to stdout
# 2. docker exec -i DEV psql ...  : Reads from stdin and restores to dev DB
# Note: We use -U postgres which usually has trust auth in docker images, or defaults.
# If password is needed inside container, usually PGPASSWORD env var works, but postgres image defaults often allow local root.

docker exec "$PROD_CONTAINER" pg_dump -U "$PROD_DB_USER" --clean --if-exists --no-owner --no-acl "$PROD_DB_NAME" \
| docker exec -i "$DEV_CONTAINER" psql -U "$DEV_DB_USER" -d "$DEV_DB_NAME"

STATUS=$?
echo ""
if [ $STATUS -eq 0 ]; then
    echo "✅ Clonación exitosa. La base de datos de Desarrollo ahora tiene los datos de Producción."
else
    echo "❌ Ocurrió un error en el proceso. Verifica los logs arriba."
fi
