# Especificación — App «Parte piloto privado» (cliente de `leulit_parte_privado`)

Fecha: 2026-09-03
Módulo servidor: `addons/leulit_parte_privado` (Odoo 17 Community)
Destinatario: desarrollador frontend que implementa el cliente móvil.

Este documento describe **todo lo necesario para implementar un cliente** que haga
las mismas operaciones que hoy se hacen desde el módulo, atacando Odoo por
JSON-RPC. No requiere ningún cambio en el servidor.

---

## 0. Alcance y decisiones ya tomadas

Estas decisiones están cerradas; no hay que volver a discutirlas.

1. **Contrato: JSON-RPC directo contra el wizard existente.** El cliente hace
   `create` sobre `leulit.parte.privado.wizard` y llama a su método `finalizar`.
   No hay ni habrá controller REST propio.
2. **La app es exclusivamente para pilotos privados.** El usuario que se
   autentica *es* el piloto. Si el usuario autenticado no resuelve a un
   `leulit.piloto` con `privado = True`, **el login se rechaza** (ver §2.2).
3. **Coexiste con el canal web, que es otro caso de uso.** En el Odoo web el
   mismo wizard lo usa personal administrativo autorizado, que transcribe el
   parte *en nombre de* un piloto. La app cubre el caso en que el piloto lo
   introduce él mismo. El servidor es idéntico para los dos.
4. **Operaciones que cubre la app:** listar sus partes, abrir la ficha de uno
   anterior en solo lectura, crear uno nuevo, y descargar los PDF firmados.
5. **Solo online.** Sin cobertura no se puede redactar ni enviar. La única
   persistencia local es el registro del envío pendiente de confirmar (§9).
6. **Nada es editable a posteriori.** Un parte cerrado está firmado
   electrónicamente y no se toca. Uno fallido tampoco se recupera: si el piloto
   se equivocó, mete uno nuevo.

---

## 1. Qué hace el servidor, en una pantalla

`leulit.parte.privado.wizard` es un `TransientModel` con 16 campos y un método,
`finalizar()`. Ese método, en una sola llamada:

1. Resuelve el `res.users` activo del piloto.
2. Crea un `leulit.vuelo` **con `with_user(usuario_piloto)`**, de modo que
   `create_uid` y el chatter queden a nombre del piloto.
3. Rellena por su cuenta todo lo que el piloto no transcribe: pesos, velocidad,
   consumo, tacómetro de salida y combustible remanente del último vuelo cerrado
   de esa máquina (`onchange_helicoptero`), distancia y combustibles
   (`calculosFuel`), y un repostaje ficticio si el remanente no llega al mínimo.
4. Recorre la **cadena A** (prevuelo → postvuelo): 8 validadores.
5. **Firma 1**: el vuelo pasa a `postvuelo`, se generan y firman POV y PTV
   (y F27 si es EC120B en primer vuelo del día).
6. Recorre la **cadena B** (postvuelo → cerrado): 9 validadores.
7. Comprueba el límite de actividad aérea del piloto.
8. **Firma 2**: el vuelo pasa a `cerrado` y `control_firma = 'firmado'`.
9. Escribe una nota en el chatter y cierra el wizard.

Es decir: **una sola llamada del cliente produce un parte de vuelo completo,
cerrado y firmado**. No hay estados intermedios que el cliente deba pilotar.

Lo que este flujo **no** pide, a diferencia del parte de vuelo normal:
meteorología, masa y centrado (W&B), performance, perfiles de formación, parte
de escuela, combustible y aceite transcritos. Todo eso o se omite o lo calcula
el servidor.

---

## 2. Acceso

### 2.1 Autenticación

Igual que la app de partes de vuelo normal (ver §11.1 de
`2026-08-18-app-parte-vuelo-spec.md`). Resumido:

```http
POST https://erp.helipistas.com/web/session/authenticate
Content-Type: application/json

{"jsonrpc":"2.0","method":"call","params":{
  "db":"<nombre_bd>","login":"<usuario>","password":"<contraseña>"}}
```

La respuesta trae `result.uid` y `result.user_context`, y devuelve una cookie
`session_id` que hay que conservar (`CookieJar`) y mandar en todas las llamadas
siguientes, incluidas las descargas de PDF.

- Cierre de sesión: `POST /web/session/destroy`
- Sesión viva: `POST /web/session/get_session_info`
- Sesión caducada: el servidor devuelve
  `odoo.http.SessionExpiredException` → re-login transparente y reintento
  **solo de operaciones de lectura**. Nunca reintentar `finalizar` de forma
  automática (§9).

### 2.2 Puerta de login: solo pilotos privados

Inmediatamente después de autenticar, y antes de mostrar ninguna pantalla:

```
1. uid ← result.uid
2. res.users.read([uid], ['partner_id'])          → partner_id
3. leulit.piloto.search_read(
       [('partner_id','=',partner_id), ('privado','=',True)],
       ['id','name'])
4. Si el resultado está vacío  → cerrar sesión y mostrar
   «Esta aplicación es solo para pilotos privados.»
   Si trae un registro       → guardar ese id como `mi_piloto_id`.
```

`mi_piloto_id` es el eje de toda la app: filtra el listado y es el `piloto_id`
que se manda al crear. **Nunca se ofrece un selector de piloto.**

### 2.3 Grupos que necesita el usuario

Dos:

- **`leulit.RBase`** — de donde salen los catálogos: `leulit.helicoptero`,
  `leulit.piloto`, `leulit.helipuerto`, `leulit.vuelostipo`, `leulit.vuelo` y
  `leulit_signaturedoc` están todos concedidos a este grupo. **Cualquier usuario
  del ERP ya lo tiene**; es la base sobre la que se monta el resto de roles.
  No hay que hacer nada.
- **`leulit.ROperaciones_parte_privado`** — lo da este módulo, y es el único que
  hay que conceder expresamente. Concede crear/escribir sobre
  `leulit.parte.privado.wizard` y **lectura sobre `sale.order`** (los
  presupuestos).

Detalle de implementación, por si aparece un `AccessError` raro durante el
desarrollo: `ROperaciones_parte_privado` no declara `implied_ids`, y la cadena de
roles de operaciones (`ROperaciones_piloto` → `operador` → `alumno` →
`piloto_externo`) tampoco encadena a `RBase`. `RBase` llega por el rol base del
empleado (`RBase_employee` / `RBase_hide`) o por asignación directa. En la
práctica todos los pilotos lo tienen, pero si un usuario recién creado solo
llevara el grupo del módulo, se autenticaría y vería todos los desplegables
vacíos. Es el primer sitio donde mirar ante ese síntoma.

Efecto lateral conocido y aceptado: dar `ROperaciones_parte_privado` a un piloto
también le hace visible el menú «Operaciones > Vuelos > Parte piloto privado» si
alguna vez entra por el Odoo web. No es un problema — hace exactamente lo mismo
que la app.

### 2.3.1 Situación en producción a 2026-09-03

Comprobado sobre la base de datos real, y relevante para planificar el
despliegue:

- El módulo está instalado en producción desde el 2026-09-02.
- Hay **5 pilotos** marcados con `privado = True`.
- De ellos, **3 tienen usuario activo** en el ERP; los otros 2 no. Esos 2 no
  pueden usar la app, y tampoco se les puede transcribir el parte desde el web:
  `finalizar()` fallará con el error nº 3 del §8.1.
- **Ninguno de los 5 tiene todavía `ROperaciones_parte_privado`.** El grupo solo
  lo llevan hoy dos usuarios de oficina. Antes de las pruebas de la app hay que
  concedérselo a los pilotos que vayan a usarla.

### 2.4 Prerrequisitos de datos (fuera del control de la app)

Si alguno falta, `finalizar()` fallará. Conviene que el equipo lo verifique
antes de dar de alta a un piloto en la app:

- **Piloto**: check `privado` marcado en su ficha, y un `res.users` **activo**
  enlazado a su `partner_id`. Si vuela EC120B, además firma escaneada en ficha
  (`piloto.firma`) para poder generar el F27.
- **Helicóptero**: `statemachine = 'En servicio'`, sin anomalías/discrepancias
  sin firmar, sin anotaciones activas de technical log, y con `consumomedio` y
  `velocidad` informados en la ficha. Sin `velocidad` el servidor calcula
  distancia 0 y el parte se rechaza.
- **Presupuesto**: al menos un `sale.order` con `flag_flight_part = True`,
  `state = 'sale'` y `task_done = False`.
