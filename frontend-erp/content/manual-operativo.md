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

### 🔔 1.2 Notificaciones
En la parte inferior del menú lateral verás un **ícono de campana** (🔔).
*   El número en rojo indica cuántas notificaciones tienes sin leer.
*   Haz clic en la campana para ver el listado de avisos (facturas timbradas, pagos registrados, errores, etc.).
*   Puedes marcar cada notificación como leída individualmente o todas a la vez.
*   El sistema revisa si hay nuevas notificaciones automáticamente cada 30 segundos.

### ⏱️ 1.3 Sesión Automática
Tu sesión tiene una duración activa de **30 minutos**. Si sigues trabajando, el sistema la renueva automáticamente sin que tengas que volver a iniciar sesión. Solo se cierra si no haces ninguna acción durante un período prolongado o si haces clic en **"Cerrar Sesión"**.

### 🌐 1.4 Indicador de Conexión
Si tu computadora pierde el acceso a internet, verás una **barra amarilla en la parte superior** de la pantalla con el mensaje *"Sin conexión"*. Mientras esté visible, los cambios **no se guardarán**. La barra desaparece automáticamente cuando la conexión se restablece.

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
    *   **Razón Social**: Escríbela *exactamente* como aparece en su constancia, sin incluir "SA de CV" (a menos que su constancia lo diga explícitamente).
    *   **Código Postal**: Debe coincidir con el de su domicilio fiscal. Si está mal, la factura no pasará.
    *   **Régimen Fiscal**: Pregúntale cuál es (ej. "601 - Personas Morales con Fines no Lucrativos").
3.  Haz clic en **Guardar**.

---

## 📦 3. Productos y Servicios
Define qué vendes para no tener que escribirlo cada vez.

1.  Ve al menú **Productos** y da clic en **"+ Nuevo"**.
2.  **Llenado de Datos**:
    *   **Descripción**: El nombre detallado de tu producto (ej. "Mantenimiento de Aire Acondicionado").
    *   **Clave Producto SAT**: Escribe una palabra clave (ej. "limpieza") y el sistema te sugerirá claves. *Es obligatorio por el SAT*.
    *   **Clave Unidad**: Generalmente se usa:
        *   `E48` - Unidad de servicio (para servicios).
        *   `H87` - Pieza (para productos físicos).
    *   **Precio Unitario**: El precio antes de IVA.
3.  Haz clic en **Guardar**.

---

## 📊 4. Dashboard (Tablero Principal)

Al iniciar sesión, el **Dashboard** te muestra un resumen financiero de tu empresa en tiempo real.

### 4.1 Indicadores Principales (KPIs)
En la parte superior verás tarjetas con:
*   **Ingresos del mes**: Total facturado en el mes actual.
*   **Egresos del mes**: Total de gastos registrados.
*   **Por cobrar**: Facturas PPD pendientes de pago.
*   **Vencido**: Facturas que superaron su fecha de vencimiento.

### 4.2 Gráficas
*   **Ingresos vs Egresos**: Gráfica de barras comparando los últimos 12 meses.
*   **Egresos por Categoría**: Gráfica de pastel mostrando en qué se va el dinero (Nómina, Renta, Servicios, etc.).

### 4.3 Filtros del Dashboard
*   Selecciona el **mes y año** que quieres analizar usando los controles en la parte superior derecha de cada sección.
*   Si eres Administrador, también puedes filtrar por **Empresa** para ver los datos de cada razón social por separado.

---

## 🧾 5. Facturación: Ciclo de Venta

### Paso 1: Crear la Factura
1.  Ve al menú **Facturas** y presiona **"+ Nueva"**.
2.  **Encabezado**:
    *   Elige al **Cliente**.
    *   **Método de Pago**:
        *   Elige **PUE (Pago en una sola exhibición)** si ya te pagaron.
        *   Elige **PPD (Pago en parcialidades)** si te pagarán después (crédito).
3.  **Conceptos (Lo que vendes)**:
    *   Haz clic en **"Agregar concepto"**.
    *   Busca tu producto en la lista. Si no existe, puedes crearlo ahí mismo.
    *   Verifica la cantidad y el precio.
