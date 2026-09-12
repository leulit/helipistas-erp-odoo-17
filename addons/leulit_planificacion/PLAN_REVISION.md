# Revisión de código — `leulit_planificacion`

Revisión estática (sin entorno Odoo disponible) de modelos, vistas, seguridad, wizards, cron jobs
y JS del addon. Alcance limitado a ficheros bajo `addons/leulit_planificacion/`.

## 1. Resumen ejecutivo

- **Críticos: 4** — bypass de control de acceso en `leulit.reunion_asistente.write()`, borrado de
  eventos restringido a un `uid` hardcodeado, rendimiento O(días×usuarios×eventos) en el wizard de
  control de planificación, y un `@api.depends` incompleto en un campo `store=True` que lo deja
  obsoleto silenciosamente.
- **Altos: 6** — `KeyError`/uso de dato obsoleto en `_check_event_permissions`, comparación
  `Selection` vs `int` que nunca es cierta, campo `alumno` que nunca se calcula y pisa `piloto`,
  cache ORM no invalidada tras `UPDATE` SQL directo, hilo en background sin `try/finally` (fuga de
  cursor), dependencia transitiva no declarada en el manifest.
- **Medios: ~10** — SQL con N consultas por recurso/participante, `_search_partner` en Python puro,
  `write_uid`/`create_uid` redefinidos dos veces, reglas de negocio comparando por `name`
  traducible, cron de Google Calendar sin dependencia declarada ni `ir.cron` que lo dispare,
  `sale_order_line.py` con una dependencia implícita no declarada.
- **Bajos: ~8** — logging con `_logger.error` para mensajes informativos, magic numbers/fechas,
  campo `tipo` marcado "Remove" aún presente, comprobación redundante dentro de un bucle, nombres
  de variable confusos.