- **Orden cronológico**: los partes de una misma máquina deben introducirse en
  orden real, uno detrás de otro. La cadena rechaza un parte que quede por
  detrás en el tiempo de otro ya en postvuelo o cerrado de esa máquina.

### 2.5 Sin restricciones a nivel de fila

**No existe ninguna `ir.rule` sobre `leulit.vuelo`.** Cualquier usuario con
`RBase` puede leer todos los vuelos de la compañía. El filtrado por piloto que
hace la app es una decisión de producto, no una barrera de seguridad; no se debe
presentar al usuario como si lo fuera.

---

## 3. Transporte JSON-RPC

### 3.1 Llamada genérica

```http
POST https://erp.helipistas.com/web/dataset/call_kw
Content-Type: application/json

{"jsonrpc":"2.0","method":"call","params":{
  "model":"<modelo>",
  "method":"<método>",
  "args":[ ... ],
  "kwargs":{ ... }}}
```

Métodos que usa esta app, y ninguno más:

- `search_read` — catálogos y listado.
- `read` — ficha de un parte.
- `create` — el registro del wizard.
- `finalizar` — el botón, con `args: [[wizard_id]]`.
- `name_search` — búsqueda incremental en los desplegables largos
  (helipuertos): `args: []`, `kwargs: {name, args: <domain>, operator: 'ilike', limit: 20}`.

**No** hace falta `onchange` en ningún punto (§6.3), **ni** `web_save`, **ni**
comandos x2many.

### 3.2 Formato de horas — `float_time`

Todas las horas y duraciones son `Float` en horas decimales:

- `10:30` → `10.5`
- `1:12` → `1.2`
- **6 minutos → `0.1`**. Es la unidad mínima de todo el sistema.

Conversión: `horas = floor(v)`, `minutos = round((v - floor(v)) * 60)`.
Al construir el valor, redondear a 2 decimales.

Las horas son **locales**, no UTC. No aplicar ninguna conversión de zona.

### 3.3 Errores

Odoo devuelve **HTTP 200** con un objeto `error` en el cuerpo:

```json
{"error":{"code":200,"message":"Odoo Server Error",
 "data":{"name":"odoo.exceptions.UserError",
         "message":"Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM",
         "arguments":[...],"debug":"..."}}}
```

Tratamiento obligatorio por `data.name`:

- `odoo.exceptions.UserError` — diálogo con `data.message` **íntegro**. Son
  mensajes de negocio redactados en castellano para el piloto. No reescribirlos
  ni resumirlos.
- `odoo.exceptions.ValidationError` — igual; si se puede inferir el campo,
  asociarlo a él.
- `odoo.exceptions.AccessError` — «No tiene permisos» + `data.message`.
  En esta app casi siempre significa que falta un grupo (§2.3).
- `odoo.exceptions.MissingError` — el registro ya no existe → volver al listado.
- `odoo.http.SessionExpiredException` — re-login y reintento, **salvo en
  `finalizar`** (§9).
- Cualquier otro — error genérico + `data.debug` a telemetría.

### 3.4 Qué del spec grande NO aplica aquí

`2026-08-18-app-parte-vuelo-spec.md` documenta la app del parte de vuelo
completo. Sirve como referencia para §11 (integración JSON-RPC) y poco más.
**No abrir ni implementar** estas secciones, no tienen equivalente en el parte
privado:

- §2 máquina de estados de tres campos y `estado_vista` — aquí el vuelo nace y
  muere en una sola llamada.
- §4 catálogo de ~200 campos del parte — aquí son 16 (§6).
- §6 lógica derivada, `onchange helicoptero_id`, `calculosFuel` — lo ejecuta el
  servidor dentro de `finalizar()`, el cliente no lo toca.
- §8 flujo de firma OTP con QR — aquí la firma es automática, sin interacción.
- §9 Weight & Balance completo.
- §10 Performance.
- §15 vista de lista del parte normal.

---

## 4. Pantallas

Cuatro. Descritas como estructura de datos, no como diseño.

### 4.1 Listado de partes

Es la pantalla de arranque tras el login.

**Consulta:**

```json
{"model":"leulit.vuelo","method":"search_read",
 "args":[[["piloto_id","=",<mi_piloto_id>]],
         ["id","codigo","fechavuelo","horasalida","horallegada","tiemposervicio",
          "airtime","helicoptero_id","lugarsalida","lugarllegada",
          "estado","control_firma","comentarios","privado_introducido_por"]],
 "kwargs":{"order":"fechavuelo desc, horasalida desc","limit":50,"offset":0}}
```

Paginar con `limit`/`offset`. `search_count` con el mismo dominio da el total.

**Nota sobre el dominio:** son *todos* los vuelos del piloto, no solo los
introducidos por esta vía. Un piloto privado que en algún momento haya volado
por el flujo normal verá también aquellos. Es lo correcto: el listado es su
historial de vuelo, no el log de la aplicación. `privado_introducido_por` se
trae igualmente porque permite distinguirlos (§4.2).

**Cada fila muestra:** `fechavuelo`, `horasalida`–`horallegada`,
`helicoptero_id[1]` (matrícula), `lugarsalida[1]` → `lugarllegada[1]`,
`tiemposervicio`, y **el estado** según §4.1.1.

#### 4.1.1 Los cuatro estados que ve el piloto

El servidor tiene `estado` (`prevuelo` / `postvuelo` / `cerrado` / `cancelado`)
y `control_firma` (`no-firmado` / `pendiente` / `firmado`). La app los traduce a
cuatro etiquetas:

- **Pendiente de finalizar** — estado **local**, no existe en el servidor. Se
  envió un `finalizar` y todavía no hay confirmación (§9). Es el único estado
  desde el que se puede reintentar.
- **Finalizado** — `estado = 'cerrado'` **y** `control_firma = 'firmado'`.
  Es el único desenlace bueno. Tiene PDF firmados descargables.
- **Fallido** — `estado = 'cancelado'`. El motivo está en `comentarios`, con el
  prefijo `Parte piloto privado fallido:`. No se recupera; hay que meter otro
  parte.
- **Incompleto** — `estado` es `prevuelo` o `postvuelo`. **No es un estado
  normal en esta app**: significa que el proceso murió a media transacción
  (worker reiniciado, despliegue a mitad) sin llegar a ejecutar el manejador de
  error del servidor. El parte existe a medias. La app lo muestra en solo
  lectura y avisa de que hay que resolverlo desde oficina por el flujo web
  normal. Ni reintentar ni dar por bueno.

Este cuarto caso no es hipotético: los validadores del servidor hacen
`cr.commit()` por el camino, así que un corte a mitad deja trabajo confirmado en
base de datos.

#### 4.1.2 Filtro por estado

El listado ofrece filtrar por esas cuatro etiquetas, multiselección, todas
activas por defecto.

- **Finalizado** → añadir al dominio `["estado","=","cerrado"],["control_firma","=","firmado"]`
- **Fallido** → `["estado","=","cancelado"]`
- **Incompleto** → `["estado","in",["prevuelo","postvuelo"]]`
- **Pendiente de finalizar** → **no va al dominio**: son registros del almacén
  local. Se mezclan en la cabecera del listado, ordenados por fecha como el
  resto.

Al combinar varios filtros, unir las cláusulas con `|` en notación polaca de
Odoo. Si el usuario deselecciona todos, mostrar el listado completo, no vacío.

### 4.2 Ficha de un parte — solo lectura, siempre

Se abre pulsando una fila. **No hay edición, ni reintento, ni cancelación desde
aquí.** Un `read` sobre el `id` con los campos:

- **Identificación:** `codigo`, `estado`, `control_firma`, `fechavuelo`
- **Vuelo:** `helicoptero_id`, `piloto_id`, `presupuesto_vuelo`, `numpax`
- **Trayecto:** `lugarsalida`, `lugarllegada`, `horasalida`, `horallegada`,
  `tiemposervicio`, `airtime`
- **Contadores:** `tacomsalida`, `tacomllegada`, `ngvuelo`, `nfvuelo`
- **Combustible (informativo, lo calculó el servidor):** `fuelsalida`,
  `fuelllegada`, `combustibleminimo`, `consumomedio_vuelo`
- **Observaciones:** `comentarios`
- **Trazabilidad:** `privado_introducido_por`

Si `privado_introducido_por` está informado y coincide con el propio piloto, el
parte lo metió él por la app. Si está informado y es otro usuario, lo transcribió
oficina por el web. Si está vacío, es un vuelo del flujo normal.

Si el estado es **Fallido**, mostrar `comentarios` de forma destacada: ahí está
el motivo del fallo.

