# Revisión — `maintenance_equipment_changes`

Revisión de código completa (modelos, vistas XML, seguridad, manifest). El módulo no tiene
controladores, wizards, cron jobs ni reports — solo 3 modelos Python, 2 vistas XML y un
fichero de seguridad. Toda la revisión es por lectura de código; no hay entorno Odoo
disponible para ejecutar nada (ver sección de dudas al final).

Depende de `maintenance` (core) y `leulit_taller` (no depende de `leulit` directamente, pero
`leulit_taller` sí depende de `leulit`, así que la cadena de foundation llega igual).

## 1. Resumen ejecutivo

**18 hallazgos**: 2 críticos, 4 altos, 7 medios, 5 bajos. Los dos críticos son bugs que
provocan una excepción no controlada (`ValueError`/`AttributeError`) en escenarios de uso
normales: escritura múltiple de `production_lot` y alta de una fila de histórico sin fecha
en el tree editable. Los altos incluyen un fallo de permisos que puede bloquear la propia
operación que el usuario intenta hacer, una regla de negocio ("no cambiar el equipo padre")
que solo se aplica en el cliente web y es trivialmente evitable por API, un dato de
aeronavegabilidad (TSN/TSO/NG/NF "Actual") que se muestra como `0.0` en vez de heredar el
valor "Inicio" cuando falta jerarquía, y una duplicación ×4 de consultas costosas en el
cálculo del histórico.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/maintenance_equipment.py:26` | `write()` no es multi-record safe (`self.production_lot` sobre recordset >1) | `equipments.write({'production_lot': X})` sobre 2+ registros (edición masiva desde list view, import, script) | Reescribir `write()` iterando `self` o separando lectura de "antes" antes del `super().write()` |
| Crítico | `models/maintenance_equipment_changes.py:26,43,60,77` | `item.date.date()` con `item.date` = `False` → `AttributeError` | Alta de fila en el tree editable `historico_pieza` (`views/maintenance_equipment.xml:16`) rellenando `tsn_inicio` antes que `Fecha`, ya que `@api.depends` no incluye `date` | Añadir `date` a `@api.depends` y guardar contra `date` vacío |
| Alto | `models/maintenance_equipment.py:39` | `create()` de `maintenance.equipment.changes` sin `sudo()` dentro de `write()` | Usuario sin `maintenance.group_equipment_manager` (pero con permiso de escritura sobre `maintenance.equipment`) cambia `production_lot` → `AccessError` en el `create()` interno, revierte todo el `write()` | `sudo()` en el `create()` |
| Alto | `models/maintenance_equipment_changes.py:20-32,37-49,54-66,71-83` | Rama `else` solo cubre `equipment_id` vacío; si `first_parent`/`helicoptero` faltan, el valor "Actual" queda en `0.0` en vez de heredar `*_inicio` | Motor/pieza sin `first_parent` resuelto o cuyo `first_parent.helicoptero` está vacío | Igualar el fallback al de la rama de `equipment_id` vacío (`item.tsn_actual = item.tsn_inicio`, etc.) |
| Alto | `models/maintenance_equipment.py:16-21` | Regla "no se puede cambiar el equipo padre" solo se aplica en `@api.onchange` (cliente web) | `write({'parent_id': X})` vía RPC/XML-RPC, import de datos, o cualquier código Python que no pase por el formulario web | Mover el control a `write()` (o `@api.constrains`) para que aplique también fuera del formulario |
| Alto | `models/maintenance_equipment_changes.py` (los 4 computes) | 4 métodos de cómputo independientes repiten la misma búsqueda `next_change` y la misma llamada a `acumulados_between_dates` por cada fila | Vista `historico_pieza` (`views/maintenance_equipment.xml:16-29`) con N filas → hasta 4×N búsquedas + 4×N llamadas a un método potencialmente costoso sobre `leulit.vuelo` | Fusionar en un único método `@api.depends` que calcule los 4 campos a la vez |
| Medio | `models/maintenance_equipment.py:23-42` | Se crea una entrada de histórico aunque `production_lot` no cambie de valor real | `equipment.write({'production_lot': mismo_id, 'otro_campo': x})` | Comparar valor antiguo vs nuevo antes de crear el registro |
| Medio | `models/maintenance_equipment.py:50` | Comparación literal `item.category_id.name == 'Pieza'` (no por `xml_id`) | Renombrado/traducción de la categoría "Pieza", o categoría no creada con ese nombre exacto | Referenciar la categoría por `xml_id` fijo (requiere que exista un registro de datos, hoy no lo hay en ningún módulo del árbol revisado) |
| Medio | `models/maintenance_equipment_changes.py` + `security.xml` | Sin `company_id` ni `ir.rule` — no hay compartimentación multi-compañía | Lectura directa del modelo (RPC/vista técnica) por un usuario de la compañía 1 mostrando históricos de motor de la compañía 2 (Icarus) | Añadir `company_id` (related a `equipment_id.company_id` o similar) + `ir.rule` — requiere decisión de negocio, ver dudas |
| Medio | `models/maintenance_equipment.py:55`; `models/maintenance_equipment_changes.py:25,42,59,76` | `get_last_change()` y las búsquedas de `next_change` fijan `order` sin el desempate `id asc` que sí define `_order` a nivel de modelo | Dos históricos con el mismo `date` (ver hallazgo de `effective_date` más abajo) → resultado no determinista | Añadir `, id asc`/`id desc` al `order=` de esas búsquedas |
| Medio | `models/maintenance_equipment.py:37` | `date` del histórico = `self.effective_date`, un campo cuyo mantenimiento (correcto) depende de que el caller lo fije justo antes de tocar `production_lot` (patrón visto en `leulit_almacen/models/stock_install.py:235-236`), sin ninguna validación aquí | Cualquier caller futuro que escriba `production_lot` sin fijar `effective_date` a la fecha real del cambio → histórico con fecha incorrecta/duplicada | Validar o derivar `date` explícitamente en `write()` en lugar de asumir que `effective_date` ya está correcto |
| Medio | `security.xml` + `views/maintenance_equipment.xml:16` | El histórico de motor es inmutable solo a nivel de UI (`edit="false"`); no hay `unlink()`/`write()` guardado ni `mail.thread` — `group_equipment_manager` puede alterar/borrar TSN/TSO históricos sin dejar rastro | Manager edita el modelo por otra vía (RPC, vista técnica) o borra filas si el widget de o2m no oculta el icono de papelera | Añadir `unlink()`/`write()` restringido (o mixin de log) si el dato debe considerarse un audit trail |
| Medio | `models/leulit_helicoptero.py:16-52` | `_get_motores`, `_get_datos_inicio_motor` y `_get_fecha_instalacion_motor` recalculan cada una, por separado, `get_motor_equipment_helicopter()` (con su propio `search`) y `get_last_change()` | Apertura de la ficha de `leulit.helicoptero` con las 3 secciones visibles → múltiples `search()` redundantes | Cachear el motor/última entrada en un único compute que alimente los 5 campos |
| Bajo | `__manifest__.py:22` + `menu.xml` | `application: True` sin ningún menú propio (todo `menu.xml` está comentado) | El módulo aparece en el listado de Apps de Odoo sin punto de entrada | `application: False` (es una extensión de `maintenance`, no una app independiente) |
| Bajo | `menu.xml:4-11` | Código muerto (menú comentado en su totalidad) | — | Eliminar el fichero o el bloque comentado |
| Bajo | `models/maintenance_equipment.py:19` | `self._origin.parent_id != False` en vez de `if self._origin.parent_id:` | Cualquier disparo del onchange | Usar comparación de truthiness estándar, evita el `_logger.warning("Comparing apples and oranges…")` de Odoo |
| Bajo | `models/leulit_helicoptero.py:16`, `models/maintenance_equipment.py:54` | Métodos públicos de un solo registro (`get_motor_equipment_helicopter`, `get_last_change`) sin `ensure_one()` | Uso futuro con recordset multi-registro | Añadir `self.ensure_one()` defensivo |
| Bajo | `__manifest__.py:4` | `description` vacía, sin README del módulo | — | Documentar brevemente el propósito del módulo |

## 3. Hallazgos críticos/altos desarrollados

### C1 — `write()` no soporta multi-record (crash "Expected singleton")

**Fichero:** `models/maintenance_equipment.py:23-42`

```python
def write(self, vals):
    if 'production_lot' in vals:
        pieza_antigua = False
        if self.production_lot:                      # <- crashea si self tiene >1 registro
            pieza_antigua = self.production_lot
        result = super(MaintenanceEquipment, self).write(vals)
        values_equipment_changes = {
            'equipment_id' : self.id,                 # <- también inválido en multi
            ...
        }
        self.env['maintenance.equipment.changes'].create(values_equipment_changes)
    else:
        result = super(MaintenanceEquipment, self).write(vals)
    return result
