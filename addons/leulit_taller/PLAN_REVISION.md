# Revisión de código — `leulit_taller`

Revisión estática (sin entorno Odoo disponible) de modelos, vistas, seguridad, wizards y reports del addon `addons/leulit_taller/`. Toda afirmación está basada en lectura directa del código citado; donde la confirmación exigía ejecutar Odoo se indica explícitamente en la sección de dudas.

## 1. Resumen ejecutivo

- **Críticos: 5** — onchains con efectos persistentes sin guardar, ausencia total de `ir.rule` + CRUD completo para `leulit.RBase` en documentos Part-145, transiciones de estado de firma sin control servidor, bug multi-registro en `maintenance.request.write()`, `NameError` en `do_move_certificate`.
- **Altos: 8** — asimetría de validación del certificador entre CRS/Form One/Boroscopia, doble-check sin exigir 2 personas distintas, timestamp `+35 min` sospechoso, usuario "Albert Petanas" hardcodeado 9 veces, bug `self`/`item` en `_get_is_activable`, `TypeError` en `create_sale_order_from_material_utilizado`, patrón de resolución de compañía por nombre (13+ sitios), mutación de `self.env.companies` como efecto colateral.
- **Medios: 11** — N+1 en varios `compute`, `search([])` de modelo completo en funciones `_search_*`, SQL crudo con `.format()`, import deprecado de Odoo 16/17 que romperá en 18, posible pérdida de líneas en `historic_check`, mal uso sistemático de `_logger.error`, `t-raw` sobre campos `Char` no saneados en 2 informes, `int(get_param(...))` sin guarda en 12 sitios, hardcode de `company_id=2`, `job_card` con `maintenance_plan_id=33` hardcodeado, commit manual dentro de un método de modelo.
- **Bajos: 4** — código muerto/comentado, `get_number()` sin uso y frágil, inconsistencia `Text`/`Html` en plantilla de remarks, `return` dentro de bucle en `modificar_manual`.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/project_task.py:84-108,31,119-121` | `@api.onchange('stage_id')` crea `account.analytic.line` y `leulit.maintenance_form_one`, y escribe `stage_id` en tareas hijas/padre | Usuario cambia el combo Estado en el formulario (sin pulsar Guardar) y luego cierra sin guardar | Mover la creación de timesheet/Form One y los `write()` de hijos/padre a un método server-side (`write()`/botón explícito), nunca a un `@api.onchange` |
| Crítico | `models/maintenance_request.py:51,58,61` | `onchange_stage` escribe `self.helicoptero.statemachine` (registro persistido, no `self`) dentro de un onchange | Abrir una WO y tocar el stage sin guardar cambia el estado del helicóptero en BD igualmente | Quitar el `write` del onchange; mover a `write()`/botón de acción explícito |
| Crítico | `security.xml` (todo el fichero) + módulo completo | No existe ningún `ir.rule`; todo CRUD (incl. `unlink`) sobre CRS, Form One, AD, SB, Job Card, etc. está concedido a `leulit.RBase`, grupo que heredan casi todos los roles funcionales | Cualquier usuario con acceso básico al ERP puede borrar un CRS o Form One ya firmado | Definir accesos diferenciados (p.ej. solo lectura + create para RBase, unlink restringido a CAMO/IT) para los modelos Part-145 críticos — requiere decisión de negocio, ver sección 5 |
| Crítico | `models/leulit_maintenance_crs.py:101-105`, `leulit_maintenance_form_one.py:115-116`, `leulit_maintenance_boroscopia.py:91-98` | `set_estado_firmado*` no comprueba grupo, estado previo ni identidad del certificador; el `groups="leulit.RolIT_developer"` que lo restringe solo existe en la vista | Cualquier usuario RBase llama al método por RPC/consola y firma el documento sin ser IT ni certificador | Añadir `self.env.user.has_group('leulit.RolIT_developer')` y comprobación de estado dentro del método |
| Crítico | `models/maintenance_request.py:34-42` | `write()` usa `self.crs`/`fecha_cierre` sobre el recordset completo cuando puede tener varios registros; aplica la misma fecha a todos | Cambio de stage en varias WO a la vez (selección múltiple / import) | Iterar `for m in self.filtered(...):` calculando `fecha_cierre` por registro |
| Crítico | `models/leulit_rel_formone_lot.py:1-7,43` | `raise ValidationError(...)` y `_('Nuevo')` sin importar `ValidationError` ni `_` | Ejecutar `do_move_certificate()` sin `form_one`/`pieza_id`, o que `next_by_code` devuelva vacío | Añadir `from odoo.exceptions import ValidationError` y `from odoo import _` |
| Alto | `models/leulit_maintenance_form_one.py:118-121`, `leulit_maintenance_boroscopia.py:97-98` | `set_estado_pendiente_firma[_boroscopia]` no valida que el usuario sea el `certificador`, a diferencia de CRS (`leulit_maintenance_crs.py:108-112`) | Cualquier técnico distinto al certificador designado marca el Form One/Boroscopia como "pendiente" | Replicar la validación de `leulit_maintenance_crs.set_estado_pendiente_firma` |
| Alto | `models/leulit_maintenance_double_check.py:18-35`, `leulit_maintenance_security_inspect.py:18-35` | Nada impide que `first_user_*` y `second_user_*` sean el mismo `self.env.user` | Un único mecánico marca las dos casillas de doble verificación | Añadir constraint que compare `first_user_*` != `second_user_*` — **confirmar con negocio, ver sección 5** |
| Alto | `models/leulit_tarea_sensible_seguridad.py:55-60` | `onchange_d_check` fija `datetime_d_check = datetime.now() + timedelta(minutes=35)`, único sitio del módulo con ese offset | Se marca `d_check` y la fecha registrada queda 35 min en el futuro | Confirmar si es regla de negocio; si no, usar `datetime.now()` como en los demás — **ver sección 5** |
| Alto | `models/leulit_wizard_add_task_request.py:33,80,103`, `models/project_task.py:231,257,278`, `models/leulit_wizard_create_maintenance_request.py:47,95,117` | `self.env['res.users'].search([('name','=','Albert Petanas')])` hardcodeado 9 veces | Esa persona cambia de nombre/se desactiva/se va → `user_ids` queda vacío sin error | Sustituir por `ir.config_parameter` (mismo patrón que `leulit.maintenance_hours_project`) — **confirmar si es regla de negocio deliberada, ver sección 5** |
| Alto | `models/maintenance_plan.py:46-54` | `_get_is_activable` comprueba `self.parent_id` (recordset completo) dentro de un `for item in self:` en vez de `item.parent_id` | Vista lista con varios Planes de Mantenimiento a la vez | Cambiar `self.parent_id` por `item.parent_id` |
| Alto | `models/maintenance_request.py:176` | `if 'DES' not in material.reference:` sin proteger `reference` falso, a diferencia del método gemelo (línea 204, que sí usa `(material.reference or '')`) | Un `stock.move.line` de material sin `reference` → `TypeError` al crear presupuesto | Igualar a `(material.reference or '')` |
| Alto | 8 ficheros (ver 3.8) | Resolución de `res.company` por nombre literal (`'Icarus Manteniment S.L.'`, `'Helipistas S.L.'`) con operadores inconsistentes (`=`, `like`, `ilike`) en 13+ sitios | Renombrar la compañía rompe silenciosamente reports/wizards (recordset vacío, sin error) | Resolver por `xmlid` como ya se hace en `leulit_almacen` (convención ya documentada en el proyecto) |
| Alto | `models/maintenance_request.py:69,76,787,1065` | `self.env.companies = ...` se asigna como efecto colateral dentro de métodos `compute`/de impresión | Cualquier lectura de `material_ids`/`componentes_ids` estrecha el alcance multiempresa para el resto de la transacción | No mutar `self.env.companies`; usar `.with_company()`/`sudo().with_context(allowed_company_ids=...)` acotado a la búsqueda concreta |
| Medio | `models/leulit_airworthiness_directive.py:14-23`, `leulit_service_bulletin.py:14-23` | `_get_remaining_hours` hace un `search()` + suma en Python por cada registro (N+1) | Listado de 100+ AD/SB dispara 100+ queries | Sustituir por `read_group`/SQL agregada |
| Medio | `models/stock_lot.py:28-66` | 4 `compute` distintos (`_get_tsn/_get_tso/_get_ng/_get_nf`) repiten la misma búsqueda de `maintenance.equipment.changes` por registro | Vista con muchos lotes → 4x queries redundantes | Unificar en un solo `compute` que calcule los 4 campos con una única búsqueda |
| Medio | `models/maintenance_equipment.py:183-221,44-51`; `leulit_helicoptero.py:25-42,53-71` | `_search_first_parent`, `_search_motor`, `_search_motor_lot`, `get_all_childs_app` cargan **todo** el modelo con `self.search([])` y filtran en Python | Filtrar por `first_parent`/`motor` en un catálogo grande de equipos | Reescribir como dominio SQL o `read_group`, evitar cargar todo el modelo |
| Medio | `models/leulit_helicoptero_pieza.py:20-44`, `leulit_vuelo.py:27-46` | SQL crudo construido con `.format()` en vez de parámetros (`%s`) | Hoy los valores vienen de `.id`/`date` internos (no explotable), pero es un patrón inseguro que se replica | Usar `self._cr.execute(sql, (params,))` con placeholders |
| Medio | `models/maintenance_request.py:13` | `from odoo.addons.web.controllers.main import Binary` — import no usado, vía shim deprecado (confirmado en fuente 17.0) que **desaparece en Odoo 18** | Ninguno hoy; falla al migrar a 18.0 (migración ya planificada según memoria del proyecto) | Eliminar el import (no se usa `Binary` en el fichero) |
| Medio | `models/leulit_maintenance_manual.py:88-99` | `onchange_check` hace `self.historic_check = [(0,0,{...})]`, reemplazando el valor completo del O2M en vez de añadir | Editar `check` dos veces en la misma sesión de edición, o tras añadir una línea manual al histórico | Cambiar a construir la lista combinando `(4, id)` de las líneas existentes + el nuevo `(0,0,...)` — **requiere verificación en UI real, ver sección 5** |
| Medio | 9 ubicaciones (ver 3.12) | `_logger.error(...)` usado para mensajes puramente informativos (no errores) | Logs de producción a nivel ERROR sin que haya fallo real, puede disparar alertas falsas | Bajar a `_logger.info`/`debug` salvo los 3 casos que sí capturan una excepción |
| Medio | `report/leulit_informe_defectos.xml:113`, `report/leulit_informe_work_order.xml:336,375` | `t-raw` sobre `task.name`/`tarea_preventiva.referencia`/`anomalia.codigo`, que son `Char` normales (no `Html`, no saneados por Odoo) | Un usuario introduce `<script>`/HTML en el nombre de la tarea o el código de la anomalía | Cambiar a `t-esc` o `t-field` salvo que el campo pase a ser `Html` deliberadamente |
| Medio | 12 ubicaciones (ver 3.13) | `int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))` repetido sin guarda | Parámetro no configurado en una BD nueva/de test → `TypeError: int() argument must be...` en vez de un error claro | Centralizar en un único método con `UserError` explícito si falta el parámetro |
| Medio | `models/leulit_rel_formone_lot.py:33` | `self.with_company(2)` — id de compañía hardcodeado | Entorno de test/staging con IDs de compañía distintos | Resolver la compañía Icarus por xmlid, igual que el resto de casos de este hallazgo |
| Medio | `models/leulit_job_card.py:42-69` | `upd_job_card_planned_activities` tiene `maintenance_plan_id=33` hardcodeado; no hay botón visible que lo llame (código de `change_equipamiento_id` comentado) | Ejecutar el método (si algo lo invoca) no actualiza nada salvo el plan 33 | Confirmar si sigue siendo necesario; si sí, parametrizar; si no, eliminar junto al código comentado |
| Medio | `models/leulit_maintenance_manual.py:33-55` | `fix_existing_attachments` hace `self.env.cr.commit()` dentro de un método de modelo | Si algún día se invoca desde un flujo normal de request (no solo shell) rompe la atomicidad de la transacción | Documentar claramente "solo shell" (ya lo dice el docstring) o quitar el commit y dejarlo al framework |
| Bajo | `models/leulit_ata.py:16-17` | `get_number()` hace `self.ata_number.replace(...)` sin proteger `False`; no se usa en ningún sitio del addon | Si algo llega a llamarlo con `ata_number` vacío, `AttributeError` | Añadir guarda `if self.ata_number else ''`, o eliminar si sigue sin uso |
| Bajo | `models/leulit_maintenance_manual.py:58-70` | `modificar_manual` itera `for item in self` pero hace `return` en la primera vuelta | Invocar el botón desde una selección múltiple solo procesa el primer registro, sin aviso | Mover el `return` fuera del bucle o usar `self.ensure_one()` si nunca debe ser multi-registro |
| Bajo | `leulit_maintenance_form_one_template.py:34` vs `leulit_maintenance_form_one.py:89` | `remarks` es `Text` en la plantilla pero `Html` en el Form One que la consume | El usuario debe teclear `<p>`/`<br>` a mano en un textarea plano para que el contador de líneas HTML funcione | Igualar `remarks` de la plantilla a `fields.Html` |
| Bajo | Varios ficheros | Bloques de código comentado dejados en el fichero (`leulit_job_card.py:16-30,71-84`, etc.) | — | Eliminar código muerto en vez de comentarlo |

## 3. Hallazgos críticos y altos — detalle

### 3.1 Onchain con efectos persistentes sin guardar (Crítico)

`models/project_task.py`, método `onchange_stage_manintenance_task` (`@api.onchange('stage_id')`, líneas 17-127):

```python
# líneas 84-95
else:
    if not self.timesheet_ids:
        for user in self.user_ids:
            self.env['account.analytic.line'].create({...})   # persiste SIEMPRE

