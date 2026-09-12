# Revisión de código — `leulit_actividad_taller`

Revisión estática (sin entorno Odoo disponible) de todo el addon: modelos, vistas XML,
seguridad, wizards y report QWeb. Dependencias reales según `__manifest__.py`:
`leulit`, `leulit_taller` (y transitivamente `project`, `maintenance`, `account_analytic`
vía esos módulos).

## 1. Resumen ejecutivo

- **1 crítico** — un `onchange` de este módulo pisa silenciosamente a otro con el mismo
  nombre definido en `leulit_taller`, perdiendo lógica de negocio (`solucion_defecto`) sin
  ningún error visible.
- **6 altos** — 2 de seguridad (acceso CRUD sin restricción a registros regulatorios
  Part-145 + HTML de usuario sin sanear volcado a un PDF `wkhtmltopdf`) y 4 de
  errores/robustez del ORM (`search()` sin `limit=1`, crash por `AttributeError`,
  falta de guardas ante valores `False`).
- **5 medios** — pérdida silenciosa de tags, mal uso de `_logger.error` para trazas,
  validación insuficiente en un wizard, código muerto voluminoso dentro de un QWeb.
- **5 bajos** — código muerto no alcanzable (confirmado por grep en todo el repo),
  un modelo/vista completos deshabilitados sin explicación, duplicación DRY menor,
  inconsistencia de nomenclatura de xmlids.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/project_task.py:12-26` | `onchange_item_job_card` tiene el mismo nombre que el de `leulit_taller/models/project_task.py:187`, así que lo sustituye por completo (no llama a `super()`) | Cualquier usuario cambia `item_job_card_id` en una tarea de taller | Renombrar el método y/o llamar a la lógica base; no duplicar campos ya cubiertos |
| Alto (seguridad) | `security.xml:4-22` | `leulit.item_experiencia_mecanico` (registro Part-145) y `leulit.tipo_actividad_mecanico` (catálogo referenciado por literales) tienen CRUD completo para `leulit.RBase`, sin `ir.rule` en ningún otro fichero del repo | Cualquier empleado con acceso básico edita/borra registros de experiencia o renombra/borra un tipo de actividad usado por comparación de string en Python | Restringir `perm_write`/`perm_unlink`/`perm_create` a un grupo más específico (CAMO/calidad) — requiere decisión de negocio, ver §5 |
| Alto (seguridad) | `report/leulit_experiencia.xml:434` | `<t t-out="o.remarks"/>` vuelca sin sanear un campo `Html` editable por cualquier `RBase` dentro de un informe generado por `wkhtmltopdf` | Un usuario introduce `<img src="file:///...">` o una URL externa en `remarks` y alguien imprime "Informe Experiencia" | Sanear/echar el texto plano (`t-esc`) o sanitizar el HTML antes de guardarlo; restringir quién puede escribir `remarks` |
| Alto | `models/leulit_wizard_report_experiencia.py:29,49` | `search([('name','like','Icarus')])` sin `limit=1`; si no hay match, `company_icarus.logo_reports` es `False` y `.decode()` revienta; si hay >1 match, "Expected singleton" | Ejecutar el informe en una BD donde la compañía no se llame exactamente "…Icarus…" o no tenga logo | Añadir `limit=1`, comprobar `company_icarus` y `company_icarus.logo_reports` antes de `.decode()`, lanzar `UserError` claro |
| Alto | `models/leulit_item_experiencia_mecanico.py:150` | `env['leulit.mecanico'].search([('user_id','=',aal.user_id.id)])` sin `limit=1`; con `aal.user_id` vacío o mecánicos duplicados, `mecanico.id` revienta ("Expected singleton") | Ejecutar `run_upd_datos_actividad` sobre líneas analíticas sin usuario o con mecánicos duplicados | Añadir `limit=1` y manejar el caso vacío explícitamente |
| Alto | `models/leulit_item_experiencia_mecanico.py:181-182` | `stock.location` buscado por `name` exacto sin `limit=1` ni scoping por compañía — mismo patrón frágil ya documentado en `leulit_almacen` (ubicaciones repetidas por compañía) | Multi-compañía (Helipistas/Icarus) con nombres de ubicación duplicados, o 0 resultados | Añadir `limit=1` + resolver por xmlid/compañía en vez de por nombre, igual que en `leulit_almacen` |
| Alto | `models/leulit_item_experiencia_mecanico.py:105-125` | `run_upd_acc_analytic_line_requests` recorre **todo** `project.task` con `maintenance_request_id` sin filtro de fecha (a diferencia de su gemelo `run_upd_datos_actividad`) y hace 2 `write()` por línea; además `tarea.finish_date + timedelta(...)` no comprueba `finish_date` falsy | Se invoca la función sobre una BD madura, o sobre una tarea sin `finish_date` | Acotar por fecha como el método hermano, fusionar los dos `write()` en uno, guardar contra `finish_date` falsy |
| Medio | `models/project_task.py:14` (y equivalente en `leulit_taller`) | `tag_id = search([('name','=','Tareas de mantenimiento')])` sin `limit=1`; si no existe el tag, `self.tag_ids = tag_id` (vía `write`) vacía **todos** los tags de la tarea | Onchange de `item_job_card_id` en una tarea que ya tenía otros tags manuales, en una BD sin el tag "Tareas de mantenimiento" | Ver §5 (duda de negocio) — posible `limit=1` + `tag_id | self.tag_ids` en vez de sustituir |
| Medio | `models/leulit_item_experiencia_mecanico.py:98,100,125,129,131,280` | `_logger.error(...)` usado para trazas informativas ("start thread", "fin") | Cada llamada a los métodos threaded | Cambiar a `_logger.info`/`_logger.debug` |
| Medio | `views/leulit_wizard_report_experiencia.xml:13-27` | `mecanico_id`, `from_date`, `to_date` no son `required`, pero `print_report_experiencia()` construye el dominio sin guardas | Lanzar el informe con el formulario vacío | Añadir `required="1"` en la vista y/o validar en Python con `UserError` explícito |
| Medio | `report/leulit_experiencia.xml:1-263` | ~260 líneas de plantilla/CSS antigua comentadas en vez de borradas | — (mantenibilidad) | Eliminar el bloque comentado (queda en el historial de git) |
| Medio | `report/leulit_experiencia.xml:337,339,402` | `t-call` a `experiencia_mecanico_report_css` tres veces en el mismo render | Cada generación del informe | Llamarlo una sola vez, fuera del `header`/`article` repetidos |
| Bajo | `models/leulit_item_experiencia_mecanico.py:97-133` | `upd_acc_analytic_line_requests` / `upd_datos_actividad` (y sus `run_*`) no tienen ningún llamador en todo el repo (grep global) — código muerto que arrastra los 3 "Altos" de arriba | — | Cablearlos (botón/cron) o eliminarlos — ver §5 |
| Bajo | `models/leulit_item_experiencia_mecanico.py:48-94` | `get_data_to_report()` tampoco tiene ningún llamador (la plantilla activa usa `get_activity_to_report`, `get_duration_to_report`, `get_privilege_to_report` directamente) | — | Eliminar, es resto de la plantilla antigua ya comentada |
| Bajo | `models/maintenance_planned_activity.py` + `views/maintenance_planned_activity.xml` | Import comentado en `models/__init__.py:3`; vista no está en `__manifest__.py` → funcionalidad completa inalcanzable | — | Decidir: terminar de cablear o eliminar ambos ficheros — ver §5 |
| Bajo | `models/leulit_wizard_add_task_request.py:17-23` y `models/leulit_wizard_create_maintenance_request.py:17-23` | Bucle idéntico de 5 líneas duplicado en ambos wizards | — | Extraer a un método común (p.ej. en `project.task` o un mixin) |
| Bajo | `report/ir_actions_report.xml:4` | xmlid `paperformat_A4_landscape_19022026_1553` rompe la convención `leulit_YYYYMMDD_HHMM` usada en el resto del módulo | — | Cosmético, sin acción obligatoria |

## 3. Hallazgos críticos/altos en detalle

### C1 — `onchange_item_job_card` pisa la lógica de `leulit_taller` (Crítico)

`leulit_taller/models/project_task.py:186-199` ya define:

```python
@api.onchange('item_job_card_id')
def onchange_item_job_card(self):
    tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
    if self.item_job_card_id:
        self.maintenance_equipment_id = self.item_job_card_id.equipamiento_id
        self.name = self.item_job_card_id.descripcion
        self.solucion_defecto = self.item_job_card_id.solucion          # <-- se pierde
        self.production_lot_id = self.item_job_card_id.equipamiento_id.production_lot or False
        self.type_maintenance = self.item_job_card_id.type_maintenance
        self.ata_ids = self.item_job_card_id.ata_ids
        self.certificacion_ids = self.item_job_card_id.certificacion_ids
        self.tipos_actividad = self.item_job_card_id.tipos_actividad
        self.manuales_ids = self.item_job_card_id.manual_id
        self.tag_ids = tag_id