4.  **Guardar Borrador**:
    *   Si das clic en "Guardar", la factura se guarda pero **NO** se envía al SAT. Puedes editarla después.

### Paso 2: Revisar antes de enviar (Evita cancelaciones)
Antes de timbrar (hacerla oficial), envíale un borrador a tu cliente:
1.  Con la factura en estado "BORRADOR", busca el botón **"Enviar Vista Previa"** (icono de sobre ✉️).
2.  Esto le manda un correo a tu cliente con la factura "sin validez oficial" para que revise sus datos.
3.  También puedes enviar la vista previa directamente desde el **listado de facturas** usando el botón de sobre que aparece en la columna de acciones de cada fila.

### Paso 3: Timbrar (Hacerla oficial)
1.  Cuando estés seguro, presiona el botón **"Timbrar"** (icono de rayo ⚡).
2.  El sistema te pedirá una **confirmación** antes de proceder — este paso es **irreversible**.
3.  El sistema la enviará al SAT y generará el PDF y XML oficiales.
4.  Automáticamente se envía por correo al cliente.

### Truco Pro: Duplicar Facturas 🚀
Si vas a hacer una factura igual a la del mes pasado:
1.  Busca la factura vieja en el listado.
2.  Abre la factura.
3.  Busca el botón **"Duplicar"** (icono de dos hojas 📄📄).
4.  Se creará una **nueva factura en borrador** con los mismos datos. Solo cambia la fecha y timbra. ¡Ahorraste 5 minutos!

---

## ❌ 5.1 Cancelación y Refacturación (Corrección de Errores)

Si timbraste una factura (Factura A) y te diste cuenta de que tiene un error (ej. precio mal, RFC mal, etc.), sigue estos pasos para corregirlo cumpliendo con el SAT.

### Paso 1: Cancelar la factura errónea (Factura A)
1.  Abre la factura que tiene el error.
2.  Presiona el botón **"Cancelar"**.
3.  El sistema te pedirá el motivo. Selecciona:
    *   **"02 - Comprobante emitido con errores sin relación"**.
    *   *(Este es el método más directo y evita complicaciones).*
4.  Confirma la cancelación.

> ⏳ **¿Qué pasa después de cancelar?** Depende del motivo:
> - **Motivos 02, 03, 04**: La cancelación se procesa de inmediato. El estatus cambia a **CANCELADA** al instante.
> - **Motivo 01** (sustitución): El receptor del CFDI tiene **72 horas hábiles** para aceptar o rechazar la cancelación. El estatus cambiará a **EN CANCELACIÓN** mientras esperas su respuesta.

### Paso 2: Crear la nueva factura (Factura B)
1.  Puedes usar el botón **"Duplicar"** en la factura cancelada para no volver a escribir todo.
2.  **Corrige el error** que tenía la anterior (ej. cambia el precio, corrige el RFC, etc.).

### Paso 3: Relacionar (¡Muy Importante!)
Para que el SAT sepa que esta nueva factura reemplaza a la anterior:
1.  En la parte inferior del formulario de la nueva factura, activa la casilla **"¿Tiene relación CFDI?"**.
2.  **Tipo relación**: Selecciona **"04 - Sustitución de los CFDI previos"**.
3.  **CFDIs relacionados**: Escribe o pega el **UUID (Folio Fiscal)** de la factura que acabas de cancelar.

### Paso 4: Timbrar
1.  Presiona **"Timbrar"** y confirma.
2.  ¡Listo! Has sustituido la factura correctamente.

---

## ⏳ 5.2 Facturas "EN CANCELACIÓN" — Qué hacer mientras esperas

Cuando solicitas cancelar una factura con **Motivo 01** (sustitución de CFDI), el SAT requiere que el receptor la acepte o rechace. Durante ese período la factura aparece en estado **EN CANCELACIÓN** y el sistema te muestra un aviso amarillo con la fecha y hora en que se envió la solicitud.

