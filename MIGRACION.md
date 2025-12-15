# Guía de Migración del Proyecto CRM a otra Computadora

Para mover el proyecto a otro equipo conservando todos los datos (clientes, facturas, logos, certificados, configuración), sigue estos pasos:

## 1. En la Computadora ACTUAL (Origen)

Antes de copiar nada, necesitamos "extraer" la información de la base de datos, ya que esta vive dentro de Docker y no en una carpeta simple.

1.  Abre una terminal en la carpeta `backend` del proyecto.
2.  Ejecuta el siguiente comando para crear un respaldo:
    ```bash
    # Asegúrate de que el contenedor de base de datos esté corriendo
    docker compose exec -T db pg_dump -U postgres app > respaldo_completo.sql
    ```
    *Si usas `docker-compose` con guión, ajusta el comando.*

3.  Verifica que se haya creado el archivo `respaldo_completo.sql` en la carpeta `backend`.

## 2. Copiar los Archivos

Ahora copia **toda la carpeta principal del proyecto** (`proyecto-crm`) a una memoria USB, nube o transfiérela a la nueva computadora.

**¿Qué estás copiando?**
*   Todo el código fuente.
*   El archivo `respaldo_completo.sql` que acabamos de crear.
*   La carpeta `backend/data`: Aquí van los **Logos** y **Certificados** (CSD) que subiste. ¡Importante no perderla!
*   El archivo `backend/.env` con tus configuraciones.

## 3. En la Computadora NUEVA (Destino)

1.  Asegúrate de tener **Docker** y **Docker Compose** instalados.
2.  Pega la carpeta del proyecto.
3.  Abre una terminal en la carpeta `backend`.
4.  Inicia **SOLO** el servicio de base de datos y restaura (Método Robusto):
    ```bash
    # 1. Limpia cualquier intento fallido anterior
    docker compose down -v
    
    # 2. Inicia la base de datos
    docker compose up -d db
    
    # 3. Espera 10 segundos a que arranque
    sleep 10
    
    # 4. Copia el respaldo al contenedor (Más seguro que usar pipes)
    docker compose cp respaldo_completo.sql db:/tmp/respaldo.sql
    
    # 5. Ejecuta la restauración interna
    docker compose exec -T db psql -U postgres -d app -f /tmp/respaldo.sql
    ```

5.  **VERIFICACIÓN**: Antes de continuar, comprueba que las tablas existen ejecutando:
    ```bash
    docker compose exec -T db psql -U postgres -d app -c "\dt"
    ```
    *Deberías ver una lista de tablas como `clientes`, `usuarios`, etc.*

## 4. Finalizar

1.  Si la verificación fue exitosa, inicia el resto del sistema:
    ```bash
    docker compose up -d
    ```

2.  Una vez que termine la restauración (puede tardar unos segundos), inicia el resto del sistema backend:
    ```bash
    docker compose up -d
    ```

**¡Listo!**
Ahora tu nueva computadora tiene el proyecto corriendo con exactamente los mismos datos, usuarios, logos y certificados que la anterior.