```

`leulit_actividad_taller/models/project_task.py:7-26` redefine **el mismo modelo y el
mismo nombre de método**:

```python
class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = "project.task"

    @api.onchange('item_job_card_id')
    def onchange_item_job_card(self):
        tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
        if self.item_job_card_id:
            self.write({
                'maintenance_equipment_id' : self.item_job_card_id.equipamiento_id.id,
                'name' : self.item_job_card_id.descripcion,
                'production_lot_id' : self.item_job_card_id.equipamiento_id.production_lot.id,
                'type_maintenance' : self.item_job_card_id.type_maintenance,
                'ata_ids' : self.item_job_card_id.ata_ids.ids,
                'certificacion_ids' : self.item_job_card_id.certificacion_ids.ids,
                'manuales_ids' : self.item_job_card_id.manual_id.ids,
                'tag_ids': tag_id.ids,
                'tipos_actividad': self.item_job_card_id.tipos_actividad.ids
            })
```

Odoo construye la clase final del modelo combinando las clases `_inherit` de todos los
módulos instalados; cuando dos módulos definen un **atributo/método con el mismo nombre**,
la resolución normal de Python (`getattr`) solo ve uno: el del módulo que queda más
"derivado" en el MRO. Como `leulit_actividad_taller` depende de `leulit_taller`
(`__manifest__.py:9-12`) se carga después, así que su `onchange_item_job_card` sustituye
por completo al de `leulit_taller` — no se llama a `super()`, no se combinan ambos.

Efecto: `solucion_defecto` deja de autorrellenarse al elegir un item de job card. No hay
excepción ni aviso — es un regreso de funcionalidad completamente silencioso. El resto de
campos coincide por casualidad (mismos valores), lo que hace el bug aún más difícil de
detectar en pruebas superficiales.

**Fix propuesto** (dentro de este módulo, sin tocar `leulit_taller`):

```python
@api.onchange('item_job_card_id')
def onchange_item_job_card_actividad_taller(self):
    if self.item_job_card_id:
        self.tag_ids = self.tag_ids | self.env['project.tags'].search(
            [('name', '=', 'Tareas de mantenimiento')], limit=1)
        self.tipos_actividad = self.item_job_card_id.tipos_actividad
