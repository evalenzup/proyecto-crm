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
4.  Inicia los servicios (esto creará una base de datos vacía):
    ```bash
    docker compose up -d --build
    ```
5.  Espera unos segundos a que la base de datos arranque correctamente.

## 4. Restaurar la Información

Ahora vamos a cargar el respaldo que hicimos en el paso 1 dentro de la nueva base de datos vacía.

1.  En la misma terminal (carpeta `backend`), ejecuta:
    ```bash
    cat respaldo_completo.sql | docker compose exec -T db psql -U postgres app
    ```

**¡Listo!**
Ahora tu nueva computadora tiene el proyecto corriendo con exactamente los mismos datos, usuarios, logos y certificados que la anterior.
