# Manual Operativo Detallado: Sistema CRM/ERP

Este documento es una guía paso a paso diseñada para ayudarte a realizar tus tareas diarias de forma rápida y sencilla.

---

## 🎨 1. Personaliza tu Espacio de Trabajo
Antes de empezar, ajusta el sistema para que te sientas cómodo. Estas opciones están en la parte inferior del **menú lateral izquierdo**.

### 🌙 Modo Oscuro (Descanso Visual)
Si trabajas de noche o te molesta el brillo de la pantalla:
1.  Busca el interruptor con el icono de un **foco** (💡) o una **luna** (🌙) al final del menú.
2.  Haz clic para cambiar entre fondo blanco (Modo Claro) y fondo negro (Modo Oscuro).

### 🔎 Tamaño de Letra (AA)
Si sientes que las letras son muy pequeñas:
1.  Busca el icono de "AA" o unas letras pequeñas/grandes.
2.  Selecciona el tamaño que prefieras:
    *   **A-**: Letra pequeña (cabe más información).
    *   **A**: Tamaño normal.
    *   **A+**: Letra grande.
    *   **A++**: Letra extra grande (máxima legibilidad).

### 📄 Navegación en Listas (Paginación)
Cuando entres a secciones como "Facturas" o "Clientes", verás tablas con información. Si hay muchos registros:
*   Usa los botones **"<" (Anterior)** y **">" (Siguiente)** en la esquina inferior derecha de la tabla para ver más páginas.
*   Puedes cambiar cuántas filas ver por página (10, 20 o 50) usando el selector junto a los números de página.

### 🧠 1.1 Navegación Inteligente (Memoria de Filtros)
Una de las funciones más poderosas del sistema es su "memoria".
*   **¿Cómo funciona?**: Si estás buscando, por ejemplo, facturas del cliente "Juan Pérez" y entras a ver el detalle de una, **al regresar al listado el filtro seguirá ahí**. No tienes que volver a buscarlo.
*   **¿Dónde aplica?**: Clientes, Productos, Facturas, Pagos y Egresos.
*   **¿Cómo limpiar?**: Para borrar todo y empezar de cero, simplemente da clic en **"Cerrar Sesión"** o limpia los filtros manualmente con el botón "Limpiar" (cruz pequeña en los campos de búsqueda).

---

## 👥 2. Clientes: Cómo registrarlos sin errores

### Opción A: La forma más rápida (Recomendada) ⭐
*Usa esta opción si el cliente te envió su Constancia de Situación Fiscal (PDF).*

1.  Ve al menú **Clientes** y presiona el botón **"+ Nuevo Cliente"**.
2.  Busca el botón rojo/gris que dice **"Subir PDF Constancia"** o **Importar CSF**.
3.  Selecciona el archivo PDF de tu computadora.
4.  **¡Listo!** El sistema llenará automáticamente:
    *   Nombre (Razón Social).
    *   RFC.
    *   Código Postal.
    *   Régimen Fiscal.
5.  Solo verifica que el correo electrónico esté correcto para que le lleguen sus facturas y da clic en **Guardar**.

### Opción B: Registro Manual
1.  Ve a **Clientes > "+ Nuevo Cliente"**.
2.  Llena los campos con cuidado. **OJO**:
    *   **Razón Social**: Escríbela *exactamente* como aparece en su constancia, sin incluir "SA de CV" (a menos que su constancia lo diga explícitamente, pero el SAT ya no suele pedir el régimen societario).
    *   **Código Postal**: Debe coincidir con el de su domicilio fiscal. Si está mal, la factura no pasará.
    *   **Régimen Fiscal**: Pregúntale cuál es (ej. "Gastos en general" no es un régimen, es un uso; el régimen es algo como "601 - Personas Morales").
3.  Haz clic en **Guardar**.

---

## 📦 3. Productos y Servicios
Define qué vendes para no tener que escribirlo cada vez.

1.  Ve al menú **Catálogos > Productos** (o Productos/Servicios) y da clic en **"+ Nuevo"**.
2.  **Llenado de Datos**:
    *   **Descripción**: El nombre detallado de tu producto (ej. "Mantenimiento de Aire Acondicionado").
    *   **Clave Producto SAT**: Escribe una palabra clave (ej. "limpieza") y el sistema te sugerirá claves. *Es obligatorio por el SAT*.
    *   **Clave Unidad**: Generalmente se usa:
        *   `E48` - Unidad de servicio (para servicios).
        *   `H87` - Pieza (para productos físicos).
    *   **Precio Unitario**: El precio antes de IVA.
