Desarrollo NORTON — ERP/CRM Unificado

📖 Descripción

Desarrollo NORTON es un sistema ERP/CRM que unifica tres líneas de negocio —fumigaciones, jardinería y extintores— en una plataforma centralizada, ofreciendo módulos para:
	•	Clientes y Empresas (multitenant con control de acceso por compañía)
	•	Facturación Electrónica (CFDI 4.0)
	•	Cotizaciones y Egresos
	•	Inventarios (entradas/salidas y ajuste automático de stock)
	•	Calendarización de Servicios (rutas, alertas y asignación de técnicos)
	•	Roles y Privilegios (autenticación JWT, permisos por empresa)

🚀 Tecnologías

Capa	Tecnologías
Backend	FastAPI, SQLAlchemy, Pydantic, PostgreSQL, Alembic, Docker, Docker Compose
Frontend	Next.js, React, TypeScript, Ant Design Pro, JSON-Schema dinámico
DevOps	GitHub (Git, CI/CD), Docker Compose

📂 Estructura del Proyecto

├── backend/
│   ├── alembic/                  # Migraciones de esquema
│   ├── app/
│   │   ├── api/                  # Routers REST (empresas, clientes, productos_servicios, inventario, calendarización, catálogos_sat, auth)
│   │   ├── auth/                 # JWT y seguridad
│   │   ├── catalogos_sat/        # Datos y endpoints SAT
│   │   ├── config.py             # Settings con Pydantic
│   │   ├── core/logger.py        # Logging centralizado
│   │   ├── database.py           # Conexión y sesión
│   │   ├── exception_handlers.py # Manejadores de errores
│   │   ├── models/               # Modelos SQLAlchemy
│   │   ├── schemas/              # Esquemas Pydantic
│   │   ├── services/             # Lógica de negocio extra (CertificadoService, sync)
│   │   └── validators/           # Validaciones (RFC, email, teléfono)
│   ├── sync_db_columns.py        # Script auto-sync de columnas y constraints
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── tests/                    # Pruebas unitarias e integración
└── frontend-erp/
    ├── next.config.ts
    ├── package.json
    ├── public/
    └── src/
        ├── lib/axios.ts                    # Cliente HTTP central
        ├── hooks/useDebouncedOptions.ts    # Autocompletado SAT
        ├── components/                     # Layout, Breadcrumb, FormRenderer…
        └── pages/
            ├── empresas/
            │   ├── index.tsx
            │   └── form/[[...id]].tsx       # Crear/Editar empresas
            └── productos-servicios/
                ├── index.tsx
                └── form/[[...id]].tsx     # Crear/Editar productos y servicios

⚙️ Requisitos Previos
	•	Docker y Docker Compose instalados.
	•	Git.
	•	Python 3.10+ y Node.js ≥ 16 con npm.

🛠️ Instalación y Configuración

1. Clonar el repositorio

git clone https://github.com/tu-org/desarrollo-norton.git
cd desarrollo-norton

2. Variables de entorno

Backend (backend/.env)

DATABASE_URL=postgresql://postgres:postgres@db:5432/norton_db
SECRET_KEY=tu_super_secreto
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CERTS_PATH=./certificados

Frontend (frontend-erp/.env.local)

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api

3. Levantar con Docker Compose

# Desde la raíz del proyecto:
docker-compose up --build

	•	Backend en http://localhost:8000 (Swagger UI: /docs).
	•	Frontend en http://localhost:3000.

4. Instalar dependencias Frontend

cd frontend-erp
npm install
npm run dev

🧪 Pruebas

Para ejecutar los tests del backend:

cd backend
pytest

📈 Roadmap y Próximos Pasos
	•	Inventario: endpoints de entradas/salidas y ajuste automático de stock.
	•	Facturación CFDI 4.0: generación de comprobantes con productos e impuestos.
	•	Calendarización: rutas, alertas y asignación de técnicos.
	•	Seguridad Multitenant: perfiles, roles y permisos por empresa.

🤝 Contribuciones
	1.	Haz un fork del repositorio.
	2.	Crea una rama feature/tu-funcionalidad.
	3.	Desarrolla tu función con commits claros.
	4.	Empuja tu rama y abre un Pull Request describiendo tu aporte.

🛡️ Licencia

Uso interno para Norton. No redistribuir sin autorización.

📞 Contacto

Para soporte o colaboración:
Email: evalenzup@gmail.com