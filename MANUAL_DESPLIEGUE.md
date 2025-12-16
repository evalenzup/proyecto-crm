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