3.  Haz clic en **Guardar**.

---

## 🧾 4. Facturación: Ciclo de Venta

### Paso 1: Crear la Factura
1.  Ve al menú **Facturas** y presiona **"+ Nueva"**.
2.  **Encabezado**:
    *   Elige al **Cliente**.
    *   **Método de Pago**:
        *   Elige **PUE (Pago en una sola exhibición)** si ya te pagaron.
        *   Elige **PPD (Pago en parcialidades)** si te pagarán después (crédito).
3.  **Conceptos (Lo que vendes)**:
    *   Haz clic en **"Agregar concepto"**.
    *   Busca tu producto en la lista. Si no existe, puedes crearlo ahí mismo o usar "Nuevo producto/servicio".
    *   Verifica la cantidad y el precio.
4.  **Guardar Borrador**:
    *   Si das clic en "Guardar", la factura se guarda pero **NO** se envía al SAT. Puedes editarla después.

### Paso 2: Revisar antes de enviar (Evita cancelaciones)
Antes de timbrar (hacerla oficial), envíale un borrador a tu cliente:
1.  Con la factura en estado "BORRADOR", busca el botón **"Enviar Vista Previa"** (icono de sobre ✉️).
2.  Esto le manda un correo a tu cliente con la factura "sin validez oficial" para que revise sus datos.

### Paso 3: Timbrar (Hacerla oficial)
1.  Cuando estés seguro, presiona el botón **"Timbrar"** (icono de rayo ⚡).
2.  El sistema la enviará al SAT y generará el PDF y XML oficiales.
3.  Automáticamente se envía por correo al cliente.

### Truco Pro: Duplicar Facturas 🚀
Si vas a hacer una factura igual a la del mes pasado:
1.  Busca la factura vieja en el listado.
2.  Abre la factura.
3.  Busca el botón **"Duplicar"** (icono de dos hojas 📄📄).
4.  Se creará una **nueva factura en borrador** con los mismos datos. Solo cambia la fecha y timbra. ¡Ahorraste 5 minutos!

---

## ❌ 4.1 Cancelación y Refacturación (Corrección de Errores)

Si timbraste una factura (Factura A) y te diste cuenta de que tiene un error (ej. precio mal, RFC mal, etc.), sigue estos pasos para corregirlo cumpliendo con el SAT.

### Paso 1: Cancelar la factura errónea (Factura A)
1.  Abre la factura que tiene el error.
2.  Presiona el botón **"Cancelar"**.
3.  El sistema te pedirá el motivo. Selecciona:
    *   **"02 - Comprobante emitido con errores sin relación"**.
    *   *(Este es el método más directo y evita complicaciones).*
4.  Confirma la cancelación. El estatus cambiará a "CANCELADA" (o "EN PROCESO..." si requiere aprobación, en cuyo caso espera a que el estatus final sea CANCELADA).

### Paso 2: Crear la nueva factura (Factura B)
1.  Puedes usar el botón **"Duplicar"** en la factura cancelada para no volver a escribir todo.
2.  **Corrige el error** que tenía la anterior (ej. cambia el precio, corrige el RFC, etc.).

### Paso 3: Relacionar (¡Muy Importante!)
Para que el SAT sepa que esta nueva factura reemplaza a la anterior:
1.  En la parte inferior del formulario de la nueva factura, activa la casilla **"¿Tiene relación CFDI?"**.
2.  **Tipo relación**: Selecciona **"04 - Sustitución de los CFDI previos"**.
3.  **CFDIs relacionados**: Escribe o pega el **UUID (Folio Fiscal)** de la factura que acabas de cancelar.

### Paso 4: Timbrar
1.  Presiona **"Timbrar"**.
2.  ¡Listo! Has sustituido la factura correctamente.

---

## 💰 5. Complemento de Pagos

*Solo necesitas hacer esto si hiciste una factura PPD (Pago en Parcialidades o Diferido) y ya recibiste el dinero.*

