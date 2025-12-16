# Manual de Usuario - Sistema CRM/ERP

Bienvenido al manual operativo del sistema. Este documento describe las funciones principales para el uso diario de la plataforma.

---

## 🔑 1. Acceso al Sistema

### Iniciar Sesión
1.  Ingresa a la dirección web proporcionada por tu administrador (ej: `http://localhost:3001` para Producción).
2.  Introduce tu correo electrónico y contraseña.
    *   *Solicita tus credenciales al administrador del sistema.*
3.  Haz clic en **"Ingresar"**.

---

## 📂 2. Gestión de Catálogos
Para que el sistema funcione correctamente, es vital tener la información base completa y sin errores.

### Clientes
Antes de vender, registra a quién le venderás.
1.  Ve al menú **Clientes** y haz clic en **"+ Nuevo Cliente"**.
2.  **Datos Fiscales (Obligatorios para Factura 4.0):**
    *   **Razón Social**: Debe coincidir *exactamente* con la Constancia de Situación Fiscal (sin régimen capital como "SA de CV").
    *   **RFC**: Verifica homoclave.
    *   **Código Postal**: El registrado ante el SAT.
    *   **Régimen Fiscal**: Pregunta al cliente su régimen (ej: 601 General de Ley).
3.  **Correo Electrónico**: Aquí llegarán los PDF y XML de las facturas automáticamente.
4.  Clic en **Guardar**.

### Productos y Servicios
Define qué vendes para agilizar tus facturas.
1.  Ve al menú **Catálogos > Productos** > **"+ Nuevo"**.
2.  **Descripción**: Nombre detallado que aparecerá en el PDF.
3.  **Clave Producto SAT**: Usa el buscador del SAT (ej: `80141605` para Servicios de marketing). *Si te equivocas aquí, la factura podría no ser deducible para tu cliente.*
4.  **Clave Unidad**: Generalmente `E48` (Unidad de servicio) o `H87` (Pieza).
5.  **Precio Unitario**: Precio base antes de impuestos.

---

## 💰 3. Ciclo de Ventas (Flujo Detallado)
El flujo más común y seguro para tu administración es: **Facturar la venta → Registrar el cobro cuando ocurra**.

### Paso 1: Emitir la Factura (CFDI de Ingreso)
1.  Ve al menú **Facturas** y presiona **"+ Nueva"**.
2.  **Encabezado**:
    *   Selecciona al **Cliente**.
    *   **Uso de CFDI**: Usualmente "G03 - Gastos en general".
    *   **Método de Pago**:
        *   Elige **PUE (Pago en una sola exhibición)** si ya te pagaron o te pagan hoy.
        *   Elige **PPD (Pago en parcialidades)** si es a crédito (te pagarán días después).
3.  **Agregar Conceptos**:
    *   Busca el producto/servicio que creaste previamente.
    *   Ajusta la cantidad o precio si es necesario.
4.  **Revisión y Timbrado**:
    *   Verifica Subtotal e IVA.
    *   Haz clic en **"Timbrar ante el SAT"**.
    *   *El sistema enviará el correo al cliente y descargará el PDF automáticamente.*

### Paso 2: Registrar la Cobranza (Complemento de Pago)
**Solo necesario si la factura fue PPD (Crédito).** Si fue PUE, el sistema asume que ya está pagada.

1.  Cuando recibas el dinero en tu banco, ve a **Pagos (Cobranza)** > **"+ Nuevo Pago"**.
2.  **Datos del Depósito**:
    *   **Cliente**: Selecciónalo para ver sus deudas.
    *   **Fecha de Pago**: La fecha real del depósito bancario.
    *   **Forma de Pago**: Transferencia (03), Cheque (02), etc.
    *   **Monto**: Cantidad total recibida.
3.  **Asociar Facturas**:
    *   En la tabla inferior busca las facturas pendientes.
    *   Haz clic en **"Agregar"** o escribe cuánto abona a cada una en la columna "Monto a Pagar".
4.  **Finalizar**:
    *   Clic en **"Timbrar Pago"**. Esto genera el recibo electrónico de pago (REP) que también es obligatorio por el SAT.

---

## 💸 4. Gestión de Gastos (Egresos)
Registra tus compras y gastos operativos para tener control del flujo de efectivo.

1.  Ve al menú **Egresos** > **"+ Nuevo Egreso"**.
2.  **Llenado de Datos**:
    *   **Proveedor**: Selecciónalo (o créalo si no existe).
    *   **Fecha**: Cuándo hiciste el gasto.
    *   **Monto**: Total pagado.
    *   **Categoría**: Clasifícalo (ej: Nómina, Servicios, Renta) para tus reportes.
3.  **Adjuntar Evidencia**:
    *   Puedes subir el PDF o XML de la factura que recibiste usando el botón del clip.
4.  **Guardar**.

---

## 📊 5. Reportes y Consultas

### Filtrado de Facturas
En el módulo de **Facturas**, puedes buscar rápidamente usando la barra de filtros superior:
*   **Buscador General**: Busca por nombre de cliente.
*   **Filtro por Folio**: Escribe el número exacto del folio interno y presiona `Enter` para encontrar una factura específica.
*   **Rango de Fechas**: Filtra por fecha de emisión.

### Columnas de Fechas
En el listado de facturas visualizarás claramente:
*   **Fecha**: Emisión de la factura.
*   **Fecha Pago (Prog.)**: Cuándo se *debería* pagar según los días de crédito.
*   **Fecha Pago (Real)**: Cuándo se registró el pago efectivamente.

### Exportación
Usa el botón **"Exportar Excel"** en la parte superior derecha de cualquier listado para descargar la información visible y trabajarla externamente.

---

## ⚙️ 6. Administración

### Usuarios
*(Solo Administradores)*
1.  Ve a **Configuración > Usuarios**.
2.  Aquí puedes invitar a nuevos colaboradores (Vendedores, Contadores) y asignarles roles y contraseñas.