Si el estado es **Finalizado**, mostrar el acceso a los documentos (§4.4).

### 4.3 Alta de un parte nuevo

Un formulario con los grupos y el orden del wizard del servidor. El orden no es
libre: los Contadores cambian según el helicóptero elegido, y equivocarse ahí es
un error del servidor a los 30 segundos de espera. Detalle campo a campo en §6.

- **Vuelo:** `fechavuelo`, `helicoptero_id`, `presupuesto_vuelo`,
  `vuelo_tipo_id`, `numpax`
  (`piloto_id` no se muestra como selector: es el usuario logueado; puede
  mostrarse como texto fijo)
- **Trayecto:** `lugarsalida`, `lugarllegada`, `horasalida`, `tiemposervicio`,
  y a continuación `horallegada` y `airtime` **calculados y no editables**
- **Contadores:**
  - helicóptero **distinto** de EC120B → solo `tacomllegada`, obligatorio
  - helicóptero **EC120B** → solo `ngvuelo` y `nfvuelo`, ambos obligatorios
  - el grupo se reconstruye al cambiar `helicoptero_id`
- **Observaciones:** `comentarios` (texto libre, opcional) y `declaracion`
  (check obligatorio)

Botón **Finalizar**. Antes de enviar, ejecutar las comprobaciones de §8.0.

### 4.4 Documentos firmados

Accesible desde la ficha de un parte **Finalizado**. Ver §10.

---

## 5. Catálogos y dominios

Se cargan al entrar en el alta. Son pequeños salvo los helipuertos.

- **Helicópteros** — `leulit.helicoptero`, campos `id`, `name` (matrícula),
  `tipo`, `statemachine`, `velocidad`, `consumomedio`.
  Dominio: `[('baja','=',False)]`.
  `tipo` es el que decide qué contadores se piden; guardarlo en cliente.
- **Presupuestos** — `sale.order`, campos `id`, `name`, `partner_id`.
  Dominio: `[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)]`.
  Recargar cada vez que se abre el alta: un presupuesto puede agotarse entre
  sesiones.
- **Tipos de vuelo** — `leulit.vuelostipo`, campos `id`, `name`.
  Dominio: `[('tipo_trabajo','=','NCO')]`. **Obligatorio respetarlo**: un tipo
  que no sea NCO hace fallar la cadena si hay pasajeros.
- **Helipuertos** — `leulit.helipuerto`, campos `id`, `display_name`
  (`display_name` es `(INDICATIVO) Descripción`; `name` a secas es solo el
  indicativo OACI). Sin dominio. Son muchos: usar `name_search` con `ilike` y
  `limit: 20` en vez de descargar el catálogo entero.
- **Piloto** — no es un catálogo: es `mi_piloto_id` de §2.2.

---

## 6. Campos del alta, uno a uno

Modelo destino: `leulit.parte.privado.wizard`.

### 6.1 Los que envía el cliente

- **`fechavuelo`** · `Date` · obligatorio · formato `YYYY-MM-DD`.
  Por defecto, hoy. Puede ser pasada (es un parte transcrito de papel).
- **`helicoptero_id`** · `Many2one(leulit.helicoptero)` · obligatorio · entero.
- **`piloto_id`** · `Many2one(leulit.piloto)` · obligatorio · entero.
  **Siempre `mi_piloto_id`.**
- **`presupuesto_vuelo`** · `Many2one(sale.order)` · obligatorio · entero.
- **`vuelo_tipo_id`** · `Many2one(leulit.vuelostipo)` · obligatorio · entero.
- **`numpax`** · `Integer` · por defecto `1` · número de pasajeros / AESA.
  Puede ser 0.
- **`lugarsalida`** · `Many2one(leulit.helipuerto)` · obligatorio · entero.
- **`lugarllegada`** · `Many2one(leulit.helipuerto)` · obligatorio · entero.
- **`horasalida`** · `Float` hora local · obligatorio · > 0.
- **`tiemposervicio`** · `Float` horas · obligatorio · **múltiplo de 0.1
  (6 minutos)** y **≤ 3.0**.
- **`tacomllegada`** · `Float` · obligatorio **si el helicóptero no es EC120B**,
  no enviar si lo es.
- **`ngvuelo`** · `Float` · obligatorio **solo si es EC120B** · > 0 y ≤ 4.
- **`nfvuelo`** · `Float` · obligatorio **solo si es EC120B** · > 0 y ≤ 4.
- **`comentarios`** · `Text` · opcional · observaciones (O.V.) del parte.
- **`declaracion`** · `Boolean` · **debe ir a `true`**. Corresponde a
  «Inspección prevuelo, briefing, NOTAM y debriefing realizados». El servidor
  rechaza el parte si va a `false`.

### 6.2 Los que calcula el servidor y el cliente solo muestra

- **`horallegada`** · `Float` · `horasalida + tiemposervicio`, y si el resultado
  es ≥ 24.0 se le restan 24 (cruce de medianoche).
- **`airtime`** · `Float` · `max(tiemposervicio - 0.1, 0.0)`. Son los 6 minutos
  de arranque y parada que el PTV en papel descuenta.

Son campos `compute` no almacenados: **no se envían en el `create`** y no se
pueden escribir. El cliente los replica localmente con esas dos fórmulas para
enseñarlos mientras el piloto teclea. Son triviales y no necesitan viaje al
servidor.

- **`helicoptero_tipo`** · `Selection` relacionado con `helicoptero_id.tipo`.
  El cliente ya lo tiene del catálogo (§5); no hace falta leerlo del wizard.

### 6.3 Por qué no hay `onchange`

El wizard no define ningún `@api.onchange`. Los dos campos derivados son
`compute` puros y se calculan en cliente. Los cálculos pesados —pesos,
combustible, distancia, tacómetro de salida— los hace `finalizar()` sobre el
`leulit.vuelo` ya creado, no sobre el wizard. **El cliente no debe llamar a
`onchange` en ningún momento.**

### 6.4 Lo que el piloto NO rellena, y por qué

Para que nadie eche de menos campos del parte de papel:

- **Combustible añadido y de llegada** — el servidor arranca del remanente del
  último vuelo cerrado de esa máquina; si no cubre el mínimo legal que él mismo
  calcula, reposta lo justo (+1 litro de margen) y estima la llegada como
  `salida − consumo medio × tiempo de servicio`. No hay campo en el formulario.
- **Aceite** — fijo a 0.
- **Meteorología** — no se pide y el campo queda vacío. El validador que la
  exigiría está deliberadamente fuera de esta cadena.
- **Masa y centrado (W&B) y performance** — van manuscritos en el PTV de papel;
  no se transcriben ni se validan.
- **PAE / tripulantes con función** — fijo a 0; un vuelo NCO no los admite.
- **Tacómetro de salida** — lo hereda del último vuelo cerrado.
- **Ruta, alternativos, aterrizajes nocturnos, gancho, IFR, flotadores…** — se
  quedan con los valores por defecto del modelo.

---

## 7. Secuencia de creación

Dos llamadas. Ni una más.

### 7.1 Crear el registro del wizard

```json
{"model":"leulit.parte.privado.wizard","method":"create",
 "args":[{
   "fechavuelo":"2026-09-01",
   "helicoptero_id":3,
   "piloto_id":12,
   "presupuesto_vuelo":845,
   "vuelo_tipo_id":7,
   "numpax":1,
   "lugarsalida":21,
   "lugarllegada":21,
   "horasalida":10.5,
   "tiemposervicio":1.2,
   "tacomllegada":3412.7,
   "comentarios":"Vuelo local sin novedad",
   "declaracion":true
 }],
 "kwargs":{"context":{"lang":"es_ES","tz":"Europe/Madrid"}}}
```

Devuelve el `id` del registro transitorio. Esta llamada es barata y no tiene
efectos: si falla, ha sido un problema de tipos o de permisos.

Para un EC120B, sustituir `tacomllegada` por `ngvuelo` y `nfvuelo`.

### 7.2 Ejecutar `finalizar`

```json
{"model":"leulit.parte.privado.wizard","method":"finalizar",
 "args":[[<wizard_id>]],
 "kwargs":{"context":{"lang":"es_ES","tz":"Europe/Madrid"}}}
```

**Respuesta en caso de éxito:** `{"result": {"type": "ir.actions.act_window_close"}}`.
Es la acción con la que Odoo cierra el diálogo en el web. **El cliente la
ignora**: no lleva ni el id ni el código del vuelo creado. La confirmación real
se obtiene consultando el listado (§9.2).

**Esta es la llamada cara.** Crea el vuelo, recorre 17 validadores, genera 2 o 3
PDF y los firma. Recomendaciones:

