# Manual de Despliegue: Ambientes de Desarrollo y Producción

Este proyecto está configurado para permitir la ejecución simultánea de dos ambientes aislados en la misma máquina: **Desarrollo (Dev)** y **Producción (Prod)**.

Cada ambiente tiene su propia base de datos, puerto de API y puerto de aplicación Frontend.

---

## 🏗️ Resumen de Puertos

| Servicio | Desarrollo (Dev) | Producción (Prod) |
| :--- | :--- | :--- |
| **Frontend** | `http://localhost:3000` | `http://localhost:3001` |
| **Backend API** | `http://localhost:8000` | `http://localhost:8001` |
| **Base de Datos** | `5432` | `5433` |
| **Volumen Datos** | `pgdata` | `pgdata_prod` |

---

## 🛠️ Configuración Inicial (Solo una vez)

Antes de iniciar el ambiente de Producción por primera vez, asegúrate de haber configurado las variables de entorno.

### 1. Backend
Crea o edita el archivo `backend/.env.prod` (basado en el template entregado) con tus secretos de producción.

```bash
# Ejemplo de contenido en backend/.env.prod
DATABASE_URL=postgresql://postgres:postgres@db:5432/app_prod
SECRET_KEY=TU_CLAVE_SECRETA_PROD
...
```

### 2. Frontend
Crea el archivo `frontend-erp/.env.production` para que apunte al puerto correcto de la API.

```bash
# Contenido de frontend-erp/.env.production
NEXT_PUBLIC_API_URL=http://localhost:8001/api
```

---

## 🚀 Ejecución de Ambientes

### Opción A: Ambiente de Desarrollo
Utilizado para programar y probar cambios sin afectar datos reales.

**1. Backend (Dev)**
```bash
cd backend
docker compose up -d
```
*Esto levantará la API en el puerto 8000 y la DB en el 5432.*

**2. Frontend (Dev)**
```bash
cd frontend-erp
npm run dev
```
*Accesible en [http://localhost:3000](http://localhost:3000).*

---

### Opción B: Ambiente de Producción
Utilizado para la operación real del negocio. Los datos se guardan en un volumen separado (`pgdata_prod`).

**1. Backend (Prod)**
```bash
cd backend
# Usamos el flag -p para darle un nombre de proyecto distinto y evitar conflictos
docker compose -f docker-compose.prod.yml -p crm_prod up -d
```
*Esto levantará la API en el puerto 8001 y la DB en el 5433.*

**2. Frontend (Prod)**
```bash
cd frontend-erp
# Primero construimos la versión optimizada para Producción (carpeta .next_prod)
npm run build:prod
# Luego iniciamos el servidor en el puerto 3001
npm run start:prod
```
*Accesible en [http://localhost:3001](http://localhost:3001).*

---

## 🔄 Comandos Útiles

### Ver logs
```bash
# Desarrollo
docker compose logs -f backend

# Producción
docker compose -p crm_prod -f docker-compose.prod.yml logs -f backend
```

### Detener servicios
```bash
# Desarrollo
docker compose down

# Producción
docker compose -p crm_prod -f docker-compose.prod.yml down
```

---

## 🔄 Ciclo de Trabajo: De Desarrollo a Producción

Este es el flujo recomendado para trabajar en nuevas funcionalidades y luego publicarlas.

### 1. Desarrollo (Local)
Trabaja en tu entorno de desarrollo (Puertos 3000/8000).
*   Haz cambios en el código.
*   Prueba que todo funcione.

### 2. Pasar a Producción
Una vez que tus cambios estén listos y probados en Dev, sigue estos pasos para actualizar Producción.

**A. Actualizar Backend**
*   **Si solo cambiaste código (Python):**
    ```bash
    cd backend
    docker compose -p crm_prod -f docker-compose.prod.yml restart backend
    ```
*   **Si agregaste librerías (requirements.txt):**
    ```bash
    cd backend
    docker compose -p crm_prod -f docker-compose.prod.yml up -d --build backend
    ```

**B. Actualizar Frontend**
Siempre debes reconstruir la aplicación para que incluya los cambios visuales y de lógica.
```bash
cd frontend-erp
npm run build:prod
npm run start:prod
```

---

## 🌐 Exponer a Internet (Cloudflare Tunnel)

Para que el sistema sea accesible desde `https://app.sistemas-erp.com` sin abrir puertos.

### Configuración (Ya realizada)
Hemos creado un archivo de configuración `cloudflared_config.yml` y configurado los DNS para tu dominio.

### 🚀 Cómo Iniciar el Acceso Remoto
Cada vez que reinicies tu computadora o quieras activar el acceso externo, abre una terminal en la carpeta del proyecto y ejecuta:

```bash
# Usa la ruta absoluta para evitar errores
cloudflared tunnel --config /Users/alonso/Documents/Desarrollo/proyecto-crm/cloudflared_config.yml run
```

*Deberás ver logs indicando que las conexiones están activas.*

### URLs de Acceso
*   **Sistema (Usuarios):** `https://app.sistemas-erp.com`
*   **API (Backend):** `https://api.sistemas-erp.com` (Uso interno del sistema)

---

## ⚡ Opción 2: Sin Dominio (Solo Red Local/VPN)

Si decides no usar el dominio, puedes usar **Tailscale**.
1.  Instala Tailscale en el servidor y en tu celular/laptop.
2.  Accede usando la IP de Tailscale del servidor: `http://100.x.y.z:3001`.



---

## ❓ Solución de Problemas Comunes

### 1. Error "Network Error" o "CORS" al hacer login
*   **Causa**: El Backend rechazó la conexión porque el dominio público (ej: `app.sistemas-erp.com`) no está en la lista blanca.
*   **Solución**:
    1.  Edita `backend/app/config.py`.
    2.  Agrega tu dominio (con `https://`) a la lista `ALLOWED_ORIGINS`.
    3.  Reinicia el backend.

### 2. Error 400 / Mixed Content / Redirecciones a HTTP
*   **Causa**: El Backend (Uvicorn) no sabe que está detrás de Cloudflare (HTTPS) y trata las peticiones como inseguras (HTTP).
*   **Solución**:
    Asegúrate de que en `docker-compose.prod.yml` el comando de inicio incluya:
    ```yaml
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
    ```
    Esto fuerza al servidor a confiar en los encabezados seguros del proxy.

### 3. Error "ModuleNotFoundError" tras actualizar código
*   **Causa**: Agregaste librerías nuevas al `requirements.txt` pero solo reiniciaste el contenedor.
*   **Solución**: Reconstruye el contenedor:
    ```bash
    docker compose -p crm_prod -f docker-compose.prod.yml up -d --build backend
    ```