```

Es decir: renombrar el método (para no pisar al de `leulit_taller`) y quedarse solo con lo
que este módulo aporta de verdad (`tipos_actividad`, y la unión de tags en vez de
sustituirlos — ver duda en §5). Todo lo demás (`maintenance_equipment_id`, `name`,
`production_lot_id`, `type_maintenance`, `ata_ids`, `certificacion_ids`, `manuales_ids`)
ya lo hace `leulit_taller` y no debe repetirse.

Nota adicional (anti-patrón, no bloqueante): usar `self.write({...})` dentro de un
`@api.onchange` es contrario a la guía oficial de Odoo (se recomienda asignación directa
de campos o `self.update(vals)`); no he podido verificar en este entorno si esto llega a
lanzar una excepción sobre un registro nuevo (`NewId`) sin guardar — lo dejo en §5 como
punto a confirmar en pruebas reales, pero recomiendo eliminarlo igualmente al aplicar el
fix de arriba.

### S1 — Acceso CRUD sin restricción a datos regulatorios (Alto, seguridad)

`security.xml:4-22` da `perm_read/create/write/unlink = 1` a `leulit.RBase` para:
- `leulit.item_experiencia_mecanico` — registro de experiencia 6/24 meses del mecánico,
  usado para el informe Part-145 "Registro Experiencia 6/24 meses" (ref. M.O.E. 3.19,
  ES.145.173, ver `report/leulit_experiencia.xml`).
- `leulit.tipo_actividad_mecanico` — catálogo cuyos valores (`'Supervise'`, `'CRS'`,
  `'FOT'`, `'SGH'`, `'R/I'`, `'TS'`, `'MOD'`, `'REP'`, `'INSP'`, `'Training'`, `'Perform'`)
  se comparan **por string literal** en `models/leulit_item_experiencia_mecanico.py:64` y
  `models/leulit_item_experiencia_mecanico.py:155`.

He grepeado el resto del repo (`ir.rule`, menús con `groups`) y no existe ninguna
restricción adicional sobre estos 3 modelos — el acceso es tan amplio como el XML lo
declara. Dado que por `CLAUDE.md` casi cualquier rol funcional encadena hasta `RBase`, esto
equivale en la práctica a "cualquier empleado autenticado".

Impacto doble:
1. Cualquier empleado puede crear/editar/borrar registros de experiencia usados en
   auditorías Part-145 desde la vista `tree editable="bottom"` sin trazabilidad de
   aprobación adicional.
2. Cualquier empleado puede renombrar o borrar un `tipo_actividad_mecanico` (p.ej. "CRS"),
   lo que rompe silenciosamente `get_activity_to_report()` y `run_upd_datos_actividad()`
   (dejan de marcar la columna correspondiente, sin error).

**Fix propuesto**: restringir `perm_write`/`perm_unlink` (y quizá `perm_create`) a un
grupo más específico que `RBase` — candidatos naturales en este repo son
`leulit.RCAMO_base` (ya usado en `leulit_taller` para operaciones equivalentes, p.ej.
`project_task.py:133` `unlink()`) o un grupo de calidad. **Esta es una decisión de
negocio que no puedo tomar por lectura de código — ver §5.**

### S2 — HTML de usuario sin sanear en un informe `wkhtmltopdf` (Alto, seguridad)

`report/leulit_experiencia.xml:432-436`:

```xml
<span style="...">
    <t t-out="o.remarks"/>