- **Timeout de al menos 120 segundos.** El de 30 s por defecto de la mayoría de
  clientes HTTP es insuficiente y provoca el escenario del §9.
- Bloquear la interfaz con un indicador de progreso explícito. No es una
  operación instantánea y el piloto tiene que saberlo.
- Registrar el intento en el almacén local **antes** de enviar (§9.1).

---

## 8. Catálogo completo de validaciones

Exhaustivo, en el orden real de ejecución. De cada una: la condición, el mensaje
literal que devuelve el servidor, y si el cliente puede anticiparla.

Tres categorías de anticipación:

- **Local** — el cliente lo comprueba con lo que ya tiene en pantalla. Debe
  hacerlo: ahorra 2 minutos de espera y un error incomprensible.
- **Consultable** — el cliente puede anticiparlo con un `search_count` o un
  `read` previo. Opcional, pero recomendado para las marcadas como frecuentes.
- **Servidor** — depende de cálculos internos que el cliente no reproduce.
  Solo cabe mostrar el mensaje.

### 8.0 Comprobaciones que el cliente hace antes de enviar

Resumen operativo. Si alguna falla, no llamar a `finalizar`: mostrar el motivo
concreto y dejar al piloto corregirlo. **Nunca dejar que envíe un parte que se
sabe que va a ser rechazado**: la llamada tarda hasta dos minutos y el mensaje
que recibiría puede no tener nada que ver con la causa real (§11.1).

1. Todos los campos obligatorios de §6.1 informados.
2. `declaracion == true`.
3. `round(tiemposervicio * 60) % 6 == 0`.
4. `tiemposervicio > 0` y `tiemposervicio <= 3.0`.
5. `horasalida > 0`.
6. Si el helicóptero no es EC120B: `tacomllegada > 0`, y mayor que el
   `tacomllegada` del último vuelo cerrado de esa máquina (consultable, §8.4.7).
7. Si es EC120B: `ngvuelo > 0 && ngvuelo <= 4` y `nfvuelo > 0 && nfvuelo <= 4`.
8. `numpax >= 0`, y el tipo de vuelo elegido es de los NCO del catálogo.
9. El helicóptero elegido no está bloqueado por una anomalía sin firmar
   (§8.3.5). **Obligatorio, no opcional**: es la única forma de que el piloto se
   entere del motivo real. Sin esta consulta, el servidor le devolvería un error
   sobre la distancia prevista que no guarda ninguna relación aparente con la
   causa (§11.1).

### 8.1 Validaciones propias del wizard

Se ejecutan al principio de `finalizar()`, antes de crear nada. Un fallo aquí no
deja rastro en base de datos.

**1. Declaración sin marcar**
- Condición: `declaracion` es falso.
- Mensaje: «Debe confirmar la declaración de inspección prevuelo, briefing,
  NOTAM y debriefing.»
- Anticipación: **Local**.

**2. Tiempo de servicio no múltiplo de 6 minutos**
- Condición: `round(tiemposervicio * 60) % 6 != 0`.
- Mensaje: «El tiempo de servicio debe ser múltiplo de 6 minutos (el Air Time se
  calcula restando 6 minutos).»
- Anticipación: **Local**. La forma robusta en el formulario es no dejar
  introducir otra cosa: selector de minutos en pasos de 6.

**3. El piloto no tiene usuario en el ERP**
- Condición: `piloto_id.partner_id.user_ids` no contiene ningún usuario activo.
- Mensaje: «El piloto <nombre> no tiene usuario activo en el ERP; no se puede
  firmar en su nombre.»
- Anticipación: **Local, imposible en la app**. El piloto se ha autenticado con
  ese usuario, luego existe y está activo. Este error solo puede aparecer por el
  canal web. Se documenta por completitud.

### 8.2 Restricciones al crear el `leulit.vuelo`

Se disparan al insertar el registro. `create()` de `leulit.vuelo` **no** ejecuta
`checkValidCreateWriteData()`, así que las comprobaciones de solape se aplican
más tarde, en las cadenas.

**4. Airtime no múltiplo de 6 minutos** (`ValidationError`)
- Condición: `round(airtime * 60) % 6 != 0`.
- Mensaje: «El Airtime debe ser múltiplo de 6 minutos.»
- Anticipación: **Local**, y queda cubierta por la comprobación 2: si
  `tiemposervicio` es múltiplo de 0.1, `airtime = tiemposervicio - 0.1` también
  lo es.

**5. NG fuera de rango** (`ValidationError`)
- Condición: `ngvuelo > 4`.
- Mensaje: «El NG del vuelo no puede ser mayor de 4.»
- Anticipación: **Local**.

**6. NF fuera de rango** (`ValidationError`)
- Condición: `nfvuelo > 4`.
- Mensaje: «El NF del vuelo no puede ser mayor de 4.»
- Anticipación: **Local**.

### 8.3 Cadena A — prevuelo → postvuelo

Ocho eslabones, en este orden. A partir del primero hay `cr.commit()`
intercalados: un fallo aquí **sí** deja el vuelo creado, y el servidor lo marca
como `cancelado` (§9.3).

#### 8.3.1 `ComprobacionTripulacionEnVuelosPostvueloHandler`

**7. El piloto está en otro vuelo en postvuelo**
- Condición: existe cualquier `leulit.vuelo` con `estado = 'postvuelo'` en el que
  el piloto figure como piloto, operador, verificado o alumno.
- Mensaje: «Este vuelo no puede pasar a postvuelo. EL PILOTO ESTÁ EN UN VUELO EN
  ESTADO POST-VUELO» (o `EL OPERADOR` / `EL VERIFICADO` / `EL ALUMNO` según el
  rol).
- Anticipación: **Consultable**.
  `leulit.vuelo.search_count([('estado','=','postvuelo'),('piloto_id','=',mi_piloto_id)])`.
  Ojo: la comprobación del servidor recorre **todos** los vuelos en postvuelo del
  sistema, sin filtro de fecha. Un parte de otro piloto atascado en postvuelo con
  este piloto como tripulante bloquea el alta.

#### 8.3.2 `ComprobacionChecksHandler`

**8. Inspección prevuelo no marcada**
- Condición: `checklist_realizado` falso.
- Mensaje: «Este vuelo no puede pasar a postvuelo. NO HA MARCADO LA INSPECCIÓN
  PREVUELO CÓMO REALIZADA»
- Anticipación: **imposible que ocurra**. El wizard lo fija a `true`.

**9. Primer vuelo del día sin inspección BFF** (`check_first_flight`)
- Condición: helicóptero EC120B o CABRI G2, no hay ningún vuelo cerrado de esa
  máquina ese día, y `checklist_prevuelo_BFF` es falso.
- Mensaje: «Primer vuelo de este helicóptero hoy. Se debe hacer la inspección
  prevuelo BFF»
- Anticipación: **imposible que ocurra**. El wizard decide BFF o «entre vuelos»
  buscando si existe un vuelo cerrado de esa máquina, ese día, con hora de
  salida anterior.

**10. Vuelo posterior del día sin inspección entre vuelos** (`check_first_flight`)
- Condición: EC120B o CABRI G2, existe un vuelo cerrado ese día anterior a este,
  y `checklist_prevuelo_entre_vuelos` es falso.
- Mensaje: «Este helicóptero ya ha tenido un vuelo hoy. Se debe hacer la
  inspección entre vuelos. Vuelo anterior: <código>»
- Anticipación: **imposible que ocurra**, mismo motivo.

**11. Briefing no marcado**
- Condición: `briefing_realizado` falso.
- Mensaje: «Este vuelo no puede pasar a postvuelo. NO HA MARCADO EL BRIEFING
  AERODROMO SALIDA, LLEGADA Y ALTERNATIVOS CÓMO REALIZADO»
- Anticipación: **imposible que ocurra**. El wizard lo fija a `true` a partir del
  check `declaracion`.

#### 8.3.3 `ComprobacionTripulantesTipoActividadHandler`

**12. Pasajeros en un tipo de vuelo que no los admite**
- Condición: `numpax > 0` y el `tipo_trabajo` del tipo de vuelo no es `AOC` ni
  `NCO`.
- Mensaje: «Los unicos tipos de vuelo que pueden tener pasajeros son AOC y NCO.»
- Anticipación: **Local**, si se respeta el dominio `tipo_trabajo = 'NCO'` del
  catálogo (§5).