### ¿Qué significa este estado?
*   La factura **no está cancelada aún** — sigue siendo fiscalmente válida.
*   El receptor tiene **72 horas hábiles** para responder.
*   Si no responde en ese plazo, el SAT la cancela automáticamente.
*   La factura queda **bloqueada**: no se puede editar ni volver a cancelar.

### Verificar el resultado con el SAT
El sistema revisa automáticamente el estado al abrir la factura. También puedes hacerlo manualmente:

1.  Abre la factura que está **EN CANCELACIÓN**.
2.  Presiona el botón **"Verificar con SAT"**.
3.  El sistema consultará directamente las bases de datos del SAT en tiempo real.
4.  Si la cancelación fue aceptada o el plazo venció, el estatus cambiará automáticamente a **CANCELADA**.
5.  Si el receptor la rechazó (y el SAT lo reporta como "Vigente"), el estatus regresará a **TIMBRADA**.

> 💡 Adicionalmente, el sistema realiza una verificación automática de todas las facturas EN CANCELACIÓN cada noche a las 3:00 AM, por lo que al día siguiente siempre verás el estado actualizado sin tener que hacer nada.

### Si el receptor te avisó que rechazó la cancelación
Si tu cliente te comunica directamente que rechazó la cancelación:
1.  Abre la factura en estado **EN CANCELACIÓN**.
2.  Presiona el botón **"Receptor rechazó cancelación"**.
3.  Confirma la acción en la ventana emergente.
4.  La factura regresará al estado **TIMBRADA** y quedará vigente nuevamente.

> ⚠️ **Usa este botón solo si el cliente te confirmó explícitamente que rechazó la cancelación.** Si tienes dudas, usa primero "Verificar con SAT" para confirmar.

---

## 💰 6. Complemento de Pagos

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
    *   *(Nota: El campo "Monto" se calculará automáticamente en el siguiente paso).*

### Paso 2: Asignar el Pago a las Facturas (Saldar Deuda)
Una vez seleccionado el cliente, aparecerá abajo la tabla **"Facturas a Pagar"** con todas sus facturas pendientes.
1.  Busca la factura que te están pagando.
2.  En la columna **"Monto a Pagar"** (casilla blanca), escribe cuánto dinero estás aplicando a esa factura.
    *   *Ejemplo: Si la factura es de $10,000 y te pagaron todo, escribe 10000.*
    *   *Ejemplo: Si solo es un abono parcial, escribe la cantidad abonada.*
3.  Verás que el campo **"Monto"** (total general arriba) se actualiza solo con la suma.

### Paso 3: Guardar y Timbrar
1.  Haz clic en **"Guardar Borrador"** (icono de disquete 💾).
2.  Revisa que los datos sean correctos.
3.  Presiona el botón **"Timbrar"** (icono de rayo ⚡) y confirma. El sistema solicitará confirmación ya que **esta acción es irreversible**.
4.  El sistema generará el **REP (Recibo Electrónico de Pago)** oficial con su Folio Fiscal (UUID).

### Paso 4: Enviar al Cliente
Una vez timbrado, se habilitarán los botones de acción:
*   **Enviar por Correo**: Da clic en el botón con el icono de sobre (✉️). Se pre-llenará el correo del cliente y se adjuntarán el PDF y XML.
*   **Ver PDF**: Para descargarlo tú mismo.

### ❌ Cancelación de Pagos
Si te equivocaste al hacer el recibo de pago:
1.  Abre el pago timbrado.
2.  Presiona el botón de **"Cancelar"** 🗑️.
3.  Selecciona el motivo y confirma la cancelación.

---

## 📋 7. Presupuestos (Cotizaciones)

El módulo de Presupuestos te permite enviar cotizaciones formales a tus clientes antes de facturar.

### 7.1 Crear un Presupuesto
1.  Ve al menú **Presupuestos** y presiona **"+ Nuevo Presupuesto"**.
2.  Selecciona el **Cliente** y la **Empresa** emisora.
3.  Agrega los conceptos (productos o servicios) igual que en una factura.
4.  Haz clic en **Guardar**. El presupuesto queda en estado **BORRADOR**.

