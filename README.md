# 🚀 Proyecto CRM de Facturación

Sistema integral para la **gestión de clientes, facturación electrónica CFDI 4.0, inventarios y control de servicios** para pequeñas y medianas empresas.

Desarrollado con:
- **Backend:** FastAPI + PostgreSQL + Docker
- **Frontend:** React + Tailwind (TailAdmin) + Vite
- **Control de versiones:** Git + GitHub

---

## 📂 Estructura del proyecto

proyecto-crm/
├── backend/
├── frontend-corporativo/
└── README.md


---

## ⚙️ Requisitos previos

- Docker y Docker Compose instalados
- Git instalado
- Node.js (v18 o superior recomendado) y npm para el frontend

---

## 🛠️ Instalación del Backend

1️⃣ Ve a la carpeta del backend:
```bash
cd backend
2️⃣ Levanta el backend con PostgreSQL usando Docker:

docker compose up --build
3️⃣ Accede a la API en:

http://localhost:8000/docs (Swagger)
http://localhost:8000 (API base)
Las tablas se crearán automáticamente al iniciar por primera vez.

💻 Instalación del Frontend

1️⃣ Ve a la carpeta del frontend:

cd frontend-corporativo
2️⃣ Instala dependencias:

npm install
3️⃣ Inicia el servidor de desarrollo:

npm run dev
4️⃣ Accede en:
http://localhost:5173

🗂️ Variables de entorno

En backend/.env, configura:

DATABASE_URL=postgresql://postgres:postgres@db:5432/app
SECRET_KEY=supersecreto
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
🧪 Flujo de desarrollo

Utiliza ramas dev y feature antes de subir cambios a main.
Para nuevos módulos (clientes, facturación, reportes), usa commits claros.
Puedes probar el backend con Postman o Swagger.
El frontend consume los endpoints expuestos por FastAPI.
🚀 Despliegue

Backend:

Desplegable en un VPS con Docker.
Frontend:

Desplegable en Vercel o Netlify, conectando este repositorio.
🤝 Contribuciones

Haz un fork del repositorio.
Crea una rama feature/mi-funcionalidad.
Realiza tus cambios.
Haz un Pull Request con una descripción clara.
🛡️ Licencia

Proyecto de uso interno para Alonso.

📞 Contacto

Para soporte o colaboración:

Correo: evalenzup@cicese.edu.mx
¡Gracias por utilizar y contribuir a este CRM de Facturación 🚀!
