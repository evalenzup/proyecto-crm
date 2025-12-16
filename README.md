# Desarrollo NORTON — ERP/CRM Unificado

## Descripción

**Desarrollo NORTON** es un sistema **ERP/CRM** que integra tres líneas de negocio:

* **Fumigaciones**
* **Jardinería**
* **Extintores**

Ofrece módulos para:

*   **Empresas** (multitenant con control de acceso por compañía)
*   **Clientes** (con gestión de contactos, direcciones y datos fiscales)
*   **Productos y Servicios**
*   **Facturación Electrónica** (CFDI 4.0) - *En desarrollo*
*   **Cotizaciones** y **Egresos** - *En desarrollo*
*   **Inventarios** (entradas/salidas de stock y ajustes automáticos) - *En desarrollo*
*   **Calendarización de Servicios** (rutas, alertas y asignación de técnicos) - *En desarrollo*
*   **Roles y Privilegios** (autenticación JWT y permisos por empresa)

---

## Tecnologías

| **Capa**     | **Tecnologías**                                                  |
| ------------ | ---------------------------------------------------------------- |
| **Backend**  | FastAPI, SQLAlchemy, Pydantic, PostgreSQL, Alembic, Docker       |
| **Frontend** | Next.js, React, TypeScript, Ant Design Pro, JSON-Schema dinámico |
| **DevOps**   | GitHub (Git, CI/CD), Docker Compose                              |

---

## Estructura del Proyecto

```txt
proyecto-desarrollo-norton/
├── backend/
│   ├── alembic/                  # Migraciones de esquema
│   ├── app/
│   │   ├── api/                  # Routers REST (Clientes, Empresas, Productos)
│   │   ├── auth/                 # JWT y seguridad
│   │   ├── catalogos_sat/        # Catálogos SAT
│   │   ├── config.py             # Settings Pydantic
│   │   ├── core/logger.py        # Logging centralizado
│   │   ├── database.py           # Conexión y sesión
│   │   ├── exception_handlers.py # Manejadores de errores
│   │   ├── models/               # Modelos SQLAlchemy
│   │   ├── schemas/              # Esquemas Pydantic (con schemas comunes)
│   │   ├── services/             # Lógica de negocio (Cliente, Empresa, Producto)
│   │   └── validators/           # Validaciones (RFC, email, etc.)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── tests/                    # Pruebas unitarias e integración
└── frontend-erp/
    ├── next.config.ts
    ├── package.json
    ├── public/
    └── src/
        ├── lib/axios.ts                   # Cliente HTTP
        ├── hooks/useDebouncedOptions.ts   # Autocompletado SAT
        ├── components/                    # Layout, Breadcrumb, FormRenderer…
        └── pages/
            ├── empresas/
            │   ├── index.tsx
            │   └── form/[[...id]].tsx      # Crear/Editar empresas
            ├── clientes/
            │   ├── index.tsx
            │   └── form/[[...id]].tsx      # Crear/Editar clientes
            └── productos-servicios/
                ├── index.tsx
                └── form/[[...id]].tsx      # Crear/Editar productos y servicios
```

---

## Requisitos Previos

1.  Docker y Docker Compose
2.  Git
3.  Python 3.10+
4.  Node.js ≥ 16 y npm

> **Nota para Despliegue**: Para instrucciones detalladas sobre cómo ejecutar ambientes de **Desarrollo** y **Producción** simultáneamente, consulta el [Manual de Despliegue](./MANUAL_DESPLIEGUE.md).

---

## Instalación y Configuración

### 1. Clonar repositorio

```bash
git clone https://github.com/evalenzup/proyecto-crm.git
cd proyecto-crm
```

### 2. Variables de entorno

#### Backend (`backend/.env`)

```ini
# Core
DATABASE_URL=postgresql://postgres:postgres@db:5432/norton_db
SECRET_KEY=tu_super_secreto
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Cifrado de datos sensibles (requerido por EmailConfig)
# Genera con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=coloca_aqui_tu_clave_fernet

# Rutas de datos/archivos
DATA_DIR=/data
CERT_DIR=/data/certificados

# (Opcional) Credenciales/endpoint del PAC (Facturación Moderna)
# FM_USER_ID=
# FM_USER_PASS=
# FM_TIMBRADO_URL=http://t1.facturacionmoderna.com/timbrado/soap
```

#### Frontend ERP (`frontend-erp/.env.local`)

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

#### Frontend corporativo (`frontend-corporativo/.env`)

```ini
VITE_API_URL=http://localhost:8000/api
```

### 3. Levantar servicios con Docker Compose

```bash
cd backend
docker-compose up --build
```

*   **Backend**: `http://localhost:8000` (Swagger: `/docs`)
*   **Frontend**: `http://localhost:3000`

### 4. Instalar dependencias Frontend

```bash
cd frontend-erp
npm install
npm run dev
```

---

## Pruebas

```bash
cd backend
pytest
```

---

## Roadmap y Próximos Pasos

*   **Inventario**: Finalizar endpoints de entradas/salidas y ajuste de stock.
*   **Facturación CFDI 4.0**: Implementar la generación de comprobantes, timbrado y manejo de impuestos.
*   **Calendarización**: Desarrollar el módulo de gestión de rutas, alertas y asignación de técnicos a servicios.
*   **Seguridad Multitenant**: Refinar los roles y permisos para asegurar el aislamiento de datos por empresa.
*   **Dashboard**: Crear un panel de control con métricas y KPIs relevantes.

---

## Contribuciones

1.  Fork del repositorio
2.  Nueva rama `feature/tu-funcionalidad`
3.  Commits descriptivos
4.  Pull Request con descripción del aporte

---

## Licencia

Uso interno para Norton. No redistribuir sin autorización.

---

## Contacto

**Email:** [evalenzup@cicese.edu.mx](mailto:evalenzup@cicese.edu.mx)