</span>
```

`o.remarks` es un `fields.Html` (`models/leulit_item_experiencia_mecanico.py:30`),
editable por cualquier `RBase` (ver S1) desde la vista `tree` (`views/
leulit_item_experiencia_mecanico.xml:22`, sin widget `html` — el valor se guarda tal cual
se escriba). `t-out` no escapa contenido que Odoo ya considera "seguro" (campos `Html`
se marcan `Markup` y `t-out` los vuelca crudo, igual que `t-raw`).

Riesgo: cualquier `RBase` puede insertar `<img src="http://.../beacon">` (SSRF/beacon
saliente desde el servidor que ejecuta `wkhtmltopdf`) o, si el binario `wkhtmltopdf` del
contenedor no está invocado con `--disable-local-file-access` (no he podido comprobarlo
sin acceso al entorno — Odoo 17 fija estos flags internamente, no vía `odoo.conf`),
`<img src="file:///etc/passwd">` para intentar filtrar ficheros del servidor dentro del
PDF generado. Como mínimo, permite romper el maquetado del informe regulatorio con HTML/
CSS arbitrario.

**Fix propuesto**: cambiar a `<t t-esc="o.remarks"/>` si el campo no necesita formato
enriquecido, o sanitizar el HTML al guardar (Odoo ya sanea `Html` fields por defecto con
`sanitize=True`, que es el valor por defecto — **duda**: no se ha desactivado
explícitamente aquí, así que es posible que el saneado estándar de Odoo ya mitigue el
vector de `<script>`/`<img onerror>` pero no necesariamente `<img src="file://...">`; ver
§5). Como medida independiente, restringir quién puede escribir `remarks` (ligado a S1).

### A1 — Crash por `AttributeError`/`ValueError` al imprimir el informe (Alto)

`models/leulit_wizard_report_experiencia.py:29,49`:

```python
company_icarus = self.env['res.company'].search([('name','like','Icarus')])
...
datos = {
    'logo_ica': company_icarus.logo_reports.decode(),
    ...
}
```

- Si ninguna compañía coincide, `company_icarus` es un recordset vacío;
  `company_icarus.logo_reports` en un recordset vacío devuelve `False`, y `False.decode()`
  lanza `AttributeError: 'bool' object has no attribute 'decode'` — el usuario ve un error
  técnico en vez de un mensaje claro.
- Si coincide más de una compañía (`like` es un substring match, sin `limit=1`),
  `company_icarus.logo_reports` sobre un recordset multi-registro lanza
  `ValueError: ... expected singleton`.

**Fix propuesto**:

```python
company_icarus = self.env['res.company'].search([('name', 'like', 'Icarus')], limit=1)
if not company_icarus or not company_icarus.logo_reports:
    raise UserError('No se ha encontrado el logo de la compañía Icarus para generar el informe.')