# líneas 96-108
if self.item_job_card_id.oblig_form_one:
    if self.env['leulit.maintenance_form_one'].search([('task_id','!=',self.id)]):
        ...
        self.env['leulit.maintenance_form_one'].create({...})  # persiste SIEMPRE

# línea 121
self.parent_id.write({'stage_id': stage_id.id})                # persiste SIEMPRE
```

Un `@api.onchange` se dispara cada vez que el campo cambia en el formulario **antes** de guardar, incluso si el usuario cancela después. `create()`/`write()` sobre otros modelos (`account.analytic.line`, `leulit.maintenance_form_one`, tareas hijas/padre) son escrituras reales a BD independientemente de que `self` sea un registro virtual — el desarrollador ya conocía este riesgo, porque usa `self._origin.id` en varias líneas de la misma función (ej. línea 92, 107), pero no lo aplicó a estas llamadas de `create`/`write`. Resultado: abrir una tarea y tocar el desplegable de estado (sin guardar) puede generar un Form One EASA o una línea de parte de horas fantasma, o mover el estado de una tarea padre/hermana, sin que el usuario haya confirmado nada.

Mismo patrón, más contenido, en `models/maintenance_request.py:45-64` (`onchange_stage`):

```python
if self.accepted:
    ...
    self.helicoptero.statemachine = "En taller"   # self.helicoptero es un registro real persistido
