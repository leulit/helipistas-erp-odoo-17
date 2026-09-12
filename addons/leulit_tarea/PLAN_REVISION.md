# Revisión de código — `leulit_tarea`

Revisión estática (sin entorno Odoo disponible) de modelos, vistas, seguridad y wizard del
addon `addons/leulit_tarea/`. Dependencias declaradas en `__manifest__.py`: `leulit`,
`project_status`, `project_timesheet_time_control`.

## 1. Resumen ejecutivo

**11 hallazgos**: 3 críticos, 4 altos, 3 medios, 1 bajo. Los tres críticos están en el wizard
`unificar_etapas_wizard.py` (`leulit_tarea.unificar_etapas_wizard`/`...snapshot`): el mecanismo
de rollback puede fallar con `IntegrityError` y abortar sin restaurar nada en cuanto se combina
con "Eliminar etapas obsoletas" (su combinación por defecto sugerida en la UI); el asistente
puede colar una etapa **personal** de un usuario cualquiera como etapa compartida para toda la
empresa, o directamente reventar con "Expected singleton"; y `project.task._search_project_is_borrador`
ignora el parámetro `value`, devolviendo el mismo dominio (invertido) para `=True` y `=False`.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/unificar_etapas_wizard.py:94-127` (`action_rollback`) + `:1034-1126` (`_limpiar_etapas_obsoletas`) | El rollback restaura `type_ids`/`stage_id` con IDs de etapas que la propia normalización acaba de `unlink()`, violando FK | Ejecutar normalización con `crear_snapshot=True` **y** `limpiar_etapas_obsoletas=True` (ambas disponibles/sugeridas en el paso 3), luego pulsar "Restaurar Estado Anterior" | Antes de escribir, filtrar por `.exists()` cada id de `type_ids`/`stage_id` guardado, o impedir combinar limpieza+snapshot y avisar explícitamente que el rollback quedará parcial |
| Crítico | `models/unificar_etapas_wizard.py:378-380` y `:305-326` (`_crear_etapas_destino`) | Las etapas "destino" se buscan por `name` sin filtrar `user_id=False`, pudiendo capturar una etapa **personal** de un usuario | Un usuario cualquiera tiene/crea una etapa personal llamada igual que una etapa destino ("Pendiente", "En proceso"...); al lanzar el wizard esa etapa personal se cuela como destino compartido y se asigna a `type_ids`/`stage_id` de TODOS los proyectos/tareas de la empresa (o si hay coincidencia doble, `.filtered(...).id` revienta con `ValueError: Expected singleton`) | Añadir `('user_id','=',False)` a las dos búsquedas, igual que ya se hace (correctamente) en `_limpiar_etapas_obsoletas` |
| Crítico | `models/project_task.py:37-45` (`_search_project_is_borrador`) | El método `search` de un campo computado ignora el parámetro `value`; sólo mira `operator`, así que `('project_borrador','=',True)` y `('project_borrador','=',False)` devuelven **el mismo** dominio | Cualquier búsqueda/agrupación explícita por `project_borrador = True` (filtro guardado, pivot, API externa) devuelve el conjunto invertido — mismo resultado que `=False` | Usar `value` para decidir el operador final: `operator = ('!=' if value else '=')` si `operator=='='` (y su inverso para `!=`) |
| Alto | `models/hr_timesheet_switch.py:18-34` (`_prepare_copy_values`) | Clave de diccionario `unit_amount` duplicada (líneas 24 y 31); Python se queda con la última (31), la línea 24 es código muerto | Cada vez que se usa "Cambiar de tarea" (`hr.timesheet.switch`): la nueva entrada de tiempo hereda `record.unit_amount` (la duración ya acumulada en la entrada anterior) en vez de arrancar en `0`, que es lo que sugiere el comentario/intención de un "switch" | Eliminar una de las dos claves; decidir con el usuario si el valor correcto es `0` (nueva entrada arranca sin duración) o `record.unit_amount` (comportamiento actual) — ver sección de dudas |
| Alto | `models/hr_timesheet_switch.py:33` | `"product_uom_id": 4` — ID hardcodeado de `uom.uom` (probablemente "Horas") en vez de xmlid | Cualquier entorno donde esa fila no tenga id=4 (reinstalación, migración, merge de datos — el propio `README.md` del repo describe remapeos de IDs en migraciones) asigna una unidad de medida incorrecta o inexistente sin error visible | `self.env.ref('uom.product_uom_hour').id` |
| Alto | `models/project_task.py:22-23` y `models/hr_timesheet_switch.py:43-44` (`_get_default_project`/`_default_project_id`) | `search([('name','=','Internal'), ...])` sin `limit=1` usado directamente como default de un `Many2one` | Si existiese más de un proyecto "Internal" para la compañía (nada en el módulo lo impide), el default devuelve un recordset multi-registro; acceder a su `.id` implícito en la conversión del campo puede romper con "Expected singleton" al crear cualquier tarea o al abrir "Imputar Tiempo" | Añadir `limit=1` en ambas búsquedas |
| Alto | `views/project_task.xml:182-194` y `views/mail_activity.xml:68-85` | El mismo external id `leulit_20260116_1030_action` (sin prefijo de módulo, por tanto `leulit_tarea.leulit_20260116_1030_action`) se declara por completo dos veces en ficheros distintos, ambos cargados por el manifest | Al instalar/actualizar el módulo, `mail_activity.xml` se carga después de `project_task.xml` (orden del manifest) y **sobrescribe** la acción; la definición de `project_task.xml` (sin `view_ids` explícitos) queda muerta — quien la edite pensando que es la acción activa no verá efecto alguno | Eliminar la definición duplicada de `views/project_task.xml:182-194` (la de `mail_activity.xml` es la más completa: incluye `view_ids`) y dejar una única fuente de verdad |
| Medio | `security.xml:3-11` (`<record id="project.access_project_task" ...>`) | Se reutiliza el external id **del módulo `project`** (con prefijo explícito) para sobreescribir un `ir.model.access` que no pertenece a `leulit_tarea` | Restringe `perm_create`/`perm_unlink` para `project.group_project_user` de forma global (afecta a cualquier módulo que dependa de `project`, no sólo a este). Al desinstalar `leulit_tarea` este cambio **no se revierte** (el registro sigue perteneciendo al módulo `project`), dejando una divergencia permanente respecto al stock | Documentar explícitamente esta intención en un comentario XML, o mover la restricción a una regla/ACL propia de `leulit_tarea` en vez de mutar el registro stock, para que el ciclo de vida del cambio esté ligado al módulo |
| Medio | `models/account_analytic_line.py:19-97` (`_check_date_imputacion_horas`) | Hasta 4 `search()` independientes por cada línea de `account.analytic.line`, dentro de un bucle `for item in self`, en un `@api.constrains` que se dispara en cada `create`/`write` de imputaciones de tiempo | Un `create_multi`/import de N imputaciones dispara hasta 4×N consultas SQL individuales en vez de precalcular por lote | Precalcular fuera del bucle (o agrupar por `user_id`) los `search()` de `historial_circular`, `alumno`, `rel_parte_escuela_cursos_alumnos` y `reunion_asistente` para el conjunto de usuarios de `self` |
| Medio | `models/unificar_etapas_wizard.py:978-1011` (`_normalizar_tareas`) y `:912-976` (`_normalizar_proyecto`) | `tarea.write(...)` y `proyecto.write(...)` se ejecutan registro a registro dentro de un bucle Python, en vez de agrupar por etapa destino y hacer un único `write` por grupo | Con `aplicar_a_proyectos=True` (opción por defecto) sobre una empresa con muchos proyectos/tareas: N escrituras individuales, cada una generando su propio mensaje de tracking en el chatter de cada tarea (spam de notificaciones a followers) además de N round-trips a BD | Agrupar `tareas.filtered(lambda t: t.stage_id.id == origen_id).write({'stage_id': destino_id})` por cada línea de mapeo, en vez de tarea a tarea |
| Bajo | `models/project_task.py:15-19` (`onchange_stage_id`) | Nombres de etapa hardcodeados `['Hecho','Realizada','Finalizado']` para decidir `date_end` | Si una etapa "de cierre" tiene otro nombre (o se traduce/renombra vía el propio wizard de este módulo, que normaliza a "Realizada"), el `date_end` no se rellena; patrón ya señalado como frágil en la documentación interna del propio módulo (`NORMALIZACION_ETAPAS*.md`) | Marcar las etapas de cierre con un campo booleano (`is_closing_stage`) en vez de comparar por nombre — coherente con el propio objetivo del wizard de normalización |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Crítico] Rollback del wizard puede fallar con IntegrityError y no restaurar nada

`models/unificar_etapas_wizard.py`:

```python
# líneas 94-127, UnificarEtapasSnapshot.action_rollback
for proyecto_data in estado_proyectos:
    proyecto = self.env['project.project'].browse(proyecto_data['id'])
    if proyecto.exists():
        proyecto.write({
            'type_ids': [(6, 0, proyecto_data['type_ids'])]
        })
        ...