```

Cualquier override de `write()` en Odoo debe soportar que `self` contenga varios registros
(edición múltiple desde una vista lista, `load()`/import, o cualquier llamada programática
tipo `equipments.write({...})`). En cuanto `'production_lot'` está en `vals` y `self` tiene
más de un registro, `self.production_lot` lanza `ValueError: Expected singleton` — la
escritura completa falla, incluidos los demás campos del `vals`.

**Fix propuesto** (resuelve también el hallazgo Alto "sin `sudo()`" y el Medio "histórico
duplicado sin cambio real"):

```python
def write(self, vals):
    if 'production_lot' not in vals:
        return super().write(vals)

    old_lots = {rec.id: rec.production_lot for rec in self}
    result = super().write(vals)

    changes_model = self.env['maintenance.equipment.changes'].sudo()
    for rec in self:
        old_lot = old_lots.get(rec.id)
        if old_lot == rec.production_lot:
            continue  # sin cambio real, no generar entrada de histórico
        if not rec.effective_date:
            raise UserError(_(
                "No se puede registrar el cambio de pieza de %s sin una fecha efectiva."
            ) % rec.display_name)
        changes_model.create({
            'equipment_id': rec.id,
            'old_production_lot_id': old_lot.id if old_lot else False,
            'new_production_lot_id': rec.production_lot.id,
            'tsn_inicio': rec.production_lot.tsn_actual if rec.production_lot.tsn_actual > 0 and rec.production_lot.tsn_actual != rec.production_lot.tsn_inicio else rec.production_lot.tsn_inicio,
            'tso_inicio': rec.production_lot.tso_actual if rec.production_lot.tso_actual > 0 and rec.production_lot.tso_actual != rec.production_lot.tso_inicio else rec.production_lot.tso_inicio,
            'ng_inicio': rec.production_lot.ng_actual if rec.production_lot.ng_actual > 0 and rec.production_lot.ng_actual != rec.production_lot.ng_inicio else rec.production_lot.ng_inicio,
            'nf_inicio': rec.production_lot.nf_actual if rec.production_lot.nf_actual > 0 and rec.production_lot.nf_actual != rec.production_lot.nf_inicio else rec.production_lot.nf_inicio,
            'date': rec.effective_date,
        })
    return result