...
if not self.accepted:
    ...
    self.helicoptero.statemachine = "En servicio"
```

**Fix propuesto:** mover toda creación/escritura de otros modelos fuera del `onchange`, a `write()` (con detección de cambio de `stage_id` como ya hace `ProjectTask.write()` para `job_card_id`) o a un botón de acción explícito que el usuario dispare conscientemente.

### 3.2 Ausencia de `ir.rule` y CRUD completo para `RBase` en documentos Part-145 (Crítico)

`security.xml` (fichero completo) da de alta ~29 `ir.model.access` y **todas** conceden `perm_read=perm_create=perm_write=perm_unlink=1` al grupo `leulit.RBase`, incluyendo:

- `leulit.maintenance_crs` (CRS/Release to Service)
- `leulit.maintenance_form_one` (EASA Form 1)
- `leulit.maintenance_boroscopia`
- `leulit.airworthiness_directive`, `leulit.service_bulletin`
- `leulit.job_card`, `leulit.job_card_item`
- `leulit.modifications_and_repairs`

No existe **ningún** `ir.rule` en el módulo (`grep -r "ir.rule"` no devuelve nada). Según `CLAUDE.md` del proyecto, `leulit.RBase` es la raíz de la jerarquía de roles y "virtualmente cada rol funcional encadena hasta RBase" — es decir, prácticamente cualquier usuario con acceso al ERP tiene permiso de **borrado** sobre documentos de aeronavegabilidad ya firmados (CRS, Form One, AD). No hay separación entre "puede ver/crear" y "puede borrar un documento firmado", ni entre roles de taller y roles no relacionados con mantenimiento.

**Fix propuesto:** no lo propongo sin validarlo primero — ver sección 5, dado el precedente documentado en `CLAUDE.md` de que restringir `ir.rule` sobre modelos usados transversalmente (`hr.employee`) rompió producción. Aun así, como mínimo el `unlink` de documentos ya `firmado` debería bloquearse a nivel de modelo (constraint/override de `unlink()`), no solo de permisos de grupo.

### 3.3 Transiciones de firma sin control servidor (Crítico) + asimetría CRS/Form One/Boroscopia (Alto)

Las vistas ocultan el botón "Firmar IT" a todos salvo `leulit.RolIT_developer`:

```xml
<!-- leulit_maintenance_crs.xml:10 / leulit_maintenance_form_one.xml:11 / leulit_maintenance_boroscopia.xml:10 -->
<button name="set_estado_firmado" ... groups="leulit.RolIT_developer"/>
```

pero los métodos que ese botón llama no comprueban nada:

```python
# leulit_maintenance_crs.py:101-105
def set_estado_firmado(self):
    for task in self.request.task_ids:
        task.supervisado_por = self.certificador.id
    self.estado = 'firmado'
    self.wizard_send_email()