for tarea_data in estado_tareas:
    tarea = self.env['project.task'].browse(tarea_data['id'])
    if tarea.exists():
        tarea.write({
            'stage_id': tarea_data['stage_id']
        })
```

El snapshot se toma (`_crear_snapshot`, línea 876) **antes** de normalizar, capturando los
`type_ids`/`stage_id` que están a punto de dejar de usarse. Si además `limpiar_etapas_obsoletas`
está activo (línea 853-856), `_limpiar_etapas_obsoletas` (línea 1034) hace `etapa.unlink()`
precisamente sobre esas etapas ya no referenciadas — que son las que el snapshot guardó.

`action_rollback` sólo comprueba `proyecto.exists()`/`tarea.exists()` (que el proyecto/tarea en
sí no se haya borrado), **no** que los IDs de etapa que va a reinyectar sigan existiendo. Escribir
`(6, 0, [id_borrado, ...])` en un Many2many, o `stage_id = id_borrado` en un Many2one, es una
violación de integridad referencial a nivel de PostgreSQL: la fila ya no existe en
`project_task_type`. Esto no "no recupera algunas etapas" (como sugiere el propio
`NORMALIZACION_ETAPAS_TECNICA.md:349`, *"Rollback NO revierte eliminaciones"*) — hace fallar la
transacción completa del botón, así que ni siquiera los proyectos/tareas que sí podrían
restaurarse correctamente quedan restaurados. El snapshot es la única red de seguridad que el
propio wizard promete al usuario ("💾 Snapshot creado... Puedes revertir los cambios") y falla
exactamente en el escenario donde más se necesita.

**Fix propuesto:**

```python
def action_rollback(self):
    self.ensure_one()
    if not self.activo:
        raise UserError(_('Este snapshot ya no está activo y no puede usarse para rollback'))
    import json
    TaskType = self.env['project.task.type']

    estado_proyectos = json.loads(self.estado_proyectos)
    proyectos_restaurados = 0
    for proyecto_data in estado_proyectos:
        proyecto = self.env['project.project'].browse(proyecto_data['id'])
        if proyecto.exists():
            type_ids_validos = TaskType.browse(proyecto_data['type_ids']).exists().ids
            proyecto.write({'type_ids': [(6, 0, type_ids_validos)]})
            proyectos_restaurados += 1

    estado_tareas = json.loads(self.estado_tareas)
    tareas_restauradas = 0
    for tarea_data in estado_tareas:
        tarea = self.env['project.task'].browse(tarea_data['id'])
        stage_id = tarea_data['stage_id']
        if tarea.exists() and (not stage_id or TaskType.browse(stage_id).exists()):
            tarea.write({'stage_id': stage_id})
            tareas_restauradas += 1
    ...