```

### C2 — Compute de TSN/TSO/NG/NF Actual crashea si `date` está vacío

**Fichero:** `models/maintenance_equipment_changes.py:17-32` (idéntico en `_get_tso`,
`_get_ng`, `_get_nf`)

```python
@api.depends('equipment_id','tsn_inicio')          # <- no incluye 'date', pero se usa abajo
def _get_tsn(self):
    for item in self:
        item.tsn_actual = 0.0
        if item.equipment_id:
            if item.equipment_id.first_parent:
                if item.equipment_id.first_parent.helicoptero:
                    now = datetime.now()
                    next_change = self.search([('equipment_id','=',item.equipment_id.id),('date','>',item.date)], order='date asc', limit=1)
                    datos = self.env['leulit.vuelo'].acumulados_between_dates(
                        item.equipment_id.first_parent.helicoptero.id,
                        item.date.date(),               # <- AttributeError si item.date es False
                        now.date() if not next_change else next_change.date.date())
                    ...
```

La vista `historico_pieza` (`views/maintenance_equipment.xml:16`) es un
`tree editable="bottom" create="true"` con `date` como primera columna, pero nada obliga al
usuario a rellenarla primero. Como `@api.depends` no incluye `'date'`, basta con teclear
`tsn_inicio` (segunda casilla habitual) en la fila nueva para que el compute se dispare con
`item.date == False`, y `False.date()` lanza `AttributeError: 'bool' object has no attribute
'date'`.

**Fix propuesto** — fusiona además los 4 computes en uno solo (resuelve también los
hallazgos Alto "rama else ausente" y Alto "duplicación ×4 de queries"):

```python
@api.depends('equipment_id', 'date', 'tsn_inicio', 'tso_inicio', 'ng_inicio', 'nf_inicio')
def _compute_actuales(self):
    for item in self:
        # Fallback por defecto: heredar el valor "Inicio" (igual que si falta equipment_id)
        item.tsn_actual = item.tsn_inicio
        item.tso_actual = item.tso_inicio
        item.ng_actual = item.ng_inicio
        item.nf_actual = item.nf_inicio

        if not (item.equipment_id and item.date):
            continue
        parent = item.equipment_id.first_parent
        if not (parent and parent.helicoptero):
            continue

        next_change = self.search([
            ('equipment_id', '=', item.equipment_id.id),
            ('date', '>', item.date),
        ], order='date asc, id asc', limit=1)
        end_date = next_change.date.date() if next_change else datetime.now().date()
        datos = self.env['leulit.vuelo'].acumulados_between_dates(
            parent.helicoptero.id, item.date.date(), end_date)
        if datos:
            item.tsn_actual = item.tsn_inicio + datos[0][0]
            item.tso_actual = item.tso_inicio + datos[0][0]
            item.ng_actual = item.ng_inicio + datos[0][1]
            item.nf_actual = item.nf_inicio + datos[0][1]