Ver tabla completa abajo; los hallazgos crítico/alto se desarrollan con snippet + fix en la
sección 3.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_reunion_asistente.py:17-23` | `write()` comprueba permiso por `item` pero llama a `super().write()` sobre `self` (todo el recordset), no sobre `item` | Un usuario incluye su propia línea de asistente junto con la de otro asistente en la misma llamada `write()` (p.ej. desde un guardado de formulario con varias líneas seleccionadas, o vía RPC); su propia línea pasa el check y el `super(...).write(values)` se ejecuta sobre `self` completo, escribiendo también sobre la línea ajena antes de que el bucle llegue a esa línea y lance el `UserError` | `super(leulit_reunion_asistente, item).write(values)` dentro del bucle, o filtrar antes y hacer un solo `write` sobre el subconjunto autorizado |
| Crítico | `models/leulit_calendar_event.py:74-78` | `unlink()` sólo permite borrar a `self.env.uid == 14` (id de usuario hardcodeado) | Cualquier borrado de `calendar.event` — incluido por un administrador, por `ondelete` en cascada desde otro módulo, o por un cron de limpieza — falla con `UserError` salvo que lo ejecute exactamente el usuario con id=14 en esa base de datos | Sustituir por comprobación de grupo (`self.env.user.has_group('leulit_planificacion.RPlanificacion_manager')`, o el grupo que corresponda) en vez de un id numérico; mover el `if` fuera del bucle |
| Crítico | `models/leulit_print_ctrl_calendar_wizard.py:23-76` | Dentro del bucle por día se relanza `self.env['calendar.event'].search([], order='start asc')` **sin filtro de fecha**, es decir, una búsqueda de la tabla completa de eventos por cada día del rango, y se filtra en Python; a su vez anidado en bucle por usuario y por recurso | Generar el informe de control de planificación para un rango de, p.ej., 30 días en una base con años de histórico de eventos: hace 30 full scans de `calendar.event` (y las mismas 30× para `res.users` sin dominio, incluyendo portal/OdooBot) más bucles anidados users×events×resources | Filtrar `calendar.event` por `start`/`stop` dentro del rango una sola vez fuera del bucle de días, agrupar por fecha en Python o con `read_group`, y añadir dominio a `res.users` (al menos `active=True`, excluir usuarios sin recurso asociado) |
| Crítico | `models/leulit_event_resource_by_day.py:23-33` | `@api.depends('event_resource_lines', 'event_resource_lines.write_date', 'write_date')` en un campo `store=True`, pero el compute en realidad lee `event.tipo`, `event.cancelado`, `event.duration` vía una búsqueda SQL independiente (`domain` sobre `resource`+`fecha`), campos que no están en la lista de `depends` | Cambiar `duration`, `cancelado` o `tipo` de un `calendar.event` sin tocar la relación `byday_id` de sus `leulit.event_resource`: `total_horas_planificadas` (stored) queda desactualizado y nadie lo recalcula hasta que se ejecute manualmente `upd_compute_fields()`/`set_in_byday_event_resource()` (la propia existencia de esos métodos "forzar recompute total" es indicio de que el equipo ya detectó el problema) | Añadir los campos reales de los que depende (`event_resource_lines.event.duration`, `.cancelado`, `.tipo`, `event_resource_lines.date`) a `@api.depends`, o mejor, sustituir el `search()` interno por lectura directa de `event_resource_lines` filtrado en Python para que el grafo de dependencias de Odoo sea exacto |
| Alto | `models/leulit_calendar_event.py:98-104` | `if 'start' in vals: event_end = fields.Datetime.from_string(vals['stop'])` asume que si `start` está en `vals`, `stop` también lo está; y si sólo `stop` cambia (sin `start`), usa `self.stop` **antiguo**, no el nuevo valor | (a) Un `write({'start': ...})` sin `stop` desde código externo/otro módulo → `KeyError: 'stop'`. (b) Redimensionar sólo el extremo final de un evento (`write({'stop': ...})` sin `start`) → la comprobación de "temporada alta" evalúa con la fecha de fin **vieja**, pudiendo permitir o bloquear incorrectamente el cambio | Leer ambos valores con `vals.get('start', self.start)` / `vals.get('stop', self.stop)` (con conversión de string a datetime cuando vengan en vals) |
| Alto | `models/leulit_resource.py:60-68` | `_get_alumno` (compute de `alumno`, `@api.depends('partner')`) hace `item.piloto = valor` en vez de `item.alumno = valor` | Se lee/lista el campo `alumno` de cualquier `leulit.resource` con `partner` asignado: `alumno` nunca se rellena (queda vacío), y además pisa el valor ya calculado de `piloto` por `_get_piloto` con el resultado de la búsqueda en `leulit.alumno`, corrompiendo el campo `piloto` | `item.alumno = valor` |
| Alto | `models/leulit_event_resource_by_day.py:36-40` (`_compute_total_horas_planificadas`, línea 30) | `item1.event.tipo != 17`: `tipo` es un `Selection` (valores string) definido en `leulit_calendar_event.py:449`; comparar un string con el entero `17` nunca es `False` en Python | El filtro "excluir eventos de tipo 17" nunca excluye nada — todos los eventos entran siempre en el sumatorio de `total_horas_planificadas`, sea cual sea su `tipo` | Comparar contra la clave string correcta (`item1.event.tipo != '17'`) tras confirmar con el usuario cuál es el tipo que se pretendía excluir; nota: el propio campo `tipo` está marcado `'Tipo Remove'` en `leulit_calendar_event.py:449`, ver sección de dudas |
| Alto | `models/leulit_calendar_event.py:299-329` (`_update_resource_availability`) | `UPDATE leulit_event_resource ... via self._cr.execute(...)` sin invalidar la caché de campos de la ORM (`invalidate_recordset`/`invalidate_cache`) | Tras crear/escribir un `calendar.event` con `resource_fields`, si en la misma transacción se vuelve a leer `resource_fields.availability_hours`/`date`/`hora_ini`/etc. de esos `leulit.event_resource` (p.ej. desde otro método encadenado, un related field, o el propio `create()`/`write()` que continúa tras el `@api.constrains`), la ORM puede devolver los valores cacheados **previos** al `UPDATE` SQL, no los recién escritos | Tras el `cr.execute`, llamar a `self.env['leulit.event_resource'].browse(...).invalidate_recordset(['availability_hours','date','date_deadline','fecha_ini','fecha_fin','hora_ini','hora_fin'])` (Odoo 17) para los registros afectados, o hacer el `UPDATE` vía ORM (`write()`) si el volumen lo permite |
| Alto | `models/leulit_event_resource_by_day.py:67-86` (`run_set_in_byday_event_resource`) | Hilo en background con cursor propio (`self.pool.cursor()`), sin `try/finally`; si cualquier iteración lanza excepción, el cursor no se cierra ni se hace rollback, y la excepción se pierde silenciosamente (no hay `try/except` alrededor del `for`) | Un fallo de integridad (p.ej. un `leulit.event_resource` sin `resource` válido, o error de red/BD) a mitad del bucle dentro del hilo deja una conexión abierta sin liberar y el resto del proceso no se ejecuta, sin ningún rastro en logs salvo el traceback por stderr del hilo | Envolver el cuerpo en `try/except/finally`, hacer `_logger.exception(...)` en el except, y `finally: new_cr.close()`; ver patrón de referencia ya usado en `addons/leulit/models/res_partner.py` (`_recalcular_complete_name_thread`) citado en `CLAUDE.md` |
| Alto | `security.xml:202-210` | `ir.model.access` referencia `leulit_parte_145.model_leulit_helicoptero`, y `models/leulit_helicoptero.py` hace `_inherit = "leulit.helicoptero"`, pero `leulit_parte_145` **no** está en `depends` del manifest — sólo llega de forma transitiva vía `leulit_taller → leulit_operaciones → leulit_parte_145` | Si en el futuro `leulit_taller` o `leulit_operaciones` dejan de depender de `leulit_parte_145` (o se reordena/refactoriza esa cadena), la carga de `security.xml` fallará con "External ID not found" y el `_inherit` del modelo fallará al construir el registro | Añadir `leulit_parte_145` explícitamente a `depends` en `__manifest__.py` (es inocuo, ya está instalado siempre que este módulo lo esté) |
| Medio | `models/leulit_calendar_event.py:230-284` (`_check_overlaps`) | Una consulta SQL por cada id de recurso/participante dentro de un bucle Python, ejecutada en cada `create`/`write` vía `@api.constrains` | Evento con 5 recursos y 8 participantes → 13 `SELECT` separados en cada guardado; en calendarios muy activos esto se ejecuta constantemente | Sustituir el bucle por una única consulta con `le.{column} = ANY(%s)` y agrupar resultados en Python; añadir `LIMIT 1` ya que sólo se usa la primera fila |
| Medio | `models/leulit_resource.py:79-94` (`_search_partner`) | Carga **todos** los `leulit.resource` (`self.search([])`) y filtra en Python en vez de traducir a dominio SQL | Cualquier búsqueda/filtro por `partner` sobre recursos (p.ej. un dominio de vista) con muchos recursos activos | Traducir a `[('user.partner_id', operator, value)]` si el ORM lo permite vía related search, o construir el dominio directamente sobre `user_id` sin cargar todos los registros |
| Medio | `models/leulit_resource.py:18-35` (`_get_work_time`, `_get_availability_time`) | Patrón N+1: por cada `leulit.resource` se hace un `search()` completo de `leulit.event_resource` y se suma en Python | Vista de lista/kanban de recursos con muchos registros → una query por fila en vez de un `read_group` agregando `work_hours`/`availability_hours` por `resource` | Sustituir por `self.env['leulit.event_resource'].read_group([('resource','in',self.ids)], ['work_hours:sum','availability_hours:sum'], ['resource'])` y mapear resultados |
| Medio | `models/leulit_calendar_event.py:447-448` vs `464-465` | `create_uid`/`write_uid` se declaran dos veces: primero como `fields.Integer` (líneas 447-448), después como `fields.Many2one('res.users', ...)` (líneas 464-465); la segunda definición gana en Python, dejando la primera como código muerto y confuso | Ninguno en runtime (la definición Integer nunca se usa), pero cualquier desarrollador que lea/edite el fichero puede tocar la definición equivocada, o una herramienta de análisis estático puede marcar el conflicto | Eliminar las líneas 447-448 (las `Integer`); en general evitar redefinir `create_uid`/`write_uid`, que ya son campos mágicos de la ORM con el tipo correcto |
| Medio | `models/leulit_calendar_event.py:112` (`_check_event_permissions`) | El bloqueo de "temporada alta" compara `type_event.name == 'No disponible (vacaciones, ausencias, etc..)'`, un texto traducible/editable en `leulit.tipo_planificacion` | Si alguien renombra ese tipo de planificación (typo, traducción, ajuste de texto) desde la UI, la restricción de permisos deja de aplicarse **silenciosamente**, sin error ni aviso | Añadir un campo booleano técnico (p.ej. `es_no_disponible`) en `leulit.tipo_planificacion` y comparar por ese campo en vez del `name`; mismo patrón aplica a las comparaciones por `name`/`tipo_actividad` de los cron jobs en `leulit_calendar_event_automatizaciones.py` (menos frágil ahí porque usan `tipo_actividad`, un `Selection`, salvo `potencial_aeronaves` que compara `('name','in',['Taller'])`, línea 107) |
| Medio | `models/res_users.py:1-61` | Todo el fichero (`_sync_google_calendar_leulit`, `_sync_all_google_calendar_leulit`) usa modelos/campos de `google_calendar`/`google_account`, módulos que **no** están en `depends` ni existen como submódulo de este repo (no vendorizados en `third-party-addons`); además no hay ningún `ir.cron` en este módulo que dispare `_sync_all_google_calendar_leulit` | Si `google_calendar` no está instalado en el entorno de destino, invocar el método manualmente (shell, RPC) lanzará `AttributeError`/`KeyError` sobre campos inexistentes en `res.users`/`calendar.event`; hoy es código muerto porque nada lo llama | Ver sección "Dudas" — confirmar con el usuario si la sincronización con Google Calendar es una función activa/planeada; si lo es, declarar `google_calendar` en `depends` y añadir el `ir.cron`; si no, eliminar el fichero |
| Medio | `models/sale_order_line.py` (todo el fichero) | `_timesheet_create_task_prepare_values` sobrescribe un método que pertenece a `sale_timesheet` (módulo Community estándar de facturación por partes de horas), no declarado en `depends`; el fichero conserva la cabecera de copyright original de un módulo OCA/Tecnativa de 2019 sin relación aparente con planificación de vuelos | Si `sale_timesheet` no está instalado, el método es código muerto; si lo está (vía dependencia transitiva de otro addon no declarada), este override cambia comportamiento global de creación de tareas desde líneas de venta sin que quede documentado en este módulo | Ver sección "Dudas" — confirmar si este fichero pertenece realmente a `leulit_planificacion` o es un resto de copiar/pegar de otro módulo |
| Medio | `models/leulit_reunion_asistente.py:25-30` (`_get_user`) | Compute `store=True` de `user_id` sólo asigna el campo dentro de `if item.partner_id:`; si `partner_id` está vacío no se asigna explícitamente `False` | Borrar el `partner_id` de un asistente ya existente: el comportamiento de `user_id` ante una rama sin asignación explícita depende de la versión de Odoo (riesgo de quedarse con el valor cacheado/anterior en vez de limpiarse) | Añadir `else: item.user_id = False` |
| Bajo | `models/leulit_event_resource_by_day.py:51,56,61,63,86` | Uso de `_logger.error(...)` para trazas puramente informativas ("start thread", "end thread") | Cada ejecución del recálculo masivo genera entradas de nivel ERROR en logs/alertas sin que haya ningún error real | Cambiar a `_logger.info(...)` |
| Bajo | `models/leulit_event_resource_by_day.py:72` | Fecha mágica `"2023-01-01"` hardcodeada como límite inferior del recálculo masivo | Ninguno funcional hoy, pero dificulta entender/mantener por qué ese corte | Extraer a constante nombrada con comentario explicando el origen de la fecha |
| Bajo | `models/leulit_calendar_event.py:75-77` | `for item in self: if self.env.uid != 14: raise ...` repite la misma comprobación (no depende de `item`) tantas veces como registros en `self` | Ninguno funcional, sólo ineficiencia cosmética | Sacar el `if` fuera del bucle |
| Bajo | `models/leulit_print_calendar_wizard.py:22-23` | Botón `imprimir()` siempre lanza `UserError('Funcionalidad no migrada boton')` | Cualquier usuario que pulse "Imprimir" en este wizard ve un error genérico de funcionalidad no migrada | Si no se va a implementar, quitar el botón de la vista (`views/leulit_print_calendar_wizard.xml`) para no exponer una función rota; si se va a implementar, priorizarlo en el plan |
| Bajo | `models/leulit_calendar_event.py:449` | Campo `tipo = fields.Selection(..., string='Tipo Remove', ...)` sigue presente y con `string` indicando que debería eliminarse | Ninguno funcional directo, pero es la base del bug de comparación `!= 17` en `leulit_event_resource_by_day.py:30` — mientras el campo exista mal etiquetado, seguirán apareciendo estos deslices | Confirmar con el usuario si `tipo` puede eliminarse ya (y su uso real en `event_resource_by_day.py`), ver sección "Dudas" |
| Bajo | `models/leulit_calendar_recurrence.py:24-28` | Variable `start_mapping` usada para almacenar valores de **`stop`** (nombre engañoso) | Ninguno funcional | Renombrar a `stop_mapping` |
| Bajo | `groups.xml` / `security.xml:106-114` | El grupo `RPlanificacion_own` ("Mi planificación") concede `perm_read=1` sin `ir.rule` que limite a "mis eventos" — el filtrado real de "propios" es sólo una convención de nombre, la lectura es global | Ninguno funcional en la práctica (el propio módulo `calendar` de Odoo ya da lectura amplia de `calendar.event` a usuarios internos), pero el nombre del grupo puede inducir a error sobre el alcance real de los permisos | Documentar en el propio grupo (`res.groups.comment`) que "own" sólo restringe escritura vía Python, no lectura |

## 3. Hallazgos críticos/altos — detalle

### 3.1 [CRÍTICO] Bypass de control de acceso en `leulit.reunion_asistente.write()`

`models/leulit_reunion_asistente.py:17-23`

```python
def write(self, values):
    for item in self:
        if item.user_id and self.env.uid == item.user_id.id:
            super(leulit_reunion_asistente,self).write(values)
        else:
            raise UserError('El usuario no esta autorizado a realizar esta modificación')
    return True
```

El bucle comprueba el permiso registro a registro (`item`), pero la llamada real a `write()` se
hace sobre `self` — el recordset completo con el que se invocó el método — no sobre `item`. Si
`self` contiene la línea del usuario actual junto con la de otro asistente, en la primera
iteración (la propia) ya se escribe sobre **todo** `self`, incluida la línea ajena; sólo al llegar
a esa línea ajena se lanza el `UserError`, cuando el dato ya se ha modificado.

**Fix propuesto:**

```python
def write(self, values):
    for item in self:
        if item.user_id and self.env.uid == item.user_id.id:
            super(leulit_reunion_asistente, item).write(values)
        else:
            raise UserError('El usuario no esta autorizado a realizar esta modificación')
    return True
```

### 3.2 [CRÍTICO] Borrado de eventos restringido a un `uid` hardcodeado

`models/leulit_calendar_event.py:74-78`

```python
def unlink(self):
    for item in self:
        if self.env.uid != 14:
            raise UserError('Intento de eliminar evento no autorizado.')
    return super().unlink()
```

Esto ata la autorización de borrado a un id numérico de usuario concreto de una base de datos
concreta, en vez de a un rol/grupo. Rompe para cualquier otro administrador, para llamadas
`sudo()` de otros módulos que necesiten borrar eventos en cascada, y es completamente opaco (no
hay forma de saber, leyendo el código, quién es el usuario 14 sin consultar la BD).

**Fix propuesto (a validar con el usuario qué grupo debe autorizar el borrado):**

```python
def unlink(self):
    if not self.env.user.has_group('leulit_planificacion.RPlanificacion_manager'):
        raise UserError('Intento de eliminar evento no autorizado.')
    return super().unlink()
```

### 3.3 [CRÍTICO] Rendimiento cuadrático/cúbico en el informe de control de planificación

`models/leulit_print_ctrl_calendar_wizard.py:23-76`

```python
def _get_data_to_print_control_planificacion(self):
    ...
    users = self.env['res.users'].search([], order='id asc')
    for i in range(resta_fecha.days+1):
        day = self.from_date + timedelta(days=i)
        eventos = self.env['calendar.event'].search([], order='start asc')   # <-- TODOS los eventos, cada día
        eventos_fecha = []
        for evento in eventos:
            if day == evento.start.date():                                   # filtro en Python
                eventos_fecha.append(evento)
        ...
        for user in users:                                                   # TODOS los usuarios
            for evento in eventos_fecha:
                for resource_field in evento.resource_fields:                # por cada recurso
                    if resource_field.resource.user.id == user.id:
                        ...
```

Con `N` = nº de eventos totales en la base y `D` = días del rango solicitado, esto ejecuta `D`
`search()` completos de `calendar.event` (sin dominio de fecha) y recorre `usuarios × eventos_del_día
× recursos_del_evento` en Python puro. En una base con años de eventos acumulados este wizard puede
tardar minutos o agotar memoria/CPU del worker.

**Fix propuesto (esquema):**

```python
def _get_data_to_print_control_planificacion(self):
    data = {}
    dias = []
    users = self.env['res.users'].search([('share', '=', False)], order='id asc')
    date_start = fields.Datetime.to_datetime(self.from_date)
    date_end = fields.Datetime.to_datetime(self.to_date) + timedelta(days=1)
    eventos = self.env['calendar.event'].search([
        ('start', '>=', date_start), ('start', '<', date_end),
    ], order='start asc')
    eventos_por_dia = defaultdict(lambda: [])
    for evento in eventos:
        eventos_por_dia[evento.start.date()].append(evento)

    horas_por_dia = self.env['account.analytic.line'].read_group(
        [('date', '>=', self.from_date), ('date', '<=', self.to_date)],
        ['unit_amount:sum'], ['date', 'employee_id'], lazy=False,
    )
    ...
