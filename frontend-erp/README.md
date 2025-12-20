# Sistema CRM/ERP - Frontend

Plataforma unificada para la gestión integral de Clientes, Facturación 4.0, Cobranza y Gastos.

## 🚀 Características Principales

### 👥 Gestión de Clientes
- **Validación Fiscal**: Carga automática de datos mediante escaneo de Constancia de Situación Fiscal (PDF).
- **Expediente Digital**: Historial completo de ventas y saldos por cliente.

### 📦 Productos y Servicios
- **Catálogo Inteligente**: Búsqueda por descripción, clave interna o clave SAT.
- **Autocompletado**: Filtros rápidos tipo "Google" para encontrar items en segundos.

### 🧾 Facturación 4.0 (CFDI)
- **Timbrado Nativo**: Integración directa con PAC para generación de XML y PDF.
- **Validación en Tiempo Real**: Prevención de errores fiscales antes de timbrar.
- **Envío Automático**: Envío de facturas por correo a múltiples destinatarios.
- **Duplicación**: "Clonado" de facturas previas para agilizar la captura recurrente.

### 🧠 Navegación Inteligente (Filter Context)
- **Persistencia de Búsquedas**: El sistema "recuerda" tus filtros (fechas, clientes, estatus) mientras navegas entre pantallas.
- **Sesión Limpia**: Al cerrar sesión, todos los filtros se reinician automáticamente por seguridad y comodidad.

### 📊 Finanzas
- **Cobranza (REP)**: Generación de complementos de pago (Recibo Electrónico de Pagos).
- **Control de Gastos**: Registro de egresos con categorías y evidencias adjuntas.

## 🛠 Tecnologías

- **Framework**: Next.js 14 (React)
- **UI Library**: Ant Design 5 (con ConfigProvider para temas dinámicos)
- **Estado Global**: React Context API
- **Cliente HTTP**: Axios (con interceptores para manejo de tokens)
- **Estilos**: CSS Modules + Ant Design Token System

## 📦 Instalación y Despliegue

1. **Instalar dependencias**:
   ```bash
   npm install
   ```

2. **Modo Desarrollo**:
   ```bash
   npm run dev
   ```

3. **Producción**:
   ```bash
   npm run build
   npm start
   ```

## 🌙 Personalización
El sistema incluye un **selector de tema** en la barra lateral que permite:
- Alternar entre **Modo Claro / Oscuro**.
- Ajustar el **Tamaño de Fuente** globalmente (A-, A, A+, A++) para accesibilidad.

---
*Desarrollado para optimizar el flujo operativo y fiscal de la empresa.*