### 7.2 Estados del Presupuesto
Un presupuesto puede estar en los siguientes estados:
*   **Borrador**: Recién creado, aún no enviado.
*   **Enviado**: Ya fue enviado al cliente por correo.
*   **Aceptado**: El cliente confirmó que procede.
*   **Rechazado**: El cliente no aceptó la cotización.
*   **Facturado**: Ya se convirtió en factura oficial.

### 7.3 Enviar al Cliente
1.  Abre el presupuesto.
2.  Presiona el botón **"Enviar"** (icono de sobre ✉️).
3.  El sistema enviará un correo al cliente con el PDF adjunto y cambiará el estado a **Enviado**.

### 7.4 Cambiar el Estado
Para marcar un presupuesto como Aceptado, Rechazado o Facturado:
1.  Abre el presupuesto.
2.  Usa el selector de **Estado** en la parte superior del formulario.
3.  Guarda los cambios.

### 7.5 Eliminar un Presupuesto
Solo se pueden eliminar presupuestos en estado **Borrador**.
1.  Abre el presupuesto.
2.  Presiona el botón **"Eliminar"** y confirma.

---

## 💰 8. Cobranza: Recupera tu Dinero

Gestiona de forma proactiva a los clientes que te deben dinero para mejorar tu flujo de efectivo.

### 8.1 Dashboard (Tu Tablero de Control)
Al entrar a "Cobranza", verás indicadores clave:
*   **KPIs**: Cuánto te deben en total, cuánto está vencido (urgente) y cuánto está vigente.
*   **Gráfico de Antigüedad**: Te muestra visualmente qué tan vieja es la cartera.
*   **Top Deudores**: Lista rápida de quiénes te deben más dinero.

### 8.2 Reporte de Antigüedad (Antigüedad de Saldos)
Es la tabla principal donde ves cliente por cliente.
*   **Colores de Alerta**:
    *   **Verde**: Saldo Vigente (aún no vence).
    *   **Amarillo**: Vencido de 1-30 días (primer aviso).
    *   **Naranja**: Vencido de 31-60 días y 61-90 días (atención media).
    *   **Rojo**: Vencido más de 90 días (crítico).
*   **Acciones Rápidas**:
    1.  **Estado de Cuenta (PDF)**: Da clic en el icono de **PDF** para ver y descargar el documento.
    2.  **Enviar por Correo**: Da clic en el icono de **Sobre (✉️)**.
        *   Se abrirá una ventana para confirmar los destinatarios.
        *   Se adjunta el PDF automáticamente.
    3.  **Bitácora (Notas)**: Da clic en el icono de **Libreta**.
        *   Aquí puedes anotar: "Hablé con contabilidad, prometen pago el viernes".
        *   También verás el **historial automático** de cuándo les enviaste el estado de cuenta.

---

## 💸 9. Control de Gastos (Egresos)

Registra tus compras para saber en qué se va el dinero.

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

---

## ⚙️ 10. Administración de Empresas (Solo Gerentes)

### Agregar Nueva Empresa
Si tienes varias razones sociales, regístralas aquí para mantenerlas separadas.

1.  Ve a **Empresas** > **"+ Nueva Empresa"**.
2.  **Llenado de Datos**:
    *   Puedes usar el botón **"Subir PDF Constancia"** para ahorrar tiempo (igual que en Clientes).
    *   **Certificados Digitales (CSD)**: En la parte inferior, sube los archivos `.cer` y `.key` que te dio el SAT, y escribe la **Contraseña** de la llave privada. Sin esto, no podrás timbrar.
    *   **Logo**: Sube tu logo para que aparezca en los PDFs.
        *   El logo debe ser en formato **PNG** y pesar máximo **2 MB**.
3.  **Correo Electrónico**:
    *   Una vez guardada la empresa, busca el botón **"Configurar Correo Electrónico"**.
    *   Aquí pones los datos de tu servidor SMTP (ej. Gmail, Outlook) para que las facturas se envíen automáticamente desde tu cuenta.
    *   Cuando la empresa tiene correo configurado, verás una palomita verde (✅) en el listado de empresas.