```

(la reestructuración exacta de `horas_realizadas`/agregación por usuario y día debería
consensuarse, ya que cambia la forma de recorrer los datos — no es un cambio mecánico de una
línea).

### 3.4 [CRÍTICO] `@api.depends` incompleto en campo `store=True`

`models/leulit_event_resource_by_day.py:23-33`

```python
@api.depends('event_resource_lines','event_resource_lines.write_date','write_date')
def _compute_total_horas_planificadas(self):
    for item in self:
        dominio = [('resource', '=', item.resource.id), ('date', '=', item.fecha)]
        total = 0
        ids = []
        for item1 in self.env['leulit.event_resource'].search(dominio):
            if item1.event.tipo != 17 and item1.event.cancelado == False and item1.event.id not in ids:
                total +=  item1.event.duration
                ids.append(item1.event.id)
        item.total_horas_planificadas = total
```

El compute lee `event.tipo`, `event.cancelado`, `event.duration` de los `leulit.event_resource`
relacionados por `resource`+`fecha` (vía `search()`, no vía el O2M `event_resource_lines`), pero el
`@api.depends` sólo cubre `event_resource_lines` y su `write_date`. Cambios en `duration`,
`cancelado` o `tipo` de un `calendar.event` no disparan el recompute de este campo `store=True` a
menos que también cambie la relación `byday_id`. Los métodos `upd_compute_fields()` y
`run_set_in_byday_event_resource()` en el mismo fichero, que fuerzan un recompute total tocando
`self.env.all.tocompute` directamente, son un indicio fuerte de que el equipo ya lidia con este
síntoma de forma manual.

**Fix propuesto (mínimo):**

```python
@api.depends(
    'event_resource_lines', 'event_resource_lines.date',
    'event_resource_lines.event.duration', 'event_resource_lines.event.cancelado',
    'event_resource_lines.event.tipo',
)
def _compute_total_horas_planificadas(self):
    ...
