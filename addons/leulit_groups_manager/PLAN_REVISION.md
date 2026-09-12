# Revisión de código — `leulit_groups_manager`

Revisión estática (sin entorno Odoo local ejecutable). Módulo Odoo 17 Community,
`depends: ['base', 'web']` — **no depende de `leulit`** (confirmado en `__manifest__.py:21-24`),
por lo que no hereda directamente la lógica de `RBase`/`ir.rule` del módulo fundacional, pero sí
la **manipula genéricamente** desde el wizard de copia (ver hallazgo #4), lo cual es relevante dado
el incidente documentado en el `CLAUDE.md` del proyecto (commit `e85e8f1a`, regla `RBase` +
`hr.employee`).

No hay controladores HTTP, cron jobs (`ir.cron`) ni informes (`ir.actions.report`) en este módulo —
solo modelos, 3 wizards `TransientModel`, vistas y seguridad.

## 1. Resumen ejecutivo

**12 hallazgos**: 0 críticos, **4 altos**, **4 medios**, **4 bajos**. Los más graves son un heurístico
de clasificación (`is_leulit_group`) que **no detecta la mayoría de los grupos reales del proyecto**
(incluido `RBase`), un patrón N+1 de queries sin límite en el árbol completo de menús, un grupo de
seguridad (`group_groups_manager`) definido pero **nunca usado** que otorga admin total bajo un
nombre engañoso, y un wizard de copia masiva de `ir.rule`/menús/permisos que no muestra qué se va a
modificar antes de ejecutar cuando `copy_all=True` (por defecto).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Alto | `models/res_groups.py:73-85` | `_compute_is_leulit_group` compara `category_id.name.lower()` contra una lista fija de palabras que no cubre la mayoría de categorías reales del proyecto | Abrir "Gestión de Grupos" (filtro por defecto `is_leulit_group=True`) — `RBase`, `RBase_employee`, `RBase_hide`, grupos `RComercial_*`, `RContabilidad_*`, `RolIT_*` no aparecen | Derivar de `category_id.id`/módulo de origen (xmlid) en vez de un substring hardcoded del nombre de categoría, o ampliar+mantener la lista junto con las categorías reales |
| Alto | `models/menu_list_wizard.py:54-80` | `_build_menu_tree_html` hace 1 `search()` de `ir.ui.menu` por cada nodo del árbol, de forma recursiva, sin batching | Ejecutar "Ver Menús Accesibles" en una instalación con ~350 módulos de terceros → cientos/miles de queries síncronas en un solo compute HTML | Cargar todo `ir.ui.menu` (o vía `child_of`) en una sola query, construir un dict `parent_id -> children` en memoria y recorrerlo |
| Alto | `security/groups.xml:4-9` | Grupo `group_groups_manager` se define pero no se usa en ningún `groups=`, `ir.model.access` ni vista del módulo (grep confirmado); vía `implied_ids` concede `base.group_system` completo | Un administrador asigna "Groups Manager" pensando que es un permiso acotado ("gestionar grupos y permisos visualmente") y en realidad otorga Administrador de Sistema completo | Eliminar el grupo si no se usa, o si se pretende usar, acotar sus permisos reales a los wizards de este módulo y documentar explícitamente que implica `group_system` |
| Alto | `models/group_copy_wizard.py` (todo el wizard) + `views/group_copy_wizard_views.xml:35,50,65,83` | Con `copy_all=True` (valor por defecto, ver `views/group_copy_wizard_views.xml:118-121`) nunca se listan los elementos concretos antes de ejecutar; además `user_ids`/`menu_ids`/`access_ids`/`rule_ids` no llevan `domain` restringido a `available_*_ids`, por lo que el modo "selección específica" permite elegir *cualquier* `ir.rule`/menú/usuario del sistema, no solo los del grupo origen | Un admin ejecuta "Copiar → Reglas de Registro" con `copy_all=True` sobre un grupo con muchas `ir.rule` (p.ej. si en el futuro se reutiliza sobre modelos como `hr.employee`) sin ver antes la lista — riesgo de repetir el incidente documentado en `CLAUDE.md` (RBase + hr.employee, commit `e85e8f1a`) | Mostrar siempre la lista a copiar (quitar el `invisible="copy_all"` del notebook o añadir un paso de confirmación/preview), y añadir `domain="[('id','in', available_user_ids)]"` (y equivalentes) a los 4 campos de selección |
| Medio | `models/group_copy_wizard.py:219-224,240-245,298-303` | El mensaje de éxito usa `len(users_to_copy)`/`len(menus_to_copy)`/`len(rules_to_copy)` en vez de contar lo realmente escrito; el `if ... not in ...` del bucle salta elementos ya presentes pero no descuenta del contador | Copiar "Usuarios" de un grupo con 10 miembros, 3 ya en el grupo destino → solo se escriben 7, pero el mensaje dice "10 usuarios han sido añadidos" | Llevar un contador incremental dentro del bucle (como ya se hace correctamente en `_copy_access_rights` con `created_count`) |
| Medio | `models/group_copy_wizard.py:215-217,236-238,294-296` | Bucle `for x in recordset: if cond: x.write(...)` en vez de un único `write()` batched sobre todo el recordset (`(4, id)` es idempotente, no hace falta el `if`); en `_copy_access_rights` además N `search()` + N `create()` individuales | Copiar 200 usuarios/menús/reglas → 200 UPDATEs/queries individuales en vez de 1 | `to_copy.write({'groups_id': [(4, target.id)]})` en una sola llamada; para `_copy_access_rights`, precalcular `existing_model_ids` con una sola query y usar `create()` con lista de dicts |
| Medio | `models/res_groups.py:51-59` | `_compute_group_category` declara dependencia de `'name'` pero nunca lo usa; el `help` del campo dice "Extracted from category_id or module name" pero el fallback siempre es el literal `'Sin Categoría'` | Un grupo sin `category_id` (p.ej. creado manualmente) siempre cae en el cajón "Sin Categoría" pese a lo que indica la ayuda del campo | Implementar el fallback real (extraer de `name` o de `category_id` vía xmlid/módulo), o corregir el `help`/quitar `'name'` de `@api.depends` si no se va a usar |
| Medio | `views/menu.xml:12-30` | `menu_users_groups_management`, `menu_groups_catalog`, `menu_user_group_matrix` no llevan `groups="base.group_system"` propio (solo lo tiene el `menu_groups_manager_root` padre); las acciones `ir.actions.act_window` asociadas tampoco declaran `groups_id` | Acceso directo a la URL de la acción (`/odoo/action-<id>`) bypassea el árbol de menús; el gate real depende únicamente de `ir.model.access` sobre `res.groups`/`res.users`, no verificable en este entorno sin leer el `ir.model.access.csv` del core (ver sección de dudas) | Añadir `groups="base.group_system"` explícito a cada `<menuitem>` y `groups_id` a cada `ir.actions.act_window`, como defensa en profundidad, igual que ya se hace en `menu_diagnose_menu_access`/`menu_group_copy_wizard` |
| Bajo | `models/group_copy_wizard.py:114` | `available_user_ids = wizard.source_group_id.users` no filtra usuarios inactivos/archivados (a diferencia de `_compute_users_count` en `res_groups.py:61-65`, que sí filtra `active`) | Copiar "Usuarios" con `copy_all=True` desde un grupo con ex-empleados archivados → se les añade el grupo destino aunque no puedan iniciar sesión | Filtrar `.filtered(lambda u: u.active)` si el objetivo es solo usuarios activos, o documentar que es intencional |
| Bajo | `models/menu_access_diagnosis_wizard.py:31-36` y `models/menu_list_wizard.py:47-52` | `_check_menu_access` duplicado idéntico en ambos wizards (violación DRY) | — (mantenibilidad) | Extraer a un método compartido, p.ej. en un `AbstractModel` mixin o como método de `res.groups`/`ir.ui.menu` |
| Bajo | `models/menu_access_diagnosis_wizard.py` (múltiples líneas), `models/menu_list_wizard.py`, `models/group_copy_wizard.py:142-143`, `models/res_users.py:68-71` | HTML construido con f-strings insertando `group.name`/`menu.name`/`user.name` sin escapar explícitamente | Un grupo/menú con un nombre malicioso (`<img src=x onerror=...>`) — mitigado en la práctica porque `fields.Html` sanitiza por defecto (`sanitize=True`) en Odoo 17, pero no verificable en este entorno sin ejecutar | Escapar explícitamente con `markupsafe.escape()` como defensa en profundidad, sin depender solo del sanitizado implícito del campo |
| Bajo | `security/ir_model_access.xml:6-25` | `access_res_groups_manager`/`access_res_users_manager` otorgan CRUD completo sobre `res.groups`/`res.users` a `base.group_system`, permiso que probablemente ya concede el `ir.model.access.csv` core de Odoo para ese mismo grupo | — (posible redundancia, no verificable sin leer el core, que no está en este repo) | Confirmar contra el core si son redundantes; si lo son, se pueden retirar sin pérdida de funcionalidad |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 `is_leulit_group` no detecta los grupos reales del proyecto (Alto)

`addons/leulit_groups_manager/models/res_groups.py:73-85`:

```python
@api.depends('name', 'category_id', 'category_id.name')
def _compute_is_leulit_group(self):
    """Identify Leulit custom groups"""
    for group in self:
        is_leulit = False
        if group.category_id:
            cat_name = group.category_id.name.lower()
            is_leulit = any(word in cat_name for word in [
                'leulit', 'operaciones', 'escuela', 'taller',
                'camo', 'parte 145', 'calidad', 'seguridad'
            ])
        group.is_leulit_group = is_leulit
```

Evidencia (`addons/leulit/groups.xml`, fuera de alcance pero consultado solo para verificar el
dato, no modificado): las categorías reales usadas por los grupos fundacionales son:

```
base_rol_category        -> name = "Rol Base"        (RBase, RBase_employee, RBase_hide, RDocumentos_responsable)
operaciones_rol_category -> name = "Rol Operaciones"  (ROperaciones_*)
taller_rol_category      -> name = "Rol Taller"
camo_rol_category        -> name = "Rol CAMO"
calidad_rol_category     -> name = "Rol Calidad"
comercial_rol_category   -> name = "Rol Comercial"
```

`"rol base".lower()` y `"rol comercial".lower()` no contienen ninguna de las palabras de la lista
(`'leulit'`, `'operaciones'`, ...) → `RBase`, `RBase_employee`, `RBase_hide`, `RComercial_*`,
`RContabilidad_*`, `RolIT_*` quedan clasificados como **NO Leulit**, pese a ser exactamente los
grupos que este módulo pretende resaltar. Como la acción principal del módulo
(`action_groups_enhanced`, `views/res_groups_views.xml:143-161`) abre por defecto con
`search_default_leulit_groups: 1`, un administrador que abra "Catálogo de Grupos" **no verá
`RBase` en la lista inicial**.

**Fix propuesto** (ejemplo, a validar con el usuario porque cambia el criterio de clasificación):

```python
@api.depends('category_id')
def _compute_is_leulit_group(self):
    for group in self:
        xmlid = group.get_external_id().get(group.id, '')
        module = xmlid.split('.')[0] if '.' in xmlid else ''
        group.is_leulit_group = module.startswith('leulit')
```

Esto identifica el grupo por el módulo que lo declaró (vía `ir.model.data`), no por texto libre de
la categoría, y es robusto frente a nuevas categorías/palabras.

### 3.2 N+1 sin límite en el árbol completo de menús (Alto)

`addons/leulit_groups_manager/models/menu_list_wizard.py:54-80`:

```python
def _build_menu_tree_html(self, html, menu, all_groups, level=0):
    ...
    child_menus = self.env['ir.ui.menu'].search([('parent_id', '=', menu.id)], order='sequence, name')
    for child_menu in child_menus:
        self._build_menu_tree_html(html, child_menu, all_groups, level + 1)
```

Para cada nodo del árbol se hace una query nueva. Con un ERP que vendoriza ~350 módulos
OCA/community (`CLAUDE.md` del proyecto), el árbol de `ir.ui.menu` puede tener varios cientos o
miles de nodos → el mismo número de queries síncronas dentro de un único compute (`@api.depends`
no-stored, se recalcula en cada lectura del campo).

**Fix propuesto**:

```python
@api.depends('user_id')
def _compute_menu_list_html(self):
    for wizard in self:
        ...
        all_menus = self.env['ir.ui.menu'].search([], order='parent_id, sequence, name')
        children_by_parent = {}
        for m in all_menus:
            children_by_parent.setdefault(m.parent_id.id, []).append(m)
        ...
        for root_menu in children_by_parent.get(False, []):
            wizard._build_menu_tree_html(html, root_menu, all_groups, children_by_parent, level=0)

def _build_menu_tree_html(self, html, menu, all_groups, children_by_parent, level=0):
    ...
    for child_menu in children_by_parent.get(menu.id, []):
        self._build_menu_tree_html(html, child_menu, all_groups, children_by_parent, level + 1)
```

Una sola query para todo el árbol, recorrido en memoria.

### 3.3 Grupo `group_groups_manager` sin uso, otorga admin completo (Alto)

`addons/leulit_groups_manager/security/groups.xml`:

```xml
<record id="group_groups_manager" model="res.groups">
    <field name="name">Groups Manager</field>
    <field name="category_id" ref="base.module_category_administration"/>
    <field name="comment">Can manage user groups and permissions visually</field>
    <field name="implied_ids" eval="[(4, ref('base.group_system'))]"/>
</record>
```

Grep exhaustivo confirma que `group_groups_manager` **no aparece en ningún otro fichero del
módulo** (ni `groups=` de menú, ni `group_id` de `ir.model.access`, ni vista, ni `implied_ids` de
otro grupo). Todos los permisos reales del módulo (`security/ir_model_access.xml`,
`security/wizards_access.xml`, todos los `<menuitem groups="...">`) apuntan directamente a
`base.group_system`, no a este grupo. Es decir: el grupo es efectivamente **código muerto**, salvo
que alguien lo asigne manualmente a un usuario desde Ajustes → Usuarios → Grupos, en cuyo caso ese
usuario se convierte silenciosamente en Administrador de Sistema completo (por `implied_ids`), pese
a que el nombre y el comentario ("Can manage user groups and permissions visually") sugieren un
alcance mucho más acotado.

**Fix propuesto**: si el grupo no tiene uso previsto, eliminarlo (`security/groups.xml`) junto con
la limpieza de datos en upgrade. Si se pretende usar como grupo de entrada acotado, no debe implicar
`base.group_system`; los `ir.model.access`/`menuitem` de este módulo deberían apuntar a
`group_groups_manager` en vez de a `base.group_system` directamente, y sus permisos deberían
limitarse a los modelos que gestiona este módulo, no a admin total. **Esto es una decisión de
producto/seguridad que no se puede tomar solo leyendo el código — queda documentada en la sección de
dudas.**

### 3.4 Copia masiva sin preview + sin domain en selección específica (Alto)

`addons/leulit_groups_manager/views/group_copy_wizard_views.xml:31` — el notebook con el detalle de
lo que se va a copiar solo se muestra si `copy_all` está desmarcado:

```xml
<notebook invisible="copy_all">
    ...
    <field name="user_ids" widget="many2many_tags">
    ...
    <field name="menu_ids">
    ...
    <field name="access_ids">
    ...
    <field name="rule_ids">
```

Y el valor por defecto de la acción es `copy_all=True` (`action_group_copy_wizard`,
`views/group_copy_wizard_views.xml:118-121`). Es decir: en el flujo por defecto, un administrador
pulsa "Copiar" viendo solo un contador (`stats_info`) y nunca la lista concreta de qué `ir.rule`,
menús o `ir.model.access` se van a modificar.

Además, ninguno de los 4 campos de selección específica tiene `domain`:

```xml
<field name="user_ids" widget="many2many_tags">        <!-- línea 35, sin domain -->
<field name="menu_ids">                                  <!-- línea 50, sin domain -->
<field name="access_ids">                                 <!-- línea 65, sin domain -->
<field name="rule_ids">                                    <!-- línea 83, sin domain -->
```

Con `copy_all=False`, el widget `many2many_tags`/lista permite elegir *cualquier* `res.users`,
`ir.ui.menu`, `ir.model.access` o `ir.rule` del sistema, no solo los que pertenecen al grupo origen
— contradice el propio `help` de los campos ("Usuarios/Menús/... específicos a copiar **del grupo
origen**").

Esto es relevante en este proyecto concreto porque el `CLAUDE.md` documenta un incidente real
(commit `e85e8f1a`, revertido) causado por una regla de `ir.rule` mal alcance sobre `hr.employee`
combinada con `RBase`. Una herramienta que permite "añadir grupo X a un conjunto de `ir.rule`" sin
mostrar antes cuáles son ni restringir cuáles se pueden elegir es exactamente el tipo de operación
que puede reproducir ese incidente.

**Fix propuesto**:
- Quitar `invisible="copy_all"` del `<notebook>`, o añadir un paso de confirmación que liste los
  elementos afectados antes de escribir.
- Añadir `domain="[('id','in', available_user_ids)]"` (y equivalentes para `menu_ids`, `access_ids`,
  `rule_ids`) a los 4 campos.

## 4. Plan de acción priorizado

1. **[Alto]** Corregir `_compute_is_leulit_group` (`models/res_groups.py:73-85`) — decidir con el
   usuario el criterio correcto (por módulo/xmlid vs. lista de palabras) antes de tocarlo, ya que
   cambia qué grupos se muestran por defecto en producción.
2. **[Alto]** Reescribir `_build_menu_tree_html`/`_compute_menu_list_html`
   (`models/menu_list_wizard.py:12-80`) para una sola query + recorrido en memoria.
3. **[Alto]** Decidir el propósito de `group_groups_manager` (`security/groups.xml`): eliminar si es
   código muerto, o acotar sus permisos si se va a usar — **requiere decisión del usuario**.
4. **[Alto]** En `group_copy_wizard` (`models/group_copy_wizard.py` +
   `views/group_copy_wizard_views.xml`): mostrar siempre la lista de elementos a copiar y añadir
   `domain` a `user_ids`/`menu_ids`/`access_ids`/`rule_ids`.
5. **[Medio]** Corregir el conteo en los mensajes de éxito de `_copy_users`/`_copy_menus`/
   `_copy_record_rules` (`models/group_copy_wizard.py`).
6. **[Medio]** Batching de escrituras/búsquedas en las 4 funciones `_copy_*`
   (`models/group_copy_wizard.py`).
7. **[Medio]** Implementar (o corregir el `help` de) el fallback de `_compute_group_category`
   (`models/res_groups.py:51-59`).
8. **[Medio]** Añadir `groups="base.group_system"` explícito a los 3 `<menuitem>` sin él y
   `groups_id` a sus `ir.actions.act_window` (`views/menu.xml:12-30`,
   `views/res_users_views.xml`, `views/res_groups_views.xml`).
9. **[Bajo]** Filtrar usuarios activos en `available_user_ids` si es el comportamiento deseado
   (`models/group_copy_wizard.py:114`).
10. **[Bajo]** Extraer `_check_menu_access` duplicado a un método compartido.
11. **[Bajo]** Escapar explícitamente los valores insertados en los campos `Html` construidos por
    f-string, como defensa en profundidad.
12. **[Bajo]** Verificar y, si procede, eliminar la redundancia en
    `security/ir_model_access.xml:6-25` frente al `ir.model.access.csv` core de `base`.

## 5. Dudas / no verificable sin entorno

- **`group_groups_manager` (hallazgo 3.3)**: no puedo determinar desde el código si este grupo se
  pretende asignar a alguien en producción o si es un resto de una iteración anterior del módulo. Es
  una decisión de producto/seguridad — **queda pendiente de que el usuario decida** (eliminarlo vs.
  acotarlo).
- **Redundancia de `ir.model.access.xml` frente al core** (`security/ir_model_access.xml:6-25`): el
  `ir.model.access.csv` de `base` no está en este repositorio (es código core de Odoo, no
  vendorizado), así que no puedo confirmar con certeza si `base.group_system` ya tiene CRUD completo
  sobre `res.groups`/`res.users` de forma nativa. Si es así, estos registros son redundantes pero
  inofensivos; si no, son necesarios. Solo se puede confirmar leyendo `ir.model.access.csv` del
  Odoo 17 instalado en el contenedor, o consultando `ir.model.access` vía el ORM en el entorno de
  pruebas (`docker exec ... odoo shell` o una lectura MCP contra el Odoo real).
- **Acceso real a `ir.rule` desde el wizard** (`_copy_record_rules`,
  `models/group_copy_wizard.py:127-129,284-303`): la lectura de `ir.rule` se hace vía `.sudo()`
  tanto en el compute como en la escritura, así que el acceso debería funcionar independientemente
  del `ir.model.access` del usuario sobre `ir.rule` — pero no puedo confirmar en runtime que no haya
  ningún efecto secundario (p.ej. un `ir.rule` con `active=False` que igualmente aparezca en
  `available_rule_ids` y se reactive/asocie sin que el admin lo note, ya que el dominio de búsqueda
  no filtra por `active`).
- **Sanitizado efectivo de los campos `Html` computados** (hallazgo "Bajo" de XSS): asumo que
  `fields.Html(sanitize=True)` (valor por defecto en Odoo 17, no hay `sanitize=False` explícito en
  ningún campo de este módulo) sanitiza también los valores asignados desde Python en un `compute`,
  no solo los que llegan desde el cliente web. No puedo ejecutar Odoo en este entorno para
  confirmarlo con un caso de prueba real (p.ej. un grupo con `name = '<img src=x onerror=alert(1)>'`
  y verificar el HTML final renderizado).
- **Efecto real de la falta de `groups=` en 3 `<menuitem>`** (hallazgo 8): no puedo confirmar en
  runtime si Odoo 17 oculta igualmente esos submenús por herencia del padre (`menu_groups_manager_root`,
  que sí tiene `groups="base.group_system"`) cuando se navega por el árbol normal de menús, ni cuál
  es el resultado exacto de acceder directamente a la URL de la acción (`/odoo/action-<id>`) sin
  pasar por el menú, sin una instancia Odoo corriendo contra la que probarlo.