---

## 👥 11. Gestión de Usuarios
Dales acceso a tus empleados sin compartir tu contraseña.

1.  Ve al menú **Usuarios** (solo visible para Administradores).
2.  Presiona **"+ Nuevo Usuario"**.
3.  **Roles**:
    *   **Administrador**: Tiene acceso a TODO, incluyendo todas las empresas.
    *   **Supervisor**: Puede ver y crear registros, pero solo de la empresa que le asignes.
4.  Si eliges "Supervisor", selecciona la **Empresa Asignada**.
5.  Crea su contraseña inicial y compártesela de forma segura.

---

## 🔍 12. Auditoría (Solo Gerentes)

El módulo de Auditoría está disponible únicamente para usuarios autorizados. Permite ver **qué hizo cada usuario** en el sistema.

### ¿Para qué sirve?
*   Saber quién timbró, canceló o eliminó una factura y a qué hora.
*   Ver qué información se ha exportado a Excel y por quién.
*   Monitorear los envíos de correo realizados.
*   Detectar actividad inusual o errores de operación.

### Cómo usar los filtros
1.  Ve al menú **Auditoría** (solo aparece si tienes acceso).
2.  Filtra por:
    *   **Empresa**: Selecciona la razón social que quieres revisar.
    *   **Email usuario**: Escribe el correo del empleado para ver solo sus acciones.
    *   **Acción**: Filtra por tipo de evento (Crear Factura, Exportar Excel, Login, etc.).
    *   **Rango de fechas**: Acota el período de tiempo.
3.  La tabla muestra: fecha/hora, usuario, acción realizada, entidad afectada y detalle adicional.

### Tipos de eventos registrados
| Evento | Cuándo ocurre |
|---|---|
| LOGIN | Cada vez que un usuario inicia sesión |
| CREAR / TIMBRAR / CANCELAR FACTURA | Al crear, timbrar o cancelar una factura |
| CREAR / TIMBRAR / CANCELAR PAGO | Al operar complementos de pago |
| ENVIAR FACTURA / PAGO EMAIL | Al enviar documentos por correo |
| CREAR / ACTUALIZAR / ELIMINAR CLIENTE | Al modificar el catálogo de clientes |
| CREAR / ACTUALIZAR / ELIMINAR EGRESO | Al operar gastos |
| EXPORTAR EXCEL | Al descargar cualquier reporte en Excel |
| CREAR / ACTUALIZAR EMPRESA | Al modificar datos de la empresa |
| Operaciones de Presupuesto | Crear, actualizar, enviar, cambiar estado |

---

## ⚠️ Glosario Rápido
*   **Timbrar**: Avisarle al SAT que hiciste una factura. Es irreversible (tienes que cancelar si te equivocas).
*   **UUID**: Es el "Folio Fiscal". Un código largo que es la verdadera identificación de la factura ante el SAT.
*   **PUE**: "Pago en Una sola Exhibición". Úsalo para ventas de contado.
*   **PPD**: "Pago en Parcialidades o Diferido". Úsalo para crédito.
*   **REP**: Recibo Electrónico de Pago. El complemento de pago timbrado.
*   **CSF**: Constancia de Situación Fiscal. El documento "acta de nacimiento" fiscal de tu cliente.
*   **CSD**: Certificado de Sello Digital. Los archivos `.cer` y `.key` que usa el SAT para validar tus facturas.
*   **CFDI**: Comprobante Fiscal Digital por Internet. El término técnico de una "factura electrónica".
*   **EN CANCELACIÓN**: Estado intermedio de una factura. La solicitud de cancelación ya fue enviada al SAT pero el receptor aún no ha respondido. La factura sigue siendo válida hasta que se confirme la cancelación.
*   **Motivo 01**: Motivo de cancelación que requiere aprobación del receptor (implica sustitución por otra factura). Activa el período de espera de 72 horas hábiles.
*   **Motivos 02/03/04**: Motivos de cancelación que no requieren aprobación del receptor. Se procesan de inmediato.

---