datos = {
    'logo_ica': company_icarus.logo_reports.decode(),
    ...
}
```

### A2/A3/A4 — Robustez del ORM en `leulit_item_experiencia_mecanico.py` (Alto, código actualmente no alcanzable)

Ver tabla §2. Los tres viven dentro de `run_upd_datos_actividad` / 
`run_upd_acc_analytic_line_requests`, que confirmo por grep global que **no tienen ningún
llamador en todo el repo** (ni botón, ni cron, ni server action, ni otro módulo). Es decir,
hoy no son explotables/ejecutables desde la UI — pero el código existe, se puede invocar
manualmente (shell, `ir.cron` futuro, botón que se añada más adelante) y arrastra bugs
reales si se activa tal cual está. Los detallo igualmente porque el enunciado pide cubrir
"errores/bugs" y "rendimiento" del código presente, no solo el alcanzable.

## 4. Plan de acción (orden sugerido de ejecución)

1. **[Crítico]** `models/project_task.py` — renombrar `onchange_item_job_card` para no
   pisar al de `leulit_taller`; dejar solo la lógica propia de este módulo (tipos_actividad
   + tag), sin duplicar el resto de campos. Confirmar con el usuario si el reseteo de
   `tag_ids` debe seguir sustituyendo o debe unir (ver duda §5).
2. **[Alto/seguridad]** `security.xml` — acordar con el usuario el grupo correcto para
   `leulit.item_experiencia_mecanico` y `leulit.tipo_actividad_mecanico` (ver duda §5) y
   ajustar `perm_write`/`perm_unlink`.
3. **[Alto/seguridad]** `report/leulit_experiencia.xml:434` — cambiar `t-out` por `t-esc`
   salvo que el usuario confirme que `remarks` necesita HTML enriquecido; en ese caso,
   documentar por qué se asume seguro.
4. **[Alto]** `models/leulit_wizard_report_experiencia.py` — añadir `limit=1` + guarda
   antes de `.decode()`.
5. **[Bajo→decisión]** Decidir el destino de `upd_acc_analytic_line_requests` /
   `upd_datos_actividad` / `get_data_to_report` (cablear o eliminar) — si se decide
   cablear, aplicar entonces los fixes A2/A3/A4 de la tabla; si se elimina, se resuelven
   solos.
6. **[Bajo→decisión]** Decidir el destino de `models/maintenance_planned_activity.py` +
   `views/maintenance_planned_activity.xml` (terminar de cablear o eliminar).
7. **[Medio]** `views/leulit_wizard_report_experiencia.xml` — marcar `mecanico_id`,
   `from_date`, `to_date` como `required`, o validar explícitamente en Python.
8. **[Medio]** `models/leulit_item_experiencia_mecanico.py` — sustituir `_logger.error`
   por `_logger.info`/`debug` en los mensajes de traza (líneas 98, 100, 125, 129, 131, 280).
9. **[Medio]** `report/leulit_experiencia.xml` — borrar el bloque comentado (líneas 1-263)
   y dejar un único `t-call` a `experiencia_mecanico_report_css`.
10. **[Bajo]** Extraer a un helper común el bucle duplicado de
    `leulit_wizard_add_task_request.py` / `leulit_wizard_create_maintenance_request.py`.

## 5. Dudas / no verificable sin entorno

Preguntas que requieren una decisión de negocio o una comprobación en un Odoo real — no
las he cerrado por mi cuenta:

1. **Grupo de acceso correcto para `leulit.item_experiencia_mecanico` /
   `leulit.tipo_actividad_mecanico`** (hallazgo S1). ¿Debe seguir siendo `RBase` (todo
   empleado) o restringirse a CAMO/calidad (`RCAMO_base` u otro grupo existente)? Es un
   registro con valor regulatorio Part-145, pero desconozco si en la operativa real de
   Helipistas cualquier mecánico rellena su propia experiencia (lo cual justificaría un
   acceso amplio a `create`, pero no necesariamente a `unlink`/editar registros ajenos).

2. **Semántica de `self.tag_ids = tag_id` en el onchange** (hallazgo M1/C1): ¿es
   intencional que al elegir un item de job card se **sustituyan** todos los tags de la
   tarea por únicamente "Tareas de mantenimiento" (perdiendo tags manuales previos), o
   debería ser una unión (`self.tag_ids | tag_id`)? El mismo patrón de sustitución ya
   existe en `leulit_taller/models/project_task.py:199`, así que podría ser una regla de
   negocio deliberada replicada a propósito — no lo he asumido.

3. **`t-out` sobre `remarks` (hallazgo S2)**: no puedo comprobar sin un Odoo real si el
   campo `Html` se está guardando con el saneado por defecto de Odoo (`sanitize=True`) o
   si en algún punto se desactiva; tampoco puedo comprobar con qué flags exactos invoca
   este contenedor a `wkhtmltopdf` (si `--disable-local-file-access` está activo). Ambas
   cosas solo se confirman con acceso al proceso de generación de PDF en marcha.

4. **Anti-patrón `self.write()` dentro de `@api.onchange`** (nota en C1): no he podido
   verificar en Odoo 17 real si esto llega a lanzar una excepción sobre una tarea nueva
   (`NewId`, aún no guardada) al pasar por el `write()` sobreescrito de
   `leulit_taller/models/project_task.py:294` (que compara `job_card_id` antes/después).
   Como el fix de C1 elimina el `write()`, esto queda resuelto de forma incidental, pero
   recomiendo probarlo manualmente en el entorno de pruebas antes de dar el fix por
   cerrado.

5. **Destino de `models/maintenance_planned_activity.py`** (hallazgo bajo): ¿fue
   deshabilitado deliberadamente (import comentado, vista fuera del manifest) por una
   incompatibilidad conocida, o quedó a medias? No hay ningún comentario en el código que
   lo explique.

6. **Destino de `upd_acc_analytic_line_requests` / `upd_datos_actividad` /
   `get_data_to_report`**: código huérfano sin llamador en todo el repo. ¿Estaba previsto
   engancharlos a un botón/cron que nunca se añadió, o son restos de una iteración
   anterior del informe (coincide con que `get_data_to_report` es el que usaba la
   plantilla vieja, ahora comentada)?