```

Y avisar en el mensaje final cuántas etapas no pudieron recrearse (porque fueron eliminadas)
para que el usuario sepa que la restauración es parcial.

### 3.2 [Crítico] Una etapa personal de un usuario puede colarse como etapa compartida

```python
# líneas 305-326, _crear_etapas_destino
for nombre_etapa in self.ETAPAS_DESTINO_TAREA:
    etapa = TaskType.search([('name', '=', nombre_etapa)], limit=1)   # <- sin user_id=False
    if not etapa:
        etapa = TaskType.create({...})
```

```python
# líneas 377-380, action_analizar_etapas
etapas_destino = self.env['project.task.type'].search([
    ('name', 'in', self.ETAPAS_DESTINO_TAREA)                          # <- sin user_id=False
])
```

`project.task.type` (heredado del `project` stock de Odoo) tiene un campo `user_id` para las
etapas *personales* por usuario (kanban "Mis Tareas"). El propio módulo es consciente de esto y
lo protege explícitamente en `_limpiar_etapas_obsoletas` (línea 1060: `TaskType.search([('user_id', '=', False)])`,
con el comentario "SOLO elimina etapas compartidas/públicas"), pero **no** aplica el mismo filtro
al elegir/crear las etapas *destino*. Dos consecuencias, ambas alcanzables sin tocar código:

1. Si el `search([('name','=',nombre_etapa)], limit=1)` de `_crear_etapas_destino` encuentra
   primero (según el `_order` por defecto) una etapa **personal** de un usuario con ese nombre,
   la da por buena y no crea la etapa compartida — la personal termina siendo "la" destino.
2. En `action_analizar_etapas` (líneas 389-396):
   ```python
   etapa_destino = etapas_destino.filtered(lambda e: e.name == etapa_origen.name)
   if not etapa_destino:
       etapa_destino = etapas_destino[0]
   mapeo_lineas.append((0, 0, {
       ...
       'etapa_destino_id': etapa_destino.id,   # <- revienta si etapa_destino tiene >1 registro
   ```
   Si existen a la vez una etapa compartida y una personal con el mismo nombre, `.filtered(...)`
   devuelve 2 registros y `.id` lanza `ValueError: Expected singleton`, rompiendo el Paso 1 del
   wizard para toda la empresa. Si sólo hay una coincidencia (la personal), el mapeo se genera
   igualmente y, al ejecutar la normalización real, esa etapa **privada de un usuario** se
   inyecta en `type_ids` de todos los proyectos y en `stage_id` de todas las tareas de la
   compañía (`_normalizar_proyecto`/`_normalizar_tareas`).

**Fix propuesto:** añadir `('user_id', '=', False)` a ambas búsquedas (líneas 314 y 378-380), y
al mismo dominio del widget `many2many_checkboxes`/`domain` en `views/unificar_etapas_wizard.xml:99-101`
(`etapa_destino_id`), que tiene el mismo problema al dejar elegir manualmente una etapa destino.

### 3.3 [Crítico] `_search_project_is_borrador` ignora `value`

```python
# models/project_task.py:37-45
def _search_project_is_borrador(self, operator, value):
    estado_borrador = self.env['project.status'].search([('name', '=', 'En borrador')])
    if operator == '=':
        operator = '!='
    elif operator == '!=':
        operator = '='
    else:
        raise ValueError("Invalid operator for search_project_is_borrador")
    return [('project_id.project_status', operator, estado_borrador.id)]
```

El método de búsqueda del campo computado `project_borrador` (línea 62) sólo mira `operator`, no
`value`. Actualmente el propio módulo sólo usa `('project_borrador', '=', False)` en tres
`ir.actions.act_window` (`views/project_task.xml:136,162,177`), y en ese caso concreto la
inversión de operador "acierta por casualidad" (equivale a `project_status != En borrador`, que
es lo que se pretende). Pero el método, tal y como está escrito, es **incorrecto como API de
campo `search`**: `('project_borrador', '=', True)` devuelve exactamente el mismo dominio
(`project_status != En borrador`) que `('project_borrador', '=', False)` — es decir, lo
contrario de lo que el nombre del campo promete. Cualquier uso futuro con `value=True`
(un filtro guardado, un "Group By" en pivot/kanban sobre este campo, una llamada XML-RPC externa)
devolverá el conjunto invertido.

**Fix propuesto:**

```python
def _search_project_is_borrador(self, operator, value):
    if operator not in ('=', '!='):
        raise ValueError("Invalid operator for search_project_is_borrador")
    estado_borrador = self.env['project.status'].search([('name', '=', 'En borrador')], limit=1)
    quiere_borrador = value if operator == '=' else not value
    domain_operator = '=' if quiere_borrador else '!='
    return [('project_id.project_status', domain_operator, estado_borrador.id)]
```

## 4. Plan de acción priorizado

1. **[Crítico]** `unificar_etapas_wizard.py::action_rollback` — validar existencia de cada id
   antes de reescribir `type_ids`/`stage_id`; documentar restauración parcial al usuario.
2. **[Crítico]** `unificar_etapas_wizard.py::_crear_etapas_destino` y `action_analizar_etapas`
   (líneas 314, 378-380) — filtrar `('user_id','=',False)`; mismo filtro en el dominio de
   `views/unificar_etapas_wizard.xml:99-101`.
3. **[Crítico]** `models/project_task.py::_search_project_is_borrador` — usar `value` para
   determinar el operador final.
4. **[Alto]** `models/hr_timesheet_switch.py:24,31` — resolver la clave `unit_amount` duplicada
   (requiere decisión de negocio, ver Dudas §5).
5. **[Alto]** `models/hr_timesheet_switch.py:33` — sustituir `product_uom_id: 4` por
   `self.env.ref('uom.product_uom_hour').id`.
6. **[Alto]** `models/project_task.py:23` y `models/hr_timesheet_switch.py:44` — añadir
   `limit=1` a las búsquedas de proyecto "Internal".
7. **[Alto]** `views/project_task.xml:182-194` — eliminar la acción duplicada
   `leulit_20260116_1030_action` (dejar sólo la de `views/mail_activity.xml`).
8. **[Medio]** `security.xml:3-11` — documentar o rehacer el override del `ir.model.access`
   stock `project.access_project_task` para que no quede huérfano al desinstalar el módulo.
9. **[Medio]** `models/account_analytic_line.py::_check_date_imputacion_horas` — precalcular
   los `search()` fuera del bucle `for item in self`.
10. **[Medio]** `unificar_etapas_wizard.py::_normalizar_proyecto/_normalizar_tareas` — agrupar
    escrituras por etapa destino en vez de registro a registro.
11. **[Bajo]** `models/project_task.py::onchange_stage_id` — sustituir comparación por nombre de
    etapa por un flag booleano.

## 5. Dudas / no verificable sin entorno

- **`hr_timesheet_switch.py:24,31` (clave `unit_amount` duplicada):** no puedo determinar desde
  el código cuál era el valor *intencionado* — `0` (una nueva entrada de tiempo al "cambiar de
  tarea" debería arrancar sin duración acumulada) o `record.unit_amount` (heredar la duración de
  la entrada anterior, que es lo que realmente ocurre hoy porque es la clave que sobrevive).
  Esto depende del flujo de negocio real de "Cambiar de tarea" en producción, que no puedo probar
  aquí. Requiere confirmación del usuario antes de tocarlo.
- **`_get_default_project`/`_default_project_id` — riesgo de multi-registro:** no puedo consultar
  la base de datos para confirmar si existe hoy más de un proyecto llamado "Internal" por
  compañía; el fix (`limit=1`) es defensivo y de bajo riesgo en cualquier caso.
- **`_crear_etapas_destino` — colisión con etapa personal:** no puedo consultar
  `project.task.type` en producción para saber si existen hoy etapas personales llamadas
  "Pendiente", "En proceso", "Realizada", "Pospuesta" o "N/A" que dispararían el bug de forma
  inmediata. El defecto de código es real independientemente del dato actual.
- **Comportamiento exacto de Odoo ante `(6,0,[id_inexistente])` / `write({'stage_id': id_borrado})`:**
  me baso en el comportamiento estándar de integridad referencial de PostgreSQL/ORM de Odoo
  (inserción de una referencia a una fila ya borrada = violación de FK). No he podido ejecutar el
  módulo para confirmar el mensaje de error exacto ni si Odoo 17 envuelve la excepción de alguna
  forma distinta antes de propagarla al usuario.
- **`security.xml:3-11` override de `project.access_project_task`:** no he revisado el histórico
  git completo del fichero para confirmar si esta sobreescritura fue deliberada (podría ser una
  decisión de producto ya acordada). Lo señalo como riesgo operativo, no como bug, y no lo toco
  sin confirmación.
- No se han encontrado controladores HTTP (`controllers/`) ni `ir.cron` en este módulo, por lo
  que los apartados correspondientes del `<task>` no aplican aquí.
