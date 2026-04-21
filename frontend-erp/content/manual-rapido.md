# Guía Rápida de Referencia — Sistema CRM/ERP

---

## 🔑 Acceso al Sistema

1.  Ingresa a la dirección web del sistema.
2.  Escribe tu correo y contraseña → **"Ingresar"**.
3.  Tu sesión se renueva automáticamente mientras trabajas (30 min de inactividad la cierra).
4.  Si pierdes conexión a internet, aparecerá una **barra amarilla** en la parte superior. Los cambios no se guardan hasta que se restablezca.

---

## 📊 Dashboard

Al iniciar sesión verás el tablero con:
*   **KPIs**: Ingresos, egresos, por cobrar y vencido del mes.
*   **Gráfica de barras**: Ingresos vs Egresos de los últimos 12 meses.
*   **Gráfica de pastel**: Egresos desglosados por categoría.
*   Usa los filtros de **mes/año** y **empresa** para ajustar la vista.

---

## 📂 Catálogos Base

### Clientes
1.  **Clientes > "+ Nuevo Cliente"**.
2.  **(Recomendado)** Sube el PDF de la Constancia de Situación Fiscal → se llenan RFC, Razón Social, CP y Régimen automáticamente.
3.  Verifica el correo electrónico → ahí llegarán las facturas.
4.  **Guardar**.

### Productos y Servicios
1.  **Productos > "+ Nuevo"**.
2.  Llena: Descripción, Clave SAT, Clave Unidad (`E48` = servicio, `H87` = pieza), Precio.
3.  **Guardar**.

---

## 💰 Ciclo de Ventas

### Emitir Factura
1.  **Facturas > "+ Nueva"** (o **Duplicar** una anterior para ahorrar tiempo).
2.  Cliente → Método de Pago (**PUE** = contado, **PPD** = crédito).
3.  Agregar conceptos.
4.  **Guardar Borrador** (sin enviar al SAT) o directamente **Timbrar**.
5.  Al timbrar, el sistema pide **confirmación** — es irreversible.

### Enviar Vista Previa antes de Timbrar
*   Botón **"Enviar Vista Previa"** (✉️) → manda PDF sin validez oficial al cliente para que revise.
*   También disponible directamente desde el **listado de facturas**.

### Complemento de Pago (solo facturas PPD)
1.  **Pagos > "+ Nuevo Pago"**.
2.  Selecciona cliente → aparecen sus facturas pendientes.
3.  Escribe el monto en la columna "Monto a Pagar" de cada factura.
4.  **Guardar Borrador** → **Timbrar** (pide confirmación).

---

## ❌ Cancelaciones

### Cancelar Factura
1.  Abrir factura timbrada → botón **"Cancelar"**.
2.  Motivo recomendado: **"02 - Comprobante emitido con errores sin relación"** (se cancela al instante).
3.  Para sustituirla: **Duplicar** la cancelada, corregir el error, relacionarla con tipo **"04"** y el UUID de la cancelada, luego **Timbrar**.

### ⏳ Factura "EN CANCELACIÓN" (Motivo 01 — requiere aceptación del receptor)
Cuando usas el Motivo 01, la factura queda en espera hasta **72 horas hábiles**.

| Situación | Qué hacer |
|---|---|
| Quieres saber si ya fue aceptada | Botón **"Verificar con SAT"** (el sistema también lo hace automáticamente al abrir la factura y cada noche a las 3 AM) |
| El receptor te avisó que rechazó | Botón **"Receptor rechazó cancelación"** → confirmar → vuelve a **TIMBRADA** |
| No pasa nada después de 72 horas hábiles | El SAT la cancela automáticamente; usa "Verificar con SAT" para actualizar |

> ⚠️ Mientras está **EN CANCELACIÓN** la factura no se puede editar. Sigue siendo fiscalmente válida.

### Cancelar Pago
1.  Abrir pago timbrado → botón **"Cancelar"** → seleccionar motivo → confirmar.