```

Nota: esto sigue sin cubrir el hecho de que el compute usa `search()` con dominio
`resource`+`fecha` en vez del propio `event_resource_lines` — dos `leulit.event_resource` con el
mismo `resource`/`date` pero no enlazados a este `byday_id` concreto también entrarían en el
sumatorio. Si esa es la intención de negocio real, al menos el `@api.depends` corregido evita la
mayoría de los casos de dato obsoleto; si no lo es, el método debería reescribirse para iterar
`item.event_resource_lines` directamente. **Preguntar al usuario** cuál de las dos semánticas es la
correcta (ver sección 5).

### 3.5 [ALTO] `KeyError`/uso de dato obsoleto en `_check_event_permissions`

`models/leulit_calendar_event.py:98-104`

```python
if 'start' in vals:
    event_start = fields.Datetime.from_string(vals['start'])
    event_end = fields.Datetime.from_string(vals['stop'])
else:
    event_start = self.start
    event_end = self.stop
```

**Fix propuesto:**

```python
if 'start' in vals or 'stop' in vals:
    event_start = fields.Datetime.from_string(vals['start']) if 'start' in vals else self.start
    event_end = fields.Datetime.from_string(vals['stop']) if 'stop' in vals else self.stop
else:
    event_start = self.start
    event_end = self.stop
```

### 3.6 [ALTO] Campo `alumno` nunca se calcula y pisa `piloto`

`models/leulit_resource.py:60-68`

```python
@api.depends('partner')
def _get_piloto(self):
    for item in self:
        valor = None
        if item.partner:
            piloto = self.env['leulit.piloto'].search([('partner_id','=',item.partner.id)])
            if piloto and piloto.id:
                valor = piloto.id
        item.piloto = valor