tsn_actual = fields.Float(compute='_compute_actuales', string='TSN Actual')
tso_actual = fields.Float(compute='_compute_actuales', string='TSO Actual')
ng_actual = fields.Float(compute='_compute_actuales', string='NG Actual')
nf_actual = fields.Float(compute='_compute_actuales', string='NF Actual')
```

Nota: mantengo el uso de `datos[0][0]` para TSN/TSO y `datos[0][1]` para NG/NF tal cual el
código original (mismo índice de tupla reutilizado para el par TSN/TSO y el par NG/NF) —
es el comportamiento actual, no lo cambio sin confirmar con el usuario si es intencional
(ver sección de dudas).

### A1 — `create()` del histórico sin `sudo()`

**Fichero:** `models/maintenance_equipment.py:39`

```python
self.env['maintenance.equipment.changes'].create(values_equipment_changes)
```

`security.xml:14-22` da a `base.group_user` solo `perm_read=1` sobre
`maintenance.equipment.changes` (`perm_create=0`). Si un usuario sin
`maintenance.group_equipment_manager` puede escribir `production_lot` en
`maintenance.equipment` (el ACL de `maintenance.equipment` en sí no forma parte de este
módulo — viene del core `maintenance` y no está vendorizado en el repo, así que no puedo
confirmar aquí qué grupos tienen ese permiso; ver sección de dudas), este `create()` lanzará
`AccessError` y hará fallar **todo** el `write()`, incluido el cambio de pieza que el
usuario sí estaba autorizado a hacer. Es un registro de auditoría interno del sistema, no
algo que el usuario deba necesitar permisos explícitos para generar como efecto colateral de
una acción que sí tiene permitida.

**Fix:** `self.env['maintenance.equipment.changes'].sudo().create(values_equipment_changes)`
(incluido ya en el fix de C1).

### A2 — TSN/TSO/NG/NF "Actual" caen a `0.0` en vez de heredar "Inicio"

**Fichero:** `models/maintenance_equipment_changes.py:17-32,34-49,51-66,68-83`

En los 4 computes, la única rama `else` cubre `if item.equipment_id:` (línea 21/38/55/72).
Si `equipment_id` existe pero `equipment_id.first_parent` está vacío, o
`first_parent.helicoptero` está vacío, ninguna asignación adicional ocurre — el campo se
queda en el `0.0` inicial de la línea de arriba, en lugar de heredar `tsn_inicio` (que sí es
el fallback cuando falta `equipment_id`). En el dominio de este módulo (Part-145,
trazabilidad de horas de motor/pieza) mostrar `0.0` en vez del valor de referencia real es
engañoso: un componente con muchas horas puede aparecer con "0.0" en la columna "Actual" del
histórico si su cadena de `first_parent`/`helicoptero` no está resuelta en ese momento
(pieza desinstalada, jerarquía de equipos incompleta, etc.).

**Fix:** incluido en el snippet de C2 — el fallback `item.tsn_actual = item.tsn_inicio` (y
análogos) se aplica ahora por defecto y solo se sobrescribe cuando el cálculo real es
posible.

### A3 — Regla "no cambiar el equipo padre" solo en el cliente web

**Fichero:** `models/maintenance_equipment.py:16-21`

```python
@api.onchange('parent_id')
def onchange_parent(self):
    if self._origin:
        if self._origin.parent_id != False:
            raise UserError('No se puede cambiar el equipamiento padre.')