---

## 📋 Presupuestos (Cotizaciones)

1.  **Presupuestos > "+ Nuevo Presupuesto"** → selecciona cliente y agrega conceptos.
2.  **Guardar** (queda en estado *Borrador*).
3.  Botón **"Enviar"** → manda PDF al cliente por correo y cambia estado a *Enviado*.
4.  Cambia el estado según la respuesta: *Aceptado*, *Rechazado* o *Facturado*.
5.  Solo se pueden **eliminar** presupuestos en estado *Borrador*.

---

## 💰 Cobranza

1.  Ve al menú **Cobranza**.
2.  El dashboard muestra KPIs, gráfico de antigüedad y top deudores.
3.  Colores de alerta: 🟢 Vigente · 🟡 1-30 días · 🟠 31-90 días · 🔴 +90 días.
4.  Por cada cliente puedes:
    *   📄 Descargar su **Estado de Cuenta en PDF**.
    *   ✉️ **Enviar por correo** el estado de cuenta.
    *   📓 Agregar **notas** en la bitácora de seguimiento.

---

## 💸 Egresos (Gastos)

*   **Con XML del proveedor**: Subir el XML → se llenan automáticamente fecha, monto y proveedor → agregar categoría → **Guardar**.
*   **Sin XML**: Llenar manualmente proveedor, fecha, monto, categoría → opcionalmente subir foto o PDF de comprobante → **Guardar**.

---

## ⚙️ Empresas *(Solo Administradores)*

*   **Empresas > "+ Nueva"** → llenar datos o importar desde PDF Constancia.
*   Subir certificados **.cer** y **.key** (CSD) + contraseña para poder timbrar.
*   Logo: solo formato **PNG**, máximo **2 MB**.
*   Configurar correo SMTP para envíos automáticos — cuando está activo aparece ✅ en el listado.

---

## 👥 Usuarios *(Solo Administradores)*

*   **Usuarios > "+ Nuevo"** → correo, contraseña, rol.
*   **Administrador**: acceso total a todas las empresas.
*   **Supervisor**: acceso solo a la empresa asignada.

---

## 🔍 Auditoría *(Solo Gerentes)*

*   Ve al menú **Auditoría** (solo visible para usuarios autorizados).
*   Filtra por: Empresa, Email de usuario, Tipo de acción, Rango de fechas.
*   Muestra: fecha/hora, quién lo hizo, qué hizo, sobre qué registro y detalles adicionales.
*   Útil para revisar exportaciones de Excel, envíos de correo y operaciones críticas.

---

## 🔔 Notificaciones

*   El **ícono de campana** (🔔) en el menú lateral muestra avisos del sistema.
*   El número en rojo = notificaciones sin leer.
*   Haz clic para ver el detalle y marcarlas como leídas.

---

## 📤 Exportar a Excel

*   Disponible en: Facturas, Pagos, Egresos, Clientes.
*   Botón **"Exportar"** (verde) en la parte superior de cada listado.
*   Exporta los registros del período/filtros activos en ese momento.

---

## ⚠️ Glosario

| Término | Significado |
|---|---|
| **Timbrar** | Enviar al SAT — irreversible |
| **UUID** | Folio Fiscal — identificador único de cada CFDI |
| **PUE** | Pago en Una sola Exhibición (contado) |
| **PPD** | Pago en Parcialidades o Diferido (crédito) |
| **REP** | Recibo Electrónico de Pago |
| **CSD** | Certificado de Sello Digital (.cer + .key) |
| **CSF** | Constancia de Situación Fiscal |
| **CFDI** | Factura electrónica oficial |
| **EN CANCELACIÓN** | Estado intermedio: solicitud enviada, receptor aún no ha respondido (máx. 72 h hábiles) |
| **Motivo 01** | Cancelación con sustitución — requiere aprobación del receptor (activa el período de 72 h) |
| **Motivos 02/03/04** | Cancelación directa — no requiere aprobación, se procesa al instante |