# leulit_maintenance_form_one.py:115-116
def set_estado_firmado(self):
    self.estado = 'firmado'
```

`groups` en una vista solo oculta el botón en el cliente web; no es una restricción de acceso a nivel de modelo/método. Como `ir.model.access` da `perm_write=1` a `RBase` sobre estos modelos, cualquier usuario puede invocar `set_estado_firmado` vía `call_button`/XML-RPC sin ser IT ni certificador.

Además, comparando las tres implementaciones del paso previo ("Firmar" normal, `estado='pendiente'`):

```python
# leulit_maintenance_crs.py:108-112  -> SÍ valida
def set_estado_pendiente_firma(self):
    mecanico_user = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id)])
    if mecanico_user.id != self.certificador.id:
        raise UserError('Solo el técnico certificador puede firmar esta orden de trabajo.')
    self.estado = 'pendiente'

# leulit_maintenance_form_one.py:118-121  -> NO valida quién firma
def set_estado_pendiente_firma(self):
    if not self.part_45 and not self.other_regulation:
        raise UserError(...)
    self.estado = 'pendiente'

# leulit_maintenance_boroscopia.py:97-98  -> NO valida nada
def set_estado_pendiente_firma_boroscopia(self):
    self.estado = "pendiente"
```

Form One y Boroscopia son documentos de la misma familia normativa (Part-145 release to service) que CRS, pero solo CRS impide que alguien que no sea el `certificador` asignado inicie la firma.

**Fix propuesto:**
```python
def set_estado_firmado(self):
    if not self.env.user.has_group('leulit.RolIT_developer'):
        raise UserError('Solo IT puede forzar la firma.')
    ...
