# Desarrollo NORTON — ERP/CRM Unificado

## Descripción

**Desarrollo NORTON** es un sistema **ERP/CRM** que integra tres líneas de negocio:

* **Fumigaciones**
* **Jardinería**
* **Extintores**

Ofrece módulos para:

* **Clientes** y **Empresas** (multitenant con control de acceso por compañía)
* **Facturación Electrónica** (CFDI 4.0)
* **Cotizaciones** y **Egresos**
* **Inventarios** (entradas/salidas de stock y ajustes automáticos)
* **Calendarización de Servicios** (rutas, alertas y asignación de técnicos)
* **Roles y Privilegios** (autenticación JWT y permisos por empresa)

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
│   │   ├── api/                  # Routers REST
│   │   ├── auth/                 # JWT y seguridad
│   │   ├── catalogos_sat/        # Catálogos SAT
│   │   ├── config.py             # Settings Pydantic
│   │   ├── core/logger.py        # Logging centralizado
│   │   ├── database.py           # Conexión y sesión
│   │   ├── exception_handlers.py # Manejadores de errores
│   │   ├── models/               # Modelos SQLAlchemy
│   │   ├── schemas/              # Esquemas Pydantic
│   │   ├── services/             # Lógica de negocio extra
│   │   └── validators/           # Validaciones (RFC, email, teléfono)
│   ├── sync_db_columns.py        # Sincronización automática
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
            └── productos-servicios/
                ├── index.tsx
                └── form/[[...id]].tsx      # Crear/Editar productos y servicios
```

---

## Requisitos Previos

1. Docker y Docker Compose
2. Git
3. Python 3.10+
4. Node.js ≥ 16 y npm

---

## Instalación y Configuración

### 1. Clonar repositorio

```bash
git clone https://github.com/tu-org/desarrollo-norton.git
cd desarrollo-norton
```

### 2. Variables de entorno

#### Backend (`backend/.env`)

```ini
DATABASE_URL=postgresql://postgres:postgres@db:5432/norton_db
SECRET_KEY=tu_super_secreto
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CERTS_PATH=./certificados
```

#### Frontend (`frontend-erp/.env.local`)

```ini
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### 3. Levantar servicios con Docker Compose

```bash
docker-compose up --build
```

* **Backend**: `http://localhost:8000` (Swagger: `/docs`)
* **Frontend**: `http://localhost:3000`

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

* **Inventario**: endpoints de entradas/salidas y ajuste de stock
* **Facturación CFDI 4.0**: generación de comprobantes e impuestos
* **Calendarización**: rutas, alertas y asignación de técnicos
* **Seguridad Multitenant**: roles y permisos por empresa

---

## Contribuciones

1. Fork del repositorio
2. Nueva rama `feature/tu-funcionalidad`
3. Commits descriptivos
4. Pull Request con descripción del aporte

---

## Licencia

Uso interno para Norton. No redistribuir sin autorización.

---

## Contacto

**Email:** [evalenzup@cicese.edu.mx](mailto:evalenzup@cicese.edu.mx)