**13. Tripulantes con función en un vuelo NCO**
- Condición: `numpae > 0` y el tipo de actividad es `AOC` o `NCO`.
- Mensaje: «Los tipos de vuelo AOC y NCO no pueden tener tripulantes con
  funciones en el vuelo.»
- Anticipación: **imposible que ocurra**. El wizard fija `numpae = 0`.

#### 8.3.4 `ComprobacionUsuarioPilotoHandler`

**14. Quien firma no es el piloto**
- Condición: el `uid` que ejecuta no es el usuario del piloto ni el del piloto
  supervisor.
- Mensaje: «Solo el piloto o el piloto supervisor pueden cambiar el estado del
  vuelo a postvuelo»
- Anticipación: **imposible en circunstancias normales** — el wizard ejecuta con
  `with_user` del usuario del piloto. Ver la trampa de §11.3 para el caso en que
  un `res.partner` tenga más de un `res.users`.

#### 8.3.5 `ComprobacionHelicopteroHandler`

**15. Helicóptero en taller**
- Condición: `helicoptero_id.statemachine == 'En taller'`.
- Mensaje: «Este helicóptero está en Taller»
- Anticipación: **Local**. El campo viene en el catálogo (§5): no ofrecer en el
  desplegable los que estén en taller, o avisar al seleccionarlos.

**16. Anomalía o discrepancia sin firmar**
- Condición: `isHelicopterBlocked(helicoptero_id, fechavuelo)` — hay una anomalía
  «no go» abierta para esa máquina en esa fecha.
- Mensaje: «Este helicóptero tiene una anomalía/discrepancia sin firmar y no
  puede ser utilizado»
- Anticipación: **Consultable, y obligatoria.** Llamada:
  `{"model":"leulit.vuelo","method":"isHelicopterBlocked","args":[[],<helicoptero_id>,"<fechavuelo>"]}`
  → devuelve booleano.
  Hay que ejecutarla **al elegir helicóptero y al elegir fecha**, y volver a
  ejecutarla justo antes de enviar. Si devuelve `true`, bloquear el envío y
  mostrar el motivo con estas palabras: el helicóptero tiene una anomalía o
  discrepancia sin firmar y no puede volar hasta que se resuelva.
  El motivo por el que esto no es opcional está en §11.1: sin esta consulta el
  piloto recibe, dos minutos después, un mensaje sobre la distancia prevista que
  no tiene relación aparente con la causa, y no tiene forma de saber qué hacer.

**17. Anotación activa en el technical log**
- Condición: existe alguna `leulit.anotacion_technical_log` con `estado = 'active'`
  para esa máquina.
- Mensaje: «Este helicóptero tiene una anotación activa y no puede ser utilizado»
- Anticipación: **Consultable**:
  `leulit.anotacion_technical_log.search_count([('helicoptero_id','=',X),('estado','=','active')])`.

#### 8.3.6 `ComprobacionOverlapPartesEscuelaVueloHandler`

Este eslabón es el que impone el **orden cronológico**. Es la causa más frecuente
de rechazo en producción.

**18. Existe un parte posterior ya cerrado o en postvuelo de esa máquina**
- Condición: hay otro vuelo del mismo helicóptero con `fechasalida >=` la de este
  y estado distinto de `cancelado` y `prevuelo`.
- Mensaje: «Existe un parte de vuelo con el mismo helicóptero, posterior a la
  fecha indicada, en estado Post-Vuelo. Parte de vuelo: <código>»
- Anticipación: **Consultable**. Es el error a explicar bien al piloto: los
  partes de una máquina hay que meterlos en orden. Si ya se metió el del martes,
  no se puede meter el del lunes.

**19. Existe un parte anterior de esa máquina en prevuelo**
- Condición: hay otro vuelo del mismo helicóptero con `fechasalida <=` la de este
  y estado `prevuelo`.
- Mensaje: «Existe un parte de vuelo con el mismo helicóptero, anterior a la
  fecha indicada, en estado Prevuelo. Parte de vuelo: <código>»
- Anticipación: **Consultable**. Suele venir de un parte abandonado a medias por
  el flujo web; lo tiene que resolver oficina.

**20. Existe un parte anterior de ese piloto en prevuelo**
- Condición: igual que el anterior, pero filtrando por `piloto_id`.
- Mensaje: «Existe un parte de vuelo con el mismo piloto, anterior a la fecha
  indicada, en estado Prevuelo. Parte de vuelo: <código>»
- Anticipación: **Consultable**.

**21. Solape horario con otro vuelo del mismo día**
- Condición: existe un vuelo en `postvuelo` o `cerrado` en la misma fecha cuyo
  intervalo horario se solapa con este, y comparten tripulante.
- Mensaje: «Este vuelo no puede pasar a postvuelo. EL PILOTO ESTÁ EN UN VUELO EN
  ESTADO POST-VUELO O CERRADO (SOLAPAMIENTO)» (o el rol correspondiente).
- Anticipación: **Consultable**. El cliente puede traerse los vuelos del piloto
  de esa fecha y comprobar el solape con `horasalida` / `horallegada` antes de
  enviar.

**22. El piloto está dando clase a esa hora**
- Condición: el piloto figura como profesor en un `leulit.parte_escuela` cerrado
  de esa fecha cuyo horario solapa.
- Mensaje: «El piloto o el piloto supervisor esta de profesor en un parte de
  escuela para la fecha y hora indicada. Parte de escuela: <id>»
- Anticipación: **Servidor**. Poco probable en un piloto privado.

#### 8.3.7 `DatosGeneralesPrivadoHandler`

Es el único validador propio del módulo: reproduce el general del flujo normal
**quitando** meteo, centro de gravedad, performance y cuadre de pasajeros de W&B.

**23. Distancia total prevista a cero**
- Condición: `distanciatotalprevista == 0`.
- Mensaje: «Distancia total prevista no válida »
- Anticipación: **Servidor**, pero casi siempre es un síntoma, no la causa: ver
  la trampa §11.1. La distancia la calcula el servidor como
  `velocidad_crucero × tiempo de servicio`; sale 0 si el helicóptero no tiene
  `velocidad` en ficha, o si `onchange_helicoptero` abortó por máquina bloqueada.

**24. Número de tripulantes a cero**
- Condición: `numtripulacion == 0`.
- Mensaje: «Número de personas tripulación no válido »
- Anticipación: **imposible que ocurra**. El wizard fija 1.

**25. Tiempo previsto superior a 3 horas**
- Condición: `tiempoprevisto > 3.0` (y `tiempoprevisto` es el `tiemposervicio`
  del formulario).
- Mensaje: «El valor del tiempo previsto de vuelo no puede ser superior a 3
  horas»
- Anticipación: **Local**.

**26. NOTAM no revisado**
- Condición: `notam_revisado` falso.
- Mensaje: «Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM»
- Anticipación: **imposible que ocurra**; el wizard lo fija a `true` desde
  `declaracion`.

**27. Hora de salida no válida**
- Condición: `horasalida <= 0`.
- Mensaje: «Hora de salida no válida»
- Anticipación: **Local**.

**28. Tacómetro de salida no válido**
- Condición: `tacomsalida <= 0` y el helicóptero no es EC120B.
- Mensaje: «Valor tacómetro de salida no válido»
- Anticipación: **Consultable**. `tacomsalida` lo hereda el servidor del
  `tacomllegada` del último vuelo cerrado de esa máquina. Si sale 0 es que esa
  máquina no tiene ningún vuelo cerrado con tacómetro, y hay que resolverlo
  desde oficina.

**29. Cantidad de aceite negativa**
- Condición: `oilqty < 0`.
- Mensaje: «Es obligatorio indicar la cantidad de aceite añadida. 0 es un valor
  válido.»
- Anticipación: **imposible que ocurra**; el wizard fija 0.

**30. Potencial insuficiente**
- Condición: `helicoptero_id.horas_remanente <= tiempoprevisto`.
- Mensaje: «El tiempo de vuelo previsto (H:MM) excede el número de horas
  disponibles (H:MM) para esta máquina»
- Anticipación: **Consultable**. `horas_remanente` es un campo calculado leíble
  de `leulit.helicoptero`. Merece la pena traerlo con el catálogo y avisar en el
  formulario en cuanto `tiemposervicio` se acerque.

**31. Ruta sobre agua sin flotadores**
- Condición: `ruta_id.water_zone` y `flotadores` falso.
- Mensaje: «La ruta establecida tiene areas autorotativas sobre el agua, marca el
  check de Flotadores.»
- Anticipación: **imposible que ocurra**. El parte privado no fija `ruta_id`.