def set_estado_pendiente_firma(self):
    mecanico_user = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id)])
    if mecanico_user.id != self.certificador.id:
        raise UserError('Solo el técnico certificador puede firmar.')
    ...
```
replicado en `leulit_maintenance_form_one.py` y `leulit_maintenance_boroscopia.py`.

### 3.4 Bug multi-registro en `maintenance.request.write()` (Crítico)

```python
# models/maintenance_request.py:34-42
def write(self, vals):
    res = super(MaintenanceRequest, self).write(vals)
    if 'stage_id' in vals:
        fecha_cierre = fields.Date.today()
        crs_incompletos = self.crs.filtered(lambda crs: crs.tipo_crs == 'incompleto')
        if crs_incompletos:
            fecha_cierre = max(crs_incompletos, key=lambda crs: crs.fecha).fecha
        self.filtered(lambda m: m.stage_id.done).write({'close_date': fecha_cierre})
    return res
```

Si `self` contiene más de una `maintenance.request` (p.ej. cambio de stage en varias OT seleccionadas a la vez desde la vista lista, o una actualización masiva vía import/XML-RPC), `self.crs` agrega los CRS de **todas** las OT del lote, se calcula **una sola** `fecha_cierre` y se aplica igual a todas las OT que queden en estado "done" del lote. Esto corrompe `close_date`, campo que alimenta reporting de cierre de OT.

**Fix propuesto:**
```python
def write(self, vals):
    res = super().write(vals)
    if 'stage_id' in vals:
        for m in self.filtered(lambda r: r.stage_id.done):
            fecha_cierre = fields.Date.today()
            crs_incompletos = m.crs.filtered(lambda crs: crs.tipo_crs == 'incompleto')
            if crs_incompletos:
                fecha_cierre = max(crs_incompletos, key=lambda crs: crs.fecha).fecha
            m.close_date = fecha_cierre
    return res