### Paso 1: Crear el Registro del Pago
1.  Ve al menú **Pagos** y presiona el botón **"+ Nuevo Pago"**.
2.  **Datos del Emisor y Receptor**:
    *   Selecciona la **Empresa** (tu razón social).
    *   Busca y selecciona al **Cliente** (puedes buscar por Nombre Comercial o Razón Social).
3.  **Datos del Pago**:
    *   **Fecha de Pago (Real)**: El día y hora exacta que cayó el dinero.
    *   **Forma de Pago**: ¿Cómo te pagaron? (03-Transferencia, 02-Cheque, 01-Efectivo, etc.).
    *   **Moneda**: MXN o USD.
    *   *(Nota: El campo "Monto" está bloqueado. Se calculará automáticamente en el siguiente paso).*

### Paso 2: Asignar el Pago a las Facturas (Saldar Deuda)
Una vez seleccionado el cliente, aparecerá abajo la tabla **"Facturas a Pagar"** con todas sus facturas pendientes.
1.  Busca la factura que te están pagando.
2.  En la columna **"Monto a Pagar"** (casilla blanca), escribe cuánto dinero estás aplicando a esa factura.
    *   *Ejemplo: Si la factura es de $10,000 y te pagaron todo, escribe 10000.*
    *   *Ejemplo: Si solo es un abono parcial, escribe la cantidad abonada.*
3.  Verás que el campo **"Monto"** (total general arriba) se actualiza solo con la suma de todo lo que escribiste.

### Paso 3: Guardar y Timbrar
1.  Haz clic en **"Guardar Borrador"** (icono de disquete 💾). Esto guarda el registro en tu sistema interna pero aún no avisa al SAT.
2.  Revisa que los datos sean correctos.
3.  Presiona el botón **"Timbrar"** (icono de rayo ⚡).
4.  El sistema generará el **REP (Recibo Electrónico de Pago)** oficial, obteniendo su Folio Fiscal (UUID).

### Paso 4: Enviar al Cliente
Una vez timbrado, se habilitarán los botones de acción:
*   **Enviar por Correo**: Da clic en el botón con el icono de sobre (✉️). Se pre-llenará el correo del cliente y se adjuntarán el PDF y XML.
*   **Ver PDF**: Para descargarlo tú mismo.

### ❌ Cancelación de Pagos
Si te equivocaste al hacer el recibo de pago (ej. fecha incorrecta o asignaste mal el dinero):
1.  Abre el pago timbrado.
2.  Presiona el botón de **"Papelera" (Borrar/Cancelar)** 🗑️.
3.  Selecciona el motivo:
    *   **"01 - Comprobante emitido con errores CON relación"**: Si vas a hacer uno nuevo para sustituirlo. (Te pedirá el UUID del nuevo, así que primero haz el nuevo y luego cancela este, o usa la opción 02 si se te complica).
    *   **"02 - Comprobante emitido con errores SIN relación"**: La opción más sencilla para anularlo y volver a empezar.
4.  Confirma la cancelación.

--- 

## 💰 6. Cobranza: Recupera tu Dinero

Gestiona de forma proactiva a los clientes que te deben dinero para mejorar tu flujo de efectivo.

### 6.1 Dashboard (Tu Tablero de Control)
Al entrar a "Cobranza", verás indicadores clave:
*   **KPIs**: Cuánto te deben en total, cuánto está vencido (urgente) y cuánto está vigente.
*   **Gráfico de Antigüedad**: Te muestra visualmente qué tan vieja es la cartera.
*   **Top Deudores**: Lista rápida de quiénes te deben más dinereo.

### 6.2 Reporte de Antigüedad (Antigüedad de Saldos)
Es la tabla principal donde ves cliente por cliente.
*   **Colores de Alerta**:
    *   **Verde**: Saldo Vigente (aún no vence).
    *   **Amarillo**: Vencido de 1-30 días (primer aviso).
    *   **Naranja**: Vencido de 31-60 días y 61-90 días (atención media).
    *   **Rojo**: Vencido más de 90 días (crítico).