```

Un `@api.onchange` solo se ejecuta cuando el usuario edita el campo en el formulario web del
cliente de Odoo. No se ejecuta en: `write()` llamado por XML-RPC/JSON-RPC externo, en un
import/`load()`, en un script de migración, ni en ningún otro módulo que haga
`equipment.write({'parent_id': X})` directamente (por ejemplo, un futuro flujo de
`leulit_almacen` o `leulit_taller`). La regla de negocio, tal como está, es puramente
cosmética fuera del formulario.

**Fix propuesto:**

```python
def write(self, vals):
    if 'parent_id' in vals:
        for rec in self:
            if rec.parent_id and rec.parent_id.id != vals['parent_id']:
                raise UserError(_("No se puede cambiar el equipamiento padre de %s.") % rec.display_name)
    # resto de la lógica de write() (ver fix de C1)
    ...
```

(Puede combinarse con el `write()` ya reescrito en C1 — un único método cubriendo ambos
controles.)

### A4 — Duplicación ×4 de queries costosas en el histórico

**Fichero:** `models/maintenance_equipment_changes.py` (los 4 métodos `_get_tsn`, `_get_tso`,
`_get_ng`, `_get_nf`)

Cada uno de los 4 métodos, para cada fila del histórico, repite exactamente la misma
búsqueda (`next_change = self.search([...])`) y la misma llamada a
`self.env['leulit.vuelo'].acumulados_between_dates(...)` — solo cambia qué posición de la
tupla `datos[0]` se usa al final. Con `store=False` en los 4 campos, esto se recalcula en
**cada lectura** de la vista `historico_pieza` (`views/maintenance_equipment.xml:16-29`), es
decir, hasta 4× búsquedas + 4× llamadas a `acumulados_between_dates` por fila mostrada. No
puedo cuantificar el coste real de `acumulados_between_dates` (está en `leulit_taller`, fuera
de alcance) pero por su nombre agrega datos de vuelos en un rango de fechas — probablemente
no trivial.

**Fix:** el compute único mostrado en C2 elimina la duplicación (una sola búsqueda y una sola
llamada a `acumulados_between_dates` por fila, alimentando los 4 campos).

## 4. Plan de acción priorizado

1. **[Crítico]** `models/maintenance_equipment.py` — reescribir `write()` para soportar
   multi-record (bloquea cualquier edición masiva de `production_lot`).
2. **[Crítico]** `models/maintenance_equipment_changes.py` — añadir `date` a los
   `@api.depends` y proteger contra `date` vacío antes de llamar `.date()`.
3. **[Alto]** `models/maintenance_equipment.py:39` — `sudo()` en el `create()` del histórico
   (incluido en el punto 1 si se aplica el fix combinado).
4. **[Alto]** `models/maintenance_equipment_changes.py` — corregir el fallback de
   TSN/TSO/NG/NF Actual cuando falta `first_parent`/`helicoptero`.
5. **[Alto]** `models/maintenance_equipment.py:16-21` — mover el control de "no cambiar
   padre" a `write()`, no solo `onchange`.
6. **[Alto]** `models/maintenance_equipment_changes.py` — fusionar los 4 computes en uno
   (mismo cambio que el punto 2, un solo PR cubre ambos).
7. **[Medio]** `models/maintenance_equipment.py` — no crear entrada de histórico si
   `production_lot` no cambia realmente.
8. **[Medio]** `models/maintenance_equipment.py:50` — decidir con el usuario cómo referenciar
   la categoría "Pieza" de forma robusta (ver dudas).
9. **[Medio]** `security.xml` / modelo — decidir con el usuario si `maintenance.equipment.changes`
   necesita `company_id` + `ir.rule` (ver dudas).
10. **[Medio]** `get_last_change()` y las búsquedas `next_change` — añadir `id asc` como
    desempate de `order`.
11. **[Medio]** Validar/objetar en `write()` si `effective_date` no está fijado antes de
    cambiar `production_lot` (evita fechas de histórico incorrectas).
12. **[Medio]** Decidir con el usuario si el histórico de motor necesita protección adicional
    contra edición/borrado por `group_equipment_manager` (ver dudas).
13. **[Medio]** `models/leulit_helicoptero.py` — fusionar `_get_motores`,
    `_get_datos_inicio_motor`, `_get_fecha_instalacion_motor` en un único compute que
    reutilice el motor/última entrada ya calculados.
14. **[Bajo]** `__manifest__.py` — `application: False`.
15. **[Bajo]** `menu.xml` — eliminar el bloque comentado.
16. **[Bajo]** `models/maintenance_equipment.py:19` — `if self._origin.parent_id:` en vez de
    `!= False`.
17. **[Bajo]** Añadir `ensure_one()` defensivo en `get_motor_equipment_helicopter` y
    `get_last_change`.
18. **[Bajo]** `__manifest__.py` — completar `description`.

## 5. Dudas / no verificable sin entorno

- **ACLs reales de `maintenance.equipment` (core):** el módulo `maintenance` de Odoo no está
  vendorizado en este repo (es parte del core, no de `addons/third-party-addons`), así que no
  he podido leer su `ir.model.access.csv` ni sus `ir.rule` para confirmar qué grupos pueden
  escribir `production_lot`. Esto es necesario para saber con certeza en qué casos concretos
  se dispara el `AccessError` del hallazgo A1 (sin `sudo()`). El hallazgo en sí (falta de
  `sudo()` en un `create()` dentro de un `write()` de otro modelo) es válido independientemente
  de esa confirmación.
- **`effective_date` como campo core de `maintenance.equipment`:** no está definido en
  ningún fichero de este repo (ni en `maintenance_equipment_changes` ni en `leulit_taller`),
  solo se asigna/lee. Asumo que es un campo estándar del módulo `maintenance` de Odoo 17
  (`Effective Date`), pero no puedo confirmarlo leyendo código del repo — solo por
  conocimiento general de la API. Si resultara no ser un campo core, el `write()` de
  `models/maintenance_equipment.py:37` fallaría con `AttributeError` en cada cambio de
  `production_lot`, lo que sería un hallazgo crítico adicional. Recomiendo confirmarlo
  ejecutando `env['maintenance.equipment']._fields.get('effective_date')` en un shell de
  Odoo antes de dar el punto por cerrado.
- **`ondelete` implícito del `Many2one` `equipment_id`:** `models/maintenance_equipment_changes.py:86`
  define `equipment_id` como `required=True` sin `ondelete` explícito. No puedo confirmar sin
  ejecutar el módulo si Odoo 17 aplica `cascade` (borra el histórico al borrar el equipo,
  perdiendo el audit trail) o `restrict`/otro comportamiento por defecto para un Many2one
  requerido sin `ondelete` explícito. Recomiendo fijarlo explícitamente una vez decidido el
  comportamiento deseado.
- **Semántica de negocio de `datos[0][0]`/`datos[0][1]` reutilizados para TSN/TSO y NG/NF:**
  el código original usa el mismo índice de la tupla que devuelve
  `acumulados_between_dates` tanto para TSN como para TSO (`datos[0][0]`), y tanto para NG
  como para NF (`datos[0][1]`). Esto puede ser intencional (p.ej. TSO se calcula igual que
  TSN cuando no hay overhaul de por medio) o un bug heredado — no lo cambio ni lo señalo como
  hallazgo separado porque no puedo verificar la intención sin ver `leulit.vuelo.acumulados_between_dates`
  a fondo (está fuera de alcance) ni el criterio de negocio real.
- **Necesidad de `company_id`/`ir.rule` (hallazgo Medio #9) y protección del histórico
  (hallazgo Medio #12):** son decisiones de diseño/negocio (multi-compañía, política de
  auditoría), no solo técnicas — las dejo documentadas como propuesta pero sin aplicar ni
  decidir por mi cuenta, a la espera de confirmación del usuario.
- **`edit="false"` en el tree de `historico_pieza` (`views/maintenance_equipment.xml:16`):**
  no he podido confirmar sin ejecutar el cliente web si Odoo 17 sigue mostrando el icono de
  borrado por fila en un `tree editable` con `edit="false"` pero sin `delete="false"`
  explícito. Si lo oculta, el hallazgo Medio #12 pierde parte de su superficie de ataque en
  la UI estándar (seguiría aplicando vía RPC/vista técnica).