```

### 3.5 `NameError` en `do_move_certificate` (Crítico)

```python
# models/leulit_rel_formone_lot.py:1-7
from odoo import fields, models, api
import logging
...
# línea 30-43
def do_move_certificate(self):
    if self.form_one and self.pieza_id:
        move_certificate = self.env['stock.move_certificate'].create({
            'name': self.with_company(2).env['ir.sequence'].next_by_code('stock.move.certificate') or _('Nuevo'),
            ...
        })
        move_certificate.action_validate()
        self.move_created = True
    else:
        raise ValidationError("No se ha podido crear el movimiento de certificado, falta información")
```

Ni `ValidationError` ni `_` están importados en este fichero. En el `else` (falta `form_one` o `pieza_id`) el usuario no ve el mensaje de validación pensado, sino un `NameError: name 'ValidationError' is not defined` (traceback interno). El mismo problema existe con `_('Nuevo')` si `next_by_code` devolviera vacío.

**Fix propuesto:**
```python
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
```

## 4. Plan de acción priorizado

1. **[Crítico]** `models/project_task.py` y `models/maintenance_request.py` — sacar todo `create()`/`write()` sobre otros modelos de los `@api.onchange` (§3.1).
2. **[Crítico]** `models/leulit_maintenance_crs.py`, `leulit_maintenance_form_one.py`, `leulit_maintenance_boroscopia.py` — añadir control servidor (`has_group`, estado, certificador) a `set_estado_firmado*`/`set_estado_pendiente_firma*` (§3.3).
3. **[Crítico]** `models/maintenance_request.py:34-42` — corregir `write()` para iterar por registro (§3.4).
4. **[Crítico]** `models/leulit_rel_formone_lot.py` — arreglar imports (`ValidationError`, `_`) (§3.5).
5. **[Crítico]** `security.xml` — decidir con negocio el modelo de permisos para documentos Part-145 firmados antes de tocar nada (§3.2, ver sección 5).
6. **[Alto]** `models/leulit_maintenance_form_one.py`, `leulit_maintenance_boroscopia.py` — igualar validación de certificador a la de CRS (§3.3).
7. **[Alto]** `models/maintenance_plan.py:46-54` — `self.parent_id` → `item.parent_id` en `_get_is_activable`.
8. **[Alto]** `models/maintenance_request.py:176` — proteger `material.reference` como ya hace el método gemelo.
9. **[Alto]** Resolver con negocio: doble-check mismo usuario (§3 tabla, `leulit_maintenance_double_check.py`/`leulit_maintenance_security_inspect.py`), offset de 35 min (`leulit_tarea_sensible_seguridad.py:60`), y hardcode "Albert Petanas" (9 sitios) — ver sección 5 antes de tocar código.
10. **[Alto]** Sustituir búsqueda de `res.company` por nombre por resolución vía `xmlid` en los 8 ficheros afectados; eliminar mutaciones de `self.env.companies`.
11. **[Medio]** N+1 en `leulit_airworthiness_directive.py`/`leulit_service_bulletin.py` (`_get_remaining_hours`) y en `stock_lot.py` (4 computes → 1).
12. **[Medio]** `maintenance_equipment.py`/`leulit_helicoptero.py` — reescribir `_search_first_parent`/`_search_motor*`/`get_all_childs_app` sin `self.search([])` completo.
13. **[Medio]** Quitar import muerto `Binary` en `maintenance_request.py:13` antes de la migración a Odoo 18.
14. **[Medio]** Centralizar el `int(get_param('leulit.maintenance_hours_project'))` repetido 12 veces con manejo de error claro.
15. **[Medio]** `report/leulit_informe_defectos.xml`, `leulit_informe_work_order.xml` — cambiar `t-raw` por `t-esc` en campos `Char` no saneados.
16. **[Medio]** Bajar a `info`/`debug` los `_logger.error` que no capturan una excepción real (9 sitios).
17. **[Bajo]** Limpieza: código comentado, `get_number()` sin uso, `modificar_manual` con `return` en bucle, unificar `Text`/`Html` en `remarks` de plantilla.

## 5. Dudas / no verificable sin entorno

- **Permisos (`ir.rule`) sobre documentos Part-145.** No sé si el diseño actual (todo RBase con CRUD total) es una simplificación deliberada ya aceptada por el negocio, o un descuido. El propio `CLAUDE.md` del proyecto documenta un intento previo de restringir por `ir.rule` sobre un modelo transversal (`hr.employee`) que rompió producción en horas — por eso no propongo un fix concreto sin hablarlo antes. Pregunta: ¿queréis que un usuario RBase cualquiera pueda borrar un CRS/Form One ya firmado, o hace falta restringir `unlink` (y quizá `write` post-firma) a un rol más específico (CAMO/IT)?
- **Doble check / inspección de seguridad con el mismo usuario.** `leulit_maintenance_double_check.py` y `leulit_maintenance_security_inspect.py` no impiden que `first_user_*` y `second_user_*` sean la misma persona. ¿Es un control de 4 ojos que debe forzarse en código, o hay algún control organizativo fuera del ERP que lo cubre?
- **Offset de 35 minutos en `onchange_d_check`** (`leulit_tarea_sensible_seguridad.py:60`). Es el único sitio del módulo con ese comportamiento; el resto de timestamps similares usan `datetime.now()` sin offset. No he encontrado ninguna referencia normativa/de negocio en el código que lo explique. ¿Es intencional?
- **Hardcode "Albert Petanas"** (9 sitios, 3 ficheros). ¿Es una regla de negocio real (un coordinador fijo que siempre debe quedar asignado a las subtareas autogeneradas), o un dato de prueba que quedó en producción?
- **`onchange_check` reemplazando `historic_check`** (`leulit_maintenance_manual.py:88-99`). Mi lectura del comportamiento de Odoo para asignaciones a One2many dentro de un `onchange` indica que sustituye el valor completo en vez de añadir, lo que podría perder líneas de histórico ya cargadas en el formulario. Confirmar con una prueba real en el entorno de test (editar dos veces el campo `check` de un manual con histórico existente antes de guardar).
- **`ProjectTask.write()` (`models/project_task.py:294-302`)** lee `self.job_card_id` antes/después de `super().write()` sobre un `self` que podría ser multi-registro. No tengo certeza absoluta de la semántica exacta de Odoo 17 para lectura de un campo Many2one sobre un recordset con más de un registro en este contexto concreto; recomiendo una prueba dirigida (escritura masiva de `job_card_id` sobre 2+ tareas a la vez) antes de tratarlo como confirmado.
- **`get_datos_motor_instalado_in_fecha`/`acumulados_between_dates` con SQL vía `.format()`.** Hoy los valores que reciben vienen siempre de `.id`/campos `Date` internos, así que no he encontrado una ruta de inyección real explotable — lo señalo como riesgo de patrón/fragilidad (falla si `fecha` es `False`), no como vulnerabilidad confirmada.