**32. Sin comentario de logbook**
- Condición: `vuelo_tipo_line` vacío.
- Mensaje: «No hay comentario logbook»
- Anticipación: **imposible que ocurra**; el wizard crea la línea con
  `vuelo_tipo_id`.

#### 8.3.8 `ComprobacionDatosCombustibleHandler` (cadena A)

Todo lo de este bloque lo calcula el servidor. El piloto no introduce
combustible, así que un fallo aquí es un problema de datos maestros o de
continuidad de partes, no un error de tecleo.

**33. Consumo medio a cero**
- Condición: `consumomedio_vuelo == 0`.
- Mensaje: «El valor del consumo medio esta a 0, revisa el parte de vuelo.»
- Anticipación: **Consultable**. Viene de `helicoptero.consumomedio`; si está
  vacío en ficha, esa máquina no puede usarse en la app. Comprobarlo al cargar
  el catálogo y excluirla o avisar.

**34. Combustible previsto de aterrizaje no válido**
- Condición: `combustiblelanding <= 0`.
- Mensaje: «Combustible previsto aterrizaje no válido»
- Anticipación: **Servidor**.

**35. Combustible de salida por debajo del mínimo**
- Condición: `fuelsalida < combustibleminimo`.
- Mensaje: «Cantidad combustible salida es inferior al combustible mínimo»
- Anticipación: **Servidor**. El wizard reposta automáticamente para evitarlo; si
  aun así salta, hay una incoherencia en los datos de continuidad de esa máquina.

**36. Combustible de despegue por encima del máximo del modelo**
- Condición: `fuelsalida` supera el límite del tipo — 170 l en CABRI G2, 110 l en
  R22, 180 l en R44, 410 l en EC120B.
- Mensaje: «Valor combustible al despegue excede el límite máximo»
- Anticipación: **Servidor**.

### 8.4 Firma 1 y cadena B — postvuelo → cerrado

Entre las dos cadenas, el servidor firma: el vuelo pasa a `postvuelo` y se
generan POV y PTV (y F27 si procede). **A partir de aquí, un fallo deja
documentos firmados de un parte que acabará cancelado.** Es inevitable con el
diseño actual y no lo puede evitar el cliente.

#### 8.4.1 `ComprobacionPresupuestoHandler`

**37. Sin presupuesto**
- Condición: `presupuesto_vuelo` vacío.
- Mensaje: «Este vuelo no puede pasar a cerrado. NO HA SELECCIONADO EL
  PRESUPUESTO»
- Anticipación: **Local**; el campo es obligatorio en el formulario.

#### 8.4.2 `ComprobacionChecksHandler`

**38. Debriefing / inspección postvuelo no marcados**
- Condición: `checklist_postvuelo_realizado` falso.
- Mensaje: «Este vuelo no puede pasar a cerrado. NO HA MARCADO EL DEBRIEFING CON
  LOS TRIPULANTES/ INSPECCIÓN POSTVUELO CÓMO REALIZADA»
- Anticipación: **imposible que ocurra**; el wizard lo fija a `true` desde
  `declaracion`.

#### 8.4.3 `ComprobacionUsuarioPilotoHandler`

**39.** Idéntico al nº 14, mismo mensaje. Se repite en esta cadena.

#### 8.4.4 `ComprobacionDescansoHandler`

**40. Descanso de piloto no respetado — acumulado superior a 3 horas**
- Condición: encadenando los vuelos cerrados del piloto ese día que van pegados
  unos a otros (menos de 3 minutos de separación), el tiempo total supera 3 h.
- Mensaje: «Se debe respetar el descanso de los Pilotos. Total tiempo de vuelo:
  <horas>»
- Anticipación: **Consultable**, pero el algoritmo es enrevesado. Lo razonable es
  no replicarlo y mostrar el mensaje del servidor, que ya trae el dato concreto.

**41. Descanso de piloto no respetado — descanso insuficiente entre bloques**
- Condición: entre el bloque de vuelos anterior y este no median al menos
  `tiempo_del_bloque_anterior × 20/60` horas.
- Mensaje: «Se debe respetar el descanso de los Pilotos. Hora llega vuelo
  anterior: <h>, Descanso requerido: <h>, Hora siguiente vuelo: <h>»
- Anticipación: **Servidor**. El mensaje trae los tres números; mostrarlo tal
  cual es suficiente para que el piloto entienda qué corregir.

#### 8.4.5 `ComprobacionHelicopteroHandler`

**42. Helicóptero en taller** — idéntico al nº 15, con el mensaje escrito sin
tilde: «Este helicoptero está en Taller».

**43. Anomalía sin firmar** — idéntico al nº 16, también sin tilde: «Este
helicoptero tiene una anomalía/discrepancia sin firmar y no puede ser
utilizado». En esta cadena **no** se comprueban las anotaciones del technical
log.

#### 8.4.6 `ComprobacionOverlapPartesEscuelaVueloHandler`

Este handler **no se ejecuta** en la cadena a cerrado: en este punto el vuelo
ya está en `postvuelo` y la búsqueda del handler (`fechavuelo` + estado
`postvuelo`/`cerrado`) no excluye su propio id, así que el vuelo se solaparía
consigo mismo y el cierre fallaría siempre. El flujo web (`initChainToCerrado`)
tampoco lo corre en este punto, así que omitirlo mantiene la paridad. Los casos
44 a 48 (los mismos cinco de 18–22) por tanto no existen en esta cadena, solo
en §8.3.6, al pasar a postvuelo.

#### 8.4.7 `ComprobacionDatosGeneralesHandler` (cerrado)

**49. Air Time negativo**
- Condición: `airtime < 0`.
- Mensaje: «Valor Air Time no válido»
- Anticipación: **imposible que ocurra**; la fórmula usa `max(..., 0.0)`.

**50. Air Time mayor que el tiempo de servicio**
- Condición: `airtime > tiemposervicio`.
- Mensaje: «Valor Air Time no puede ser mayor o igual que el tiempo de servicio»
- Anticipación: **imposible que ocurra**; el air time siempre es 6 minutos menor.

**51. Tiempo de servicio superior a 3 horas**
- Condición: `tiemposervicio > 3.0`.
- Mensaje: «El valor del tiempo previsto de vuelo no puede ser superior a 3
  horas»
- Anticipación: **Local**. Misma comprobación que la nº 25.

**52. Uso de gancho superior al tiempo de servicio**
- Condición: `uso_gancho > tiemposervicio`.
- Mensaje: «El tiempo de uso del gancho no puede ser superior al tiempo del
  servicio realizado.»
- Anticipación: **imposible que ocurra**; el parte privado deja `uso_gancho` a 0.

**53. Tacómetro de llegada no válido** *(solo helicópteros distintos de EC120B)*
- Condición: `tacomllegada <= 0`.
- Mensaje: «Valor tacómetro de llegada no válido»
- Anticipación: **Local**.

**54. Tacómetro de llegada no superior al de salida** *(solo distintos de EC120B)*
- Condición: `tacomllegada <= tacomsalida`.
- Mensaje: «Valor tacómetro de llegada debe ser superior al de salida»
- Anticipación: **Consultable, y la comprobación previa más rentable de todas.**
  `tacomsalida` es el `tacomllegada` del último vuelo cerrado de esa máquina.
  Consulta:

  ```json
  {"model":"leulit.vuelo","method":"search_read",
   "args":[[["helicoptero_id","=",<id>],["estado","=","cerrado"],
            ["fechasalida","!=",false]],
           ["tacomllegada","fuelllegada","fechasalida","codigo"]],
   "kwargs":{"limit":1,"order":"fechasalida desc"}}
  ```

  Mostrar ese valor como referencia junto al campo del formulario y rechazar en
  local cualquier lectura que no lo supere. Es el error de tecleo más habitual
  en R22, R44 y CABRI G2.

**55. NG no válido** *(solo EC120B)*
- Condición: `ngvuelo <= 0`.
- Mensaje: «Valor NG no válido»
- Anticipación: **Local**.

**56. NF no válido** *(solo EC120B)*
- Condición: `nfvuelo <= 0`.
- Mensaje: «Valor NF no válido»
- Anticipación: **Local**.

**57. Potencial insuficiente para el air time**
- Condición: `helicoptero_id.horas_remanente < airtime`.
- Mensaje: «El tiempo de vuelo previsto (H:MM) excede el número de horas
  disponibles (H:MM) para esta máquina»
- Anticipación: **Consultable**, igual que la nº 30.

#### 8.4.8 `ComprobacionDatosCombustibleHandler` (cerrado)

**58. Consumo medio a cero** — idéntico al nº 33.