@api.depends('partner')
def _get_alumno(self):
    for item in self:
        valor = None
        if item.partner:
            alumno = self.env['leulit.alumno'].search([('partner_id','=',item.partner.id)])
            if alumno and alumno.id:
                valor = alumno.id
        item.piloto = valor          # <-- debería ser item.alumno
```

**Fix propuesto:** cambiar la última línea a `item.alumno = valor`.

### 3.7 [ALTO] Comparación `Selection` vs `int` que nunca es cierta

`models/leulit_event_resource_by_day.py:30`

```python
if item1.event.tipo != 17 and item1.event.cancelado == False and item1.event.id not in ids:
```

`calendar.event.tipo` es un `fields.Selection` (`models/leulit_calendar_event.py:449`); sus
valores son claves string devueltas por `utilitylib.leulit_get_tipos_planificacion()` (definida en
el módulo `leulit`, fuera de alcance). Un string nunca es `== 17` (`int`), así que
`item1.event.tipo != 17` es **siempre `True`**: el filtro pensado para excluir un tipo concreto no
excluye nada. Además el propio campo está marcado `string='Tipo Remove'`, sugiriendo que iba a
eliminarse — no toco el modelo `leulit` ni cierro esto sin más contexto; ver sección "Dudas".

## 4. Plan de acción (orden de ejecución sugerido)

1. **[Crítico]** `models/leulit_reunion_asistente.py` — corregir `write()` para operar sobre
   `item`, no sobre `self`. Cambio de una línea, alto impacto de seguridad.
2. **[Crítico]** `models/leulit_calendar_event.py` (`unlink`) — sustituir el `uid == 14` por
   comprobación de grupo. Requiere decidir con el usuario qué grupo debe poder borrar eventos.
3. **[Crítico]** `models/leulit_event_resource_by_day.py` — corregir `@api.depends` de
   `_compute_total_horas_planificadas` y decidir la semántica correcta del filtro por
   `resource`+`fecha` vs `event_resource_lines`. Requiere confirmación de negocio (sección 5).
4. **[Alto]** `models/leulit_event_resource_by_day.py:30` — corregir la comparación
   `tipo != 17` una vez aclarado con el usuario qué tipo se pretendía excluir y si el campo `tipo`
   sigue vivo.
5. **[Alto]** `models/leulit_resource.py` — corregir `_get_alumno` (`item.alumno = valor`).
6. **[Alto]** `models/leulit_calendar_event.py:98-104` — corregir lectura de `start`/`stop` desde
   `vals` con `.get()` para evitar `KeyError` y datos obsoletos.
7. **[Crítico/Alto]** `models/leulit_print_ctrl_calendar_wizard.py` — reescribir
   `_get_data_to_print_control_planificacion` para filtrar por fecha en el dominio SQL en vez de en
   Python dentro del bucle de días. Cambio más grande, priorizar si el wizard se usa con rangos
   amplios o bases grandes.
8. **[Alto]** `models/leulit_calendar_event.py` (`_update_resource_availability`) — invalidar caché
   ORM tras el `UPDATE` SQL directo.
9. **[Alto]** `models/leulit_event_resource_by_day.py` (`run_set_in_byday_event_resource`) —
   envolver en `try/except/finally` para no perder excepciones ni fugar el cursor del hilo.
10. **[Alto]** `__manifest__.py` — añadir `leulit_parte_145` a `depends` (hoy sólo llega
    transitivamente).
11. **[Medio]** `models/leulit_calendar_event.py` (`_check_overlaps`) — una sola query con
    `= ANY(%s)` en vez de N queries por recurso/participante.
12. **[Medio]** `models/leulit_resource.py` (`_get_work_time`, `_get_availability_time`,
    `_search_partner`) — sustituir patrones N+1 por `read_group`/dominio directo.
13. **[Medio]** `models/leulit_calendar_event.py:447-448` — eliminar la redefinición muerta
    `create_uid`/`write_uid` como `Integer`.
14. **[Medio]** `models/leulit_calendar_event.py:112` — sustituir comparación por `name` en la
    regla de "temporada alta" por un campo técnico booleano en `leulit.tipo_planificacion`.
15. **[Medio/Duda]** `models/res_users.py` y `models/sale_order_line.py` — decidir si son código
    vivo (añadir dependencias al manifest) o restos a eliminar; ver sección 5.
16. **[Bajo]** Limpieza: `_logger.error` → `_logger.info` en `leulit_event_resource_by_day.py`;
    extraer fecha mágica `"2023-01-01"`; sacar el `if self.env.uid != 14` fuera del bucle antes de
    corregirlo (paso 2); quitar o implementar el botón `imprimir()` de
    `leulit_print_calendar_wizard.py`; renombrar `start_mapping` en `leulit_calendar_recurrence.py`.

## 5. Dudas / no verificable sin entorno

Estas cuestiones no se pueden cerrar sólo leyendo el código; necesitan una decisión de negocio o
acceso a un entorno con datos reales:

1. **`leulit_event_resource_by_day.py:30` — ¿qué tipo se pretendía excluir con `tipo != 17`?**
   El campo `tipo` de `calendar.event` está marcado como `'Tipo Remove'` (candidato a
   eliminación) en `leulit_calendar_event.py:449`, y sus valores vienen de
   `utilitylib.leulit_get_tipos_planificacion()` en el módulo `leulit` (fuera de alcance de esta
   revisión). No puedo determinar sin ver esa función qué valor de `tipo` corresponde a "17", ni si
   el campo `tipo` sigue en uso real o es vestigial. Antes de tocar esta línea necesito saber: (a)
   si `tipo` sigue vivo o se puede eliminar junto con este filtro, y (b) si se elimina, qué debe
   pasar a filtrar `total_horas_planificadas` en su lugar (¿ningún filtro por tipo? ¿usar
   `type_event` en su lugar?).

2. **`models/res_users.py` — sincronización con Google Calendar: ¿viva, planeada, o abandonada?**
   El fichero completo depende de `google_calendar`/`google_account` (no declarados en el
   manifest, no vendorizados en este repo) y define un método documentado como "Cron job" pero no
   hay ningún `ir.cron` en el módulo que lo dispare. No puedo saber sin preguntar si esto es una
   funcionalidad a medio terminar que se retomará, o código muerto que debería eliminarse junto con
   los campos `google_event_id`/`google_sequence` de `leulit_calendar_event.py:469-470`.

3. **`models/sale_order_line.py` — ¿pertenece a este módulo?**
   Sobrescribe `_timesheet_create_task_prepare_values`, método propio de `sale_timesheet` (no
   declarado en el manifest, no vendorizado en el repo), con cabecera de copyright de un módulo
   OCA/Tecnativa de 2019 sin relación aparente con planificación de vuelos de un operador de
   helicópteros. No puedo determinar si es un resto de copiar/pegar de otro proyecto o si hay una
   razón de negocio real para que viva aquí. Recomendación: confirmar con el usuario antes de
   tocarlo (eliminarlo, o mover la dependencia real a donde corresponda).

4. **`leulit.reunion_asistente._get_user` (línea 25-30) — comportamiento exacto de Odoo 17 ante
   compute `store=True` que no asigna el campo en todas las ramas.**
   No tengo forma de confirmar sin ejecutar Odoo 17 si al dejar `partner_id` vacío el campo
   `user_id` se resetea a `False`, mantiene el valor cacheado anterior, o lanza una advertencia
   interna — el comportamiento exacto de la ORM ante un compute que no cubre todas las ramas
   depende de detalles internos que no quiero asumir. Recomiendo el fix defensivo (`else:
   item.user_id = False`) independientemente de cuál sea el comportamiento real, ya que es
   inocuo y clarifica la intención.

5. **`security.xml:106-114` (`RPlanificacion_own`) — ¿la lectura global de `calendar.event` para
   este grupo es intencional?**
   El nombre "Mi planificación" sugiere alcance restringido a los propios eventos, pero el
   `ir.model.access` no va acompañado de ningún `ir.rule` que limite el dominio de lectura — el
   filtrado a "eventos propios" sólo ocurre en las vistas/menús, no a nivel de modelo. Dado que el
   módulo core `calendar` de Odoo ya concede lectura amplia de `calendar.event` a usuarios
   internos por defecto, este hallazgo puede no tener impacto práctico adicional, pero confirmar
   con el usuario si alguna vez se esperó que "own" también restringiera lectura vía `ir.rule`.

6. **`leulit.event_resource._check_work_hours` (`work_hours > 0` obligatorio si `resource.aeronave`)
   — ¿debe aplicar también a recursos de eventos cancelados?**
   La constraint no excluye `cancelado=True`; no sé si es intencional (siempre exigir horas
   previstas) o si eventos cancelados deberían quedar exentos. No lo marco como bug sin confirmar
   la regla de negocio.
