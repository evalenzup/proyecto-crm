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

## 🌐 Exponer a Internet (Opcional)

Si deseas acceder a tu entorno de Producción desde internet (fuera de tu red local), la forma más segura y gratuita es usar **Cloudflare Tunnel**. Esto evita tener que abrir puertos en tu router.

## 🌐 Exponer a Internet (Guía Paso a Paso con Cloudflare Tunnel)

Esta guía te permitirá acceder a tu sistema desde cualquier lugar sin abrir puertos en tu router, utilizando un dominio propio y la herramienta gratuita de Cloudflare.

### Prerrequisitos
1.  **Dominio**: Debes haber comprado un dominio (ej: `misistema.com`).
2.  **Cuenta Cloudflare**: Tu dominio debe estar gestionado por Cloudflare (cambia los NS en tu registrador).

### Paso 1: Instalar cloudflared
En esta Mac (donde corre el sistema), abre una terminal y ejecuta:

```bash
brew install cloudflared
```

### Paso 2: Autenticación
Vincula el agente con tu cuenta de Cloudflare:

```bash
cloudflared tunnel login
```
*Se abrirá una ventana del navegador. Selecciona tu dominio para autorizar.*

### Paso 3: Crear el Túnel
Crea un túnel con un nombre identificativo (ej: `crm-prod`):

```bash
cloudflared tunnel create crm-prod
```
*Copia el `Tunnel ID` que aparecerá en la salida (es una cadena larga tipo `UUID`).*

### Paso 4: Configurar los Subdominios (DNS)
Asigna subdominios a tu túnel. Ejecuta:

```bash
# Para el Frontend (lo que verán los usuarios)
cloudflared tunnel route dns crm-prod app.misistema.com

# Para el Backend (la API)
cloudflared tunnel route dns crm-prod api.misistema.com
```

### Paso 5: Crear Archivo de Configuración
Crea un archivo llamado `config.yml` en la carpeta `~/.cloudflared/` (o en tu carpeta de proyecto si prefieres invocarlo directamente):

```yaml
tunnel: <TU_TUNNEL_ID_DEL_PASO_3>
credentials-file: /Users/alonso/.cloudflared/<TU_TUNNEL_ID_DEL_PASO_3>.json

ingress:
  # Frontend
  - hostname: app.misistema.com
    service: http://localhost:3001
  # Backend
  - hostname: api.misistema.com
    service: http://localhost:8001
  # Regla por defecto (404)
  - service: http_status:404
```

### Paso 6: Ejecutar el Túnel
Para iniciar la conexión:

```bash
cloudflared tunnel run crm-prod
```

### Paso 7: Actualizar Frontend
Finalmente, como tu API ahora vivirá en `https://api.misistema.com`, debes reconstruir el Frontend de Producción:

1.  Edita `frontend-erp/package.json` y cambia la URL en el script `build:prod`:
    ```json
    "build:prod": "NEXT_PUBLIC_API_URL=https://api.misistema.com/api NEXT_DIST_DIR=.next_prod next build"
    ```
2.  Despliega de nuevo:
    ```bash
    npm run build:prod
    npm run start:prod
    ```

¡Listo! Ahora podrás entrar a `https://app.misistema.com` desde cualquier lugar.

---

## 🔒 Opción 2: Sin Dominio (Red Privada / Tailscale)

Si **NO** quieres comprar un dominio, puedes usar **Tailscale**. Esto crea una "red privada virtual" entre tus dispositivos.

### ¿Cómo funciona?
1.  Instalas Tailscale en esta Mac (Servidor).
2.  Instalas Tailscale en tu celular o laptop remota.
3.  Ambos dispositivos se "verán" como si estuvieran en la misma red WiFi, sin importar dónde estén.

### Pasos:
1.  Descarga e instala **Tailscale** (gratis para uso personal) en esta Mac desde `https://tailscale.com`.
2.  Loguéate y verás que te asigna una **IP Privada** (ej: `100.x.y.z`) y un **MagicDNS** (ej: `mac-studio`).
3.  En tu **Laptop Remota o Celular**, instala también Tailscale y usa la misma cuenta.
4.  Ahora podrás acceder al sistema usando la IP de Tailscale de la Mac:
    *   `http://100.x.y.z:3001` (o `http://mac-studio:3001`)

*Ventaja*: Seguridad total (solo tus dispositivos acceden).
*Desventaja*: Debes instalar la app en cada dispositivo que quiera entrar.

---

## ⚡ Opción 3: Rápido / Temporal (Tunnelmole)

Si solo necesitas mostrar el proyecto a alguien rápidamente y no quieres configurar cuentas ni instalar apps en el celular.

1.  **Instalar** (usando Node.js):
    ```bash
    npm install -g tunnelmole
    ```

2.  **Exponer Backend** (Terminal 1):
    ```bash
    tmole 8001
    # Copia la URL generada, ej: https://api-backend.tunnelmole.net
    ```

3.  **Exponer Frontend** (Terminal 2):
    ```bash
    tmole 3001
    # Copia la URL generada, ej: https://mi-frontend.tunnelmole.net
    ```

4.  **Conectar**:
    Para que funcione el login, debes reconstruir el frontend apuntando a la URL pública del backend (Paso 2):
    
    *Editar `frontend-erp/package.json`*:
    ```json
    "build:prod": "NEXT_PUBLIC_API_URL=https://api-backend.tunnelmole.net/api NEXT_DIST_DIR=.next_prod next build"
    ```
    
    *Reconstruir*:
    ```bash
    npm run build:prod
    npm run start:prod
    ```

Ahora entra a `https://mi-frontend.tunnelmole.net` desde cualquier navegador.