**59. Combustible de llegada no válido**
- Condición: `fuelllegada <= 0`.
- Mensaje: «Cantidad combustible llegada no válida»
- Anticipación: **Servidor**. Lo calcula el propio parte como
  `salida − consumo medio × tiempo de servicio`; sale ≤ 0 si el vuelo consume más
  de lo que llevaba, lo que apunta a datos de continuidad incorrectos.

**60. Combustible de salida no superior al de llegada**
- Condición: `fuelsalida <= fuelllegada`.
- Mensaje: «Cantidad combustible salida es inferior al combustible mínimo»
  *(el mensaje no corresponde a la condición; es así en el código)*
- Anticipación: **Servidor**.

#### 8.4.9 `UpdateProximoVueloHandler`

No valida nada y no puede fallar. Propaga `tacomllegada` y `fuelllegada` de este
vuelo al siguiente vuelo en prevuelo de esa máquina, si lo hay.

### 8.5 Comprobación final antes de la firma de cierre

**61. Exceso de actividad aérea**
- Condición: `verificar_actividad_aerea(fechavuelo, partner_del_piloto)` devuelve
  falso.
- Mensaje: «No se puede firmar el parte de vuelo porque se ha excedido el tiempo
  máximo de actividad aérea. Debe crear una ocurrencia para gestionar el exceso
  de tiempo de actividad aérea.»
- Anticipación: **Servidor**. Es un límite normativo sobre el conjunto de la
  actividad del piloto ese día, no sobre este parte. Si salta, hay que abrir una
  ocurrencia desde el ERP; la app no lo resuelve.

### 8.6 Recuento

61 puntos de fallo. De ellos:

- **14 son anticipables en local**, y las 9 comprobaciones de §8.0 los cubren
  todos. El cliente debe implementarlas.
- **13 son consultables** con una llamada previa. Recomendados los nº 16
  (helicóptero bloqueado) y 54 (tacómetro), que cubren la mayoría de rechazos
  reales.
- **15 son imposibles por construcción** — el wizard fija esos campos. Se
  documentan para que nadie pierda tiempo buscando el campo que falta en el
  formulario.
- **9 dependen de cálculos del servidor**: mostrar el mensaje y punto.
- El resto son repeticiones del mismo validador en las dos cadenas.

---

## 9. Timeout, reconciliación y estado «Pendiente de finalizar»

`finalizar()` **no es idempotente**. Si el cliente reintenta a ciegas tras un
timeout, crea un segundo parte. Esta sección es obligatoria, no opcional.

### 9.1 Antes de enviar

Guardar en el almacén local un registro del intento, con:

- un identificador local (UUID)
- `fechavuelo`, `helicoptero_id`, `horasalida`, `tiemposervicio`
- marca de tiempo del envío
- estado local: `enviado`

Ese registro es lo que el listado pinta como **Pendiente de finalizar**.

### 9.2 Al recibir respuesta

- **Éxito** (`ir.actions.act_window_close`): el parte existe y está cerrado.
  Borrar el registro local y **refrescar el listado desde el servidor** para
  obtener el `codigo` real, que la respuesta no trae.
- **`UserError` / `ValidationError`**: el parte no se completó. Mostrar el
  mensaje, borrar el registro local, y devolver al piloto al formulario **con
  los datos que había metido**, para que corrija sin volver a teclearlo todo.
  Ojo: según en qué eslabón falló, puede haber quedado un vuelo `cancelado` en
  el servidor (§9.3); no es un error, es la traza del intento.
- **Timeout, corte de red, o cualquier error de transporte**: **no reintentar**.
  Dejar el registro local en `enviado` y pasar a §9.4.

### 9.3 Qué deja el servidor cuando falla

Si el fallo ocurre después del primer `cr.commit()` interno, no hay vuelta atrás
completa. El wizard hace `rollback()` al último commit y, si el vuelo sigue
existiendo y no llegó a `cerrado`, lo marca `estado = 'cancelado'` con el motivo
en `comentarios` (prefijo `Parte piloto privado fallido:`), para no dejar
bloqueados ni el helicóptero ni el piloto. Después relanza el error original,
que es el que recibe el cliente.

Consecuencia visible: **un intento fallido puede dejar una fila «Fallido» en el
listado**. Es correcto y hay que mostrarla, no filtrarla. Es la única evidencia
de lo que pasó.

### 9.4 Reconciliación

Al recuperar conectividad, o al abrir el listado si hay algún registro local en
`enviado`, resolverlo así:

```json
{"model":"leulit.vuelo","method":"search_read",
 "args":[[["piloto_id","=",<mi_piloto_id>],
          ["fechavuelo","=","<fechavuelo>"],
          ["horasalida","=",<horasalida>],
          ["helicoptero_id","=",<helicoptero_id>]],
         ["id","codigo","estado","control_firma","comentarios"]],
 "kwargs":{"limit":1}}
```

Esa tupla —piloto, fecha, hora de salida, helicóptero— es única en la práctica:
el propio servidor rechaza solapes de piloto y de máquina, así que no puede
haber dos partes que la compartan.

- **No aparece nada** → el parte no llegó a crearse. Borrar el registro local y
  ofrecer reenviar.
- **`estado = 'cerrado'` y `control_firma = 'firmado'`** → salió bien y se perdió
  solo la respuesta. Borrar el registro local. Es un éxito, comunicarlo como tal.
- **`estado = 'cancelado'`** → falló. Borrar el registro local y mostrar
  `comentarios` como motivo.
- **`estado` en `prevuelo` o `postvuelo`** → **Incompleto** (§4.1.1). Borrar el
  registro local, mostrar la fila en solo lectura y avisar de que hay que
  resolverlo desde oficina. No reenviar bajo ningún concepto.

### 9.5 Mejora futura, fuera de alcance

La solución correcta sería una clave de idempotencia en el servidor: un campo
con índice único que el cliente genera y envía, de modo que un reenvío del mismo
intento devuelva el parte ya creado en vez de duplicarlo. Exige tocar el wizard,
y el módulo es aditivo por diseño. Queda anotado, no planificado.

---

## 10. Documentos firmados

### 10.1 Qué se genera

Tras un `finalizar()` con éxito hay **cuatro** documentos, y un quinto en un
caso concreto. Todos son registros de `leulit_signaturedoc` con un
`ir.attachment` colgado:

- `<vuelo_id>-postvuelo-POV` — Parte de Operación de Vuelo, versión de la primera
  firma.
- `<vuelo_id>-postvuelo-PTV` — Parte Técnico de Vuelo, versión de la primera
  firma.
- `<vuelo_id>-cerrado-POV` — POV definitivo, tras la firma de cierre.
- `<vuelo_id>-cerrado-PTV` — PTV definitivo, tras la firma de cierre.
- `<vuelo_id>-F27-E4R9` — **solo** si el helicóptero es EC120B **y** el parte era
  el primer vuelo del día de esa máquina (`checklist_prevuelo_BFF`). Se genera
  una sola vez, en la primera firma.

**Los que interesan al piloto son los `cerrado`** y, si existe, el F27. Los
`postvuelo` son estados intermedios del proceso de firma; mostrarlos como
histórico o no mostrarlos, pero nunca presentarlos como el documento válido.

### 10.2 Cómo localizarlos

```json
{"model":"leulit_signaturedoc","method":"search_read",
 "args":[[["modelo","=","leulit.vuelo"],["idmodelo","=",<vuelo_id>]],
         ["id","name","referencia","estado","attachment_id","name_attach",
          "hashcode","fecha_create"]],
 "kwargs":{}}
```

- `referencia` es la clave para clasificarlos según §10.1.
- `estado` vale `completado` cuando el documento está generado y firmado.
- `attachment_id` es `[id, nombre]`; el `id` es lo que hace falta para descargar.
- `name_attach` es el nombre de fichero, con el formato `<codigo del vuelo>-<tipo>.pdf`.
- `hashcode` es el hash de la firma electrónica; mostrarlo si se quiere permitir
  verificación, no es necesario para la descarga.

`leulit_signaturedoc` es legible por `RBase`, así que el piloto lo lee sin
permisos adicionales.

### 10.3 Cómo descargarlos

```http
GET https://erp.helipistas.com/web/content/<attachment_id>?download=true
Cookie: session_id=...
```

Devuelve el PDF como stream. Los adjuntos se crean con `public = True`, pero
enviar la cookie de sesión igualmente es lo correcto y evita depender de esa
propiedad.