*   **Acciones Rápidas**:
    1.  **Estado de Cuenta (PDF)**: Da clic en el icono de **PDF** el cual te mostrará la vista previa del documento para descargarlo.
    2.  **Enviar por Correo**: Da clic en el icono de **Sobre (✉️)**.
        *   Se abrirá una ventana para confirmar los destinatarios.
        *   Se adjunta el PDF automáticamente.
        *   Se envía un mensaje cordial invitando al pago.
    3.  **Bitácora (Notas)**: Da clic en el icono de **Libreta**.
        *   Aquí puedes anotar: "Hablé con contabilidad, prometen pago el viernes".
        *   También verás el **historial automático** de cuándo les enviaste el estado de cuenta por correo.

---

## 💸 7. Control de Gastos (Egresos)

Registra tus compras para saber en qué se va el dinero. El sistema tiene una función inteligente para ahorrarte tiempo.

### Opción A: Carga Inteligente (XML) - ¡La más rápida! ⚡
Usa esta opción si tu proveedor te dio factura (XML).

1.  Ve al menú **Egresos** y presiona **"+ Nuevo Egreso"**.
2.  Selecciona la **Empresa** (quien pagó).
3.  Busca el botón **"Subir XML"** y selecciona el archivo `.xml` de tu factura.
4.  **¡Magia!** ✨ El sistema leerá el archivo y llenará automáticamente:
    *   Fecha.
    *   Monto y Moneda.
    *   Proveedor.
    *   Método de Pago.
5.  Solo te falta completar:
    *   **Categoría**: ¿En qué concepto entra este gasto? (Nómina, Renta, Viáticos, etc.).
    *   **Descripción**: Una nota breve para ti.
6.  (Opcional) Sube el **PDF** para tener el expediente completo.
7.  Haz clic en **Guardar**.

### Opción B: Registro Manual
Si no hay factura (ej. recibo simple, taxi, propina):

1.  Ve a **Egresos > + Nuevo Egreso**.
2.  Llena todos los campos manualmente:
    *   **Proveedor**: A quién le pagaste.
    *   **Fecha**: Cuándo salió el dinero.
    *   **Monto**: Total pagado.
    *   **Categoría** y **Descripción**.
3.  Sube cualquier comprobante (foto o PDF) en "Subir Otro" o "Subir PDF".
4.  Haz clic en **Guardar**.

El archivo adjunto puede servir para subir una foto de evidencia del egreso o el comprobante de pago.

---

## ⚙️ 8. Administración de Empresas (Solo Gerentes)

### Agregar Nueva Empresa
Si tienes varias razones sociales, regístralas aquí para mantenerlas separadas.

1.  Ve a **Empresas** > **"+ Nueva Empresa"**.
2.  **Llenado de Datos**:
    *   Puedes usar el botón **"Subir PDF Constancia"** para ahorrar tiempo (igual que en Clientes).
    *   **Certificados Digitales (CSD)**: En la parte inferior, sube los archivos `.cer` y `.key` que te dio el SAT, y escribe la **Contraseña** de la llave privada. Sin esto, no podrás timbrar.
    *   **Logo**: Sube tu logo para que salga en los PDFs.
3.  **Correo Electrónico**:
    *   Una vez guardada la empresa, busca el botón **"Configurar Correo Electrónico"**.
    *   Aquí pones los datos de tu servidor SMTP (ej. Gmail, Outlook) para que las facturas se envíen automáticamente desde tu cuenta.

---

## 👥 9. Gestión de Usuarios
Dales acceso a tus empleados sin compartir tu contraseña.

1.  Ve al menú **Usuarios** (es posible que solo lo vean los Administradores).
2.  Presiona **"+ Nuevo Usuario"**.
3.  **Roles**:
    *   **Administrador**: Tiene acceso a TODO.
    *   **Supervisor**: Puede ver y crear facturas, pero solo de la empresa que le asignes.
4.  Si eliges "Supervisor", selecciona la **Empresa Asignada**.
5.  Crea su contraseña inicial (ellos no la verán, tú se las entregas).



---



## ⚠️ Glosario Rápido
*   **Timbrar**: Avisarle al SAT que hiciste una factura. Es irreversible (tienes que cancelar si te equivocas).
*   **UUID**: Es el "Folio Fiscal". Un código largo extraño que es la verdadera identificación de la factura.
*   **PUE**: "Pago en Una sola Exhibición". Úsalo para ventas de contado.
*   **PPD**: "Pago en Parcialidades o Diferido". Úsalo para crédito.
*   **CSF**: Constancia de Situación Fiscal. El documento "acta de nacimiento" fiscal de tu cliente.

---

