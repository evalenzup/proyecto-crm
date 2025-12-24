# ⚡ Guía de Reinicio Rápido (Personalizada)

Lista de comandos exactos para levantar tus ambientes después de un reinicio.

## 1. 🌐 Túnel Cloudflare
Para habilitar el acceso externo entrar a la carpeta del proyecto (proyecto-crm):
```bash
cloudflared tunnel --config cloudflared_config.yml run
```

---

## 2. 🛠️ Modo Desarrollo
Para trabajar localmente con cambios en caliente:

**Backend:**
Entrar a la carpeta del proyecto (proyecto-crm/backend)
```bash
# En terminal 1 (Raíz del proyecto)
docker-compose up --build
```

**Frontend:**
Entrar a la carpeta del proyecto (proyecto-crm/frontend-erp)
```bash
# En terminal 2 (Entrar a carpeta frontend-erp)
cd frontend-erp
npm run dev
```

---

## 3. 🚀 Modo Producción
Para desplegar la versión estable (como se usa en el servidor):

**Backend:**
Entrar a la carpeta del proyecto (proyecto-crm/backend)
```bash
# En terminal 1 (Raíz del proyecto)
docker compose -p crm_prod -f docker-compose.prod.yml up -d --force-recreate backend

# Ver logs (opcional, para confirmar que inició bien)
docker compose -p crm_prod -f docker-compose.prod.yml logs -f backend
```

**Frontend:**
Entrar a la carpeta del proyecto (proyecto-crm/frontend-erp)    
```bash
# En terminal 2 (Entrar a carpeta frontend-erp)
cd frontend-erp
npm run build:prod
npm run start:prod
```