Alternativa desaconsejada: leer el campo `datas` de `leulit_signaturedoc` por
`call_kw`, que devuelve el PDF en base64 dentro del JSON. Funciona, pero mete un
PDF entero en la respuesta JSON-RPC. Usar `/web/content`.

### 10.4 Cuándo no hay documentos

Si el parte quedó **Fallido** o **Incompleto**, puede haber documentos
`postvuelo` sin los `cerrado`. No ofrecerlos como descarga: corresponden a un
parte que no llegó a cerrarse y no tienen validez. La pantalla de documentos
solo se ofrece desde un parte **Finalizado**.

---

## 11. Trampas conocidas

Leer antes de implementar. Todas están verificadas en el código.

### 11.1 Un helicóptero bloqueado produce un error incomprensible

`finalizar()` llama a `onchange_helicoptero()` para heredar pesos, velocidad,
consumo, tacómetro y combustible del último vuelo cerrado. Pero **ese método, si
la máquina tiene una anomalía sin firmar, devuelve un aviso y no escribe nada**.
El wizard ignora el valor devuelto y sigue adelante con un vuelo sin velocidad
ni consumo, que acaba fallando varios eslabones más tarde con:

> «Distancia total prevista no válida »

El piloto no tiene forma de deducir que el problema es una anomalía abierta en
la máquina, y el parte además le habrá quedado en estado «Fallido» con ese texto
como motivo.

**Por eso la comprobación previa de `isHelicopterBlocked` (nº 16) es obligatoria,
no una optimización.** Si el piloto no puede crear el parte, la aplicación tiene
que decirle por qué; y este es el único caso del flujo en el que el mensaje del
servidor no sirve para eso. La consulta cuesta una llamada y convierte un error
críptico en una instrucción accionable.

### 11.2 El wizard reescribe `lugarsalida` a propósito

`onchange_helicoptero()` pisa `lugarsalida` con el helipuerto de llegada del
vuelo anterior de esa máquina. El wizard lo vuelve a escribir con el valor del
formulario justo después. Es intencionado: el piloto privado puede haber salido
de un sitio distinto de donde quedó la máquina. No hay nada que hacer en el
cliente, pero explica por qué el helipuerto de salida no siempre coincide con la
llegada del parte anterior.

### 11.3 Un partner con más de un usuario

El wizard resuelve el usuario del piloto con
`piloto_id.partner_id.user_ids.filtered('active')[:1]`, es decir, **el primero**.
El validador posterior compara con `user_ids.id`, que en Odoo 17 lanza una
excepción de singleton si hay más de un usuario en el partner. Si un piloto
tiene dos `res.users` sobre el mismo `res.partner`, el flujo puede fallar de
forma opaca. Es un caso raro pero conviene descartarlo si aparece un error sin
mensaje de negocio.

### 11.4 La cadena de cierre del parte privado es más estricta que la del web

Esto explica por qué un parte puede ser rechazado por la app y, con los mismos
datos, aceptado por el flujo normal del Odoo web. **No es un fallo del cliente**,
y no hay que intentar «arreglarlo».

El flujo normal construye su cadena de cierre en
`leulit_operaciones/models/leulit_vuelo.py`, en `initChainToCerrado()`. Ahí hay
un error de tecleo que lleva años en el código:

```python
chain7 = vuelo_chain_cerrado.ComprobacionDatosCombustibleHandler()
chain7 = vuelo_chain_cerrado.ComprobacionParteEscuelaHandler()   # pisa el anterior
```

La misma variable se asigna dos veces. El validador de combustible se crea y se
descarta en la línea siguiente, antes de enlazarse a la cadena. Resultado: **en
el flujo web, al cerrar un parte no se valida el combustible.**

El parte privado no reutiliza esa función: arma su propia cadena en
`chains/vuelo_chain_privado.py`, enlazando los eslabones uno a uno. Y ahí el
validador de combustible sí queda enlazado. El validador de solapes
(`ComprobacionOverlapPartesEscuelaVueloHandler`) sigue sin enlazarse al cerrar,
igual que en el flujo web: en ese punto el vuelo ya está en `postvuelo` y la
búsqueda del handler no excluye su propio id, así que auto-solaparía siempre.
El solape ya se comprueba antes, al pasar a postvuelo.

Consecuencias prácticas para el cliente:

- Los errores nº 58, 59 y 60 (combustible al cerrar) **solo pueden aparecer por
  la app**. Un usuario de oficina que cierre el mismo parte por el web no los
  vería.
- Los errores nº 44 a 48 (solapes) solo aparecen al pasar a postvuelo, no al
  cerrar — ni en la app ni en el web.

El comportamiento del parte privado es el correcto: valida lo que el web se deja
sin validar. Simplemente hay que saberlo para no perseguir un fantasma cuando un
piloto diga «pues en la oficina me lo cerraron sin problema».

**No hay nada que arreglar aquí, y `initChainToCerrado()` no se toca.**
`leulit_parte_privado` es aditivo por requisito: no modifica ni una línea de
ningún otro módulo. Es precisamente por eso que arma su propia cadena en vez de
reutilizar la del flujo normal, y por eso el validador de combustible queda
enganchado sin necesidad de corregir nada aguas arriba. Si alguien lee esta
sección y siente la tentación de «arreglar» la cadena del web, esa es una
decisión de `leulit_operaciones`, ajena a este módulo y a esta app.

### 11.5 `finalizar()` no devuelve el parte creado

Devuelve `{'type': 'ir.actions.act_window_close'}`, que es lo que el Odoo web
necesita para cerrar el diálogo. Ni el id ni el código. Toda confirmación pasa
por consultar el listado (§9.2).

### 11.6 El mensaje 60 no corresponde a su condición

`fuelsalida <= fuelllegada` devuelve «Cantidad combustible salida es inferior al
combustible mínimo», que habla de otra cosa. Es así en el servidor. No intentar
interpretarlo ni reescribirlo en el cliente: mostrar el mensaje literal.

### 11.7 Las horas son locales

Ni `horasalida` ni `horallegada` llevan zona horaria: son horas locales tal cual.
No aplicar conversión UTC. El único campo con semántica de instante es
`fechasalida`, que es un `Datetime` calculado por el servidor y que el cliente
solo usa para ordenar.

---

## 12. Checklist de implementación

En orden. Cada punto es verificable por separado.

1. Autenticación por `/web/session/authenticate` con persistencia de la cookie
   `session_id` y renovación transparente ante `SessionExpiredException`.
2. Puerta de login de §2.2: resolver `mi_piloto_id` y rechazar a quien no sea
   piloto privado.
3. Carga de catálogos (§5) con sus dominios, incluyendo `tipo`, `statemachine`,
   `velocidad`, `consumomedio` y `horas_remanente` de cada helicóptero.
4. Listado (§4.1) con paginación, las cuatro etiquetas de estado y el filtro
   multiselección.
5. Ficha en solo lectura (§4.2).
6. Formulario de alta (§4.3, §6) con los contadores condicionados al tipo de
   helicóptero y el cálculo local de `horallegada` y `airtime`.
7. Las 9 comprobaciones locales de §8.0 antes de habilitar el botón Finalizar.
8. La consulta previa **obligatoria** de `isHelicopterBlocked` (§8.3.5), con su
   mensaje propio, y la recomendada del último `tacomllegada` de la máquina
   (§8.4.7).
9. Envío en dos llamadas (§7) con timeout de 120 s e indicador de progreso.
10. Almacén local del envío pendiente y reconciliación completa de §9.
11. Mapeo de errores de §3.3, mostrando `data.message` íntegro.
12. Pantalla de documentos (§10) con descarga por `/web/content`.

---

## 13. Referencias

- Módulo servidor: `addons/leulit_parte_privado/` — el `README.md` del módulo
  documenta el lado servidor y las decisiones de diseño.
- Diseño original: `docs/superpowers/specs/2026-09-01-parte-piloto-privado-design.md`
- Plan de implementación: `docs/superpowers/plans/2026-09-02-parte-piloto-privado.md`
- App del parte de vuelo normal (§11 para JSON-RPC):
  `docs/superpowers/specs/2026-08-18-app-parte-vuelo-spec.md`
- Validadores importados: `addons/leulit_operaciones/vuelo_chain_postvuelo.py`,
  `addons/leulit_operaciones/vuelo_chain_cerrado.py`
- Cadenas propias del módulo: `addons/leulit_parte_privado/chains/vuelo_chain_privado.py`
- Firma electrónica y generación de PDF: `addons/leulit_esignature/vuelo.py`

Si alguno de esos ficheros cambia, este documento —en particular el catálogo del
§8— deja de ser fiel. La fuente de verdad es el código.
