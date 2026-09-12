# Revisión de código — `leulit_trabajador_externo`

Revisión estática (sin entorno Odoo disponible) de todos los ficheros del módulo:
`__init__.py`, `__manifest__.py`, `groups.xml`, `menu.xml`, `views/project_task.xml`.
El módulo no tiene modelos Python, controladores, wizards, cron ni reports — es
puramente declarativo (grupos + menú + acción sobre `project.task`, modelo definido en
`leulit_tarea`/`project`, fuera de alcance).

## 1. Resumen ejecutivo

**5 hallazgos**: 2 críticos, 0 altos, 3 medios, 4 bajos (9 en total). Los dos críticos
son los que importan: (a) los grupos propios del módulo (`RTExterno_base`,
`RTExterno_gestor`) no tienen ningún `ir.model.access` sobre `project.task`, así que un
usuario cuyo único rol relevante sea uno de estos recibe `AccessError` al pulsar el único
menú del módulo; (b) el dominio de la acción filtra por `user_id`, campo que muy
probablemente no existe en `project.task` en Odoo 17 (el módulo hermano `leulit_tarea`
usa `user_ids` para el mismo propósito). Ambos, si se confirman en un entorno real, dejan
el módulo completamente no funcional para su único caso de uso.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | groups.xml (todo el fichero) / ausencia de `security/ir.model.access.csv` | `RTExterno_base` y `RTExterno_gestor` no tienen ningún `ir.model.access` que les conceda permisos sobre `project.task` | Usuario con grupo `RTExterno_base` (y sin `project.group_project_user` ni `leulit_tarea.RT_base`/`RT_administrador` asignados por fuera de este módulo) abre el menú "Externo > Tareas" | Añadir `security/ir.model.access.csv` (o `security.xml` con `ir.model.access`) concediendo permisos sobre `project.task` a `RTExterno_base`/`RTExterno_gestor`, y añadirlo a `data` en el manifest |
| Crítico | views/project_task.xml:9 | El dominio de la acción usa `('user_id', '=', uid)`; `project.task` en Odoo 17 usa `user_ids` (Many2many "Asignados"), no `user_id` como Many2one — ver `leulit_tarea/views/project_task.xml:169` que usa `('user_ids', 'in', uid), ...)` para el mismo caso de uso | Cualquier usuario con acceso al menú "Tareas" de este módulo abre la acción | Cambiar el dominio a `[('user_ids', 'in', uid)]` (verificar en un shell Odoo real antes de aplicar — ver sección de dudas) |
| Medio | groups.xml:15-19 | `RTExterno_gestor` está definido (implica `RTExterno_base`) pero no se usa en ningún `menuitem`, `ir.rule` ni `ir.model.access` del módulo ni del resto del repo | Un "Gestor" externo tiene exactamente los mismos (ningún) permisos que un "Trabajador" — el rol no aporta nada distinto hoy | Definir qué debe poder hacer `RTExterno_gestor` de más (p.ej. ver tareas de todo su equipo, no solo `uid`) y modelarlo con una segunda acción/dominio o `ir.rule`; requiere decisión de negocio, ver Dudas |
| Medio | views/project_task.xml:5-10 | La acción reutiliza sin restricción las vistas estándar (tree/kanban/form/calendar) de `project.task`, heredadas en cascada de `project` + `leulit_tarea`, para un perfil de confianza reducida (trabajador externo) | Un trabajador externo con acceso ya corregido (hallazgo crítico #1) vería en el formulario/kanban de tarea todos los campos estándar (fechas, timesheets, stage global, etc.), no solo lo pensado para un externo | Evaluar si hace falta una vista `form`/`tree` propia con `inherit_id` que oculte campos internos; decisión de producto, no asumida aquí |
| Medio | groups.xml:10-13 | `RTExterno_base` no tiene `implied_ids` hacia `base.group_user` (Usuario interno) | Si a un trabajador externo se le asigna solo `RTExterno_base` (sin marcarlo aparte como usuario interno), no puede ni entrar al backend | Patrón ya existente en todo el repo (`RT_base`, `REscuela_base`, `RActividad_user`... tampoco implican `base.group_user`), así que no es un fallo exclusivo de este módulo — se señala como recordatorio, no como fix aislado |
| Bajo | menu.xml:5 y 11 | Los IDs `leulit_20200818_1028_menuitem` y `leulit_20200907_1307_menuitem` coinciden literalmente con IDs usados en `addons/leulit/menu.xml:38` y `addons/leulit_tarea/menu.xml:5` respectivamente | Ninguno en producción (Odoo namespacea por módulo: `leulit.leulit_20200818_1028_menuitem` vs `leulit_trabajador_externo.leulit_20200818_1028_menuitem`), pero confunde al grep/lectura y sugiere copy-paste sin renombrar | Renombrar los IDs propios a algo descriptivo (`menu_trabajador_externo_root`, `menu_trabajador_externo_tareas`) |
| Bajo | __manifest__.py:4 | `"description": "\n    "` — descripción vacía | — | Rellenar con una descripción real del módulo |
| Bajo | views/project_task.xml:3 | Espacio final tras `<data>` | — | Cosmético |
| Bajo | menu.xml (todo) | Ausencia de `security/` como carpeta dedicada (todo va en `groups.xml`/`menu.xml` sueltos en la raíz), inconsistente con el resto de módulos `leulit_*` que sí tienen `security.xml`/`security/ir.model.access.csv` | — | Ligado al hallazgo crítico #1: al crear el fichero de accesos, seguir la convención de carpeta `security/` del resto del repo |

## 3. Hallazgos críticos desarrollados

### 3.1 Sin `ir.model.access` para los grupos del módulo (Crítico)

**Evidencia.** El módulo define dos grupos propios:

```xml
<!-- groups.xml -->
<record id="RTExterno_base" model="res.groups">
    <field name="name">Trabajador</field>
    <field name="category_id" ref="t_externo_rol_category"/>
</record>

<record id="RTExterno_gestor" model="res.groups">
    <field name="name">Gestor</field>
    <field name="implied_ids" eval="[(4, ref('RTExterno_base'))]"/>
    <field name="category_id" ref="t_externo_rol_category"/>
</record>
```

y usa `RTExterno_base` para mostrar el único menú del módulo:

```xml
<!-- menu.xml -->
<menuitem
    id="leulit_20200907_1307_menuitem"
    name="Tareas"
    parent="leulit_20200818_1028_menuitem"
    sequence="10"
    action="leulit_20230908_1214_action"
    groups="RTExterno_base"
/>
```

El módulo **no incluye ningún `security/ir.model.access.csv` ni `ir.model.access` en
XML**, ni referencia ninguno vía `depends` que cubra específicamente a estos dos grupos.
Grepeando todo el repo, `RTExterno_base`/`RTExterno_gestor` no aparecen en ningún
`ir.model.access` ni `ir.rule` de ningún módulo. Los únicos `ir.model.access` sobre
`project.task` en el repo (`addons/leulit_tarea/security.xml:3-29`) están scoped a
`project.group_project_user`, `leulit_tarea.RT_base` y `leulit_tarea.RT_administrador` —
ninguno de los cuales es implicado por `RTExterno_base`/`RTExterno_gestor`.

**Consecuencia.** Un usuario cuyo perfil de "trabajador externo" se construya
únicamente con los grupos de este módulo (el escenario que el propio módulo da a
entender que es su caso de uso) verá el menú "Externo > Tareas" — la visibilidad del
`menuitem` la controla `groups="RTExterno_base"`, que se cumple — pero al abrirlo Odoo
evaluará `ir.model.access` para `project.task` y, al no encontrar ninguna fila que
aplique a ninguno de sus grupos, lanzará un `AccessError` ("No tiene acceso a este
documento..."). El módulo, tal como está, solo funciona si el administrador asigna
*además* — por fuera de este módulo y sin que nada lo documente ni lo fuerce — uno de
los grupos de `leulit_tarea` o `project.group_project_user`.

**Fix propuesto** (nuevo fichero `security/ir.model.access.csv`, añadido al manifest):

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_project_task_rtexterno_base,project_task_rtexterno_base,project.model_project_task,RTExterno_base,1,0,0,0
access_project_task_rtexterno_gestor,project_task_rtexterno_gestor,project.model_project_task,RTExterno_gestor,1,1,0,0
```

Los valores de `perm_write`/`perm_create` de ejemplo son una propuesta razonable (lectura
para "Trabajador", lectura+escritura para "Gestor", sin alta/baja para ninguno) —
**la decisión de qué CRUD corresponde a cada rol es de negocio y debe confirmarla el
usuario**, ver sección de dudas. Y en `__manifest__.py`:

```python
"data": [
    "security/ir.model.access.csv",
    "groups.xml",
    "views/project_task.xml",
    "menu.xml",
],
```

### 3.2 Dominio de la acción filtra por un campo que probablemente no existe (Crítico)

**Evidencia.**

```xml
<!-- views/project_task.xml -->
<record id="leulit_20230908_1214_action" model="ir.actions.act_window">
    <field name="name">Tareas TE</field>
    <field name="res_model">project.task</field>
    <field name="view_mode">tree,kanban,form,calendar</field>
    <field name="domain">[('user_id', '=', uid)]</field>
</record>
```

`project.task` no se redefine en este módulo (el modelo vive en `project`, extendido por
`leulit_tarea/models/project_task.py`, que solo hace `_inherit = ["project.task"]` sin
añadir campos `user_id`/`user_ids`). El propio `leulit_tarea` resuelve exactamente el
mismo caso de uso — "mis tareas" — usando `user_ids`, no `user_id`:

```xml
<!-- addons/leulit_tarea/views/project_task.xml:169 -->
<field name="domain">[('user_ids', 'in', uid),('project_borrador', '=', False)]</field>
```

En Odoo 17 el campo estándar de `project.task` para el/los asignados es `user_ids`
(Many2many, "Asignados a"); no he encontrado en ningún fichero de este repo (ni en los
módulos de terceros vendorizados que heredan `project.task`) una definición de un campo
`user_id` sobre este modelo. El código fuente del módulo `project` en sí no está
vendorizado en este repo (es un módulo stock de la distribución Odoo), así que no puedo
leer literalmente su definición de campos — ver nota en "Dudas".

**Consecuencia si se confirma.** Al evaluar el dominio de la acción, Odoo lanzaría un
error de campo inválido sobre `project.task` (típicamente `ValueError` /
`psycopg2.errors.UndefinedColumn` según el punto en que se resuelva el dominio), y la
acción — el único punto de entrada funcional del módulo — no cargaría para ningún
usuario.

**Fix propuesto:**

```diff
- <field name="domain">[('user_id', '=', uid)]</field>
+ <field name="domain">[('user_ids', 'in', uid)]</field>
```

## 4. Plan de acción priorizado

1. **(Crítico)** Confirmar en un entorno Odoo real (shell/`fields_get`) si `project.task`
   tiene campo `user_id` o solo `user_ids` en esta instalación 17.0, y corregir
   `views/project_task.xml:9` en consecuencia.
2. **(Crítico)** Añadir `security/ir.model.access.csv` (o `security.xml`) con las filas
   de `ir.model.access` para `RTExterno_base`/`RTExterno_gestor` sobre `project.task`,
   registrarlo en `data` del manifest, y probar login con un usuario que solo tenga estos
   grupos.
3. **(Medio)** Decidir y documentar qué diferencia a `RTExterno_gestor` de
   `RTExterno_base` (alcance de datos, permisos de escritura) e implementarlo (nueva
   acción/dominio o `ir.rule`), o eliminar el grupo si no se va a usar.
4. **(Medio)** Revisar con el usuario si las vistas estándar de `project.task`
   (formulario/kanban) exponen campos que no deberían ser visibles para un trabajador
   externo, y si hace falta una vista propia vía `inherit_id`/`xpath`.
5. **(Bajo)** Renombrar los IDs de `menu.xml` para evitar la coincidencia literal con
   IDs de `leulit`/`leulit_tarea` (namespacing correcto igualmente, pero confuso a la
   lectura).
6. **(Bajo)** Rellenar `description` en `__manifest__.py` y mover los ficheros de
   seguridad a una carpeta `security/` para alinear con la convención del resto de
   módulos `leulit_*`.

## 5. Dudas / no verificable sin entorno

- **Campo `user_id` vs `user_ids` en `project.task` (hallazgo 3.2).** No puedo confirmar
  con certeza absoluta que `user_id` no exista como campo en `project.task` en esta
  instalación 17.0, porque el módulo `project` no está vendorizado en este repo (es
  stock de la distribución Odoo) y no hay forma de ejecutar `fields_get()`. La evidencia
  disponible en el repo (uso consistente de `user_ids` en `leulit_tarea`, ningún módulo
  de terceros que redefina `user_id` en `project.task`) apunta con fuerza a que el
  dominio actual está mal, pero pido confirmación antes de tratarlo como 100% cerrado —
  un `docker exec ... odoo shell` con
  `env['project.task'].fields_get(['user_id','user_ids'])` lo resuelve en segundos.
- **Alcance de `RTExterno_gestor`.** No hay ninguna pista en el código (ni comentarios,
  ni historial visible desde este módulo) de qué debía hacer distinto un "Gestor" de un
  "Trabajador" — no lo asumo ni propongo un dominio concreto sin que el usuario lo
  confirme. Esto **no** es el patrón "self record only sobre `hr.employee`" advertido en
  `CLAUDE.md` (aquí el modelo es `project.task`, no `hr.employee`, y no hay ningún
  `ir.rule` en este módulo todavía), pero cualquier `ir.rule`/dominio que se añada para
  diferenciar el rol debería revisarse igualmente por si en algún punto se apoya en
  `hr.employee` u otro modelo compartido ERP-wide antes de cerrarlo.
- **Permisos exactos de `perm_write`/`perm_create` en el fix del hallazgo 3.1.** Propongo
  valores razonables (lectura para Trabajador, lectura+escritura para Gestor, sin
  create/unlink para ninguno) pero es una decisión de negocio del usuario, no la doy por
  cerrada.
- **Quién asigna hoy `project.group_project_user` / `leulit_tarea.RT_base` a los
  trabajadores externos existentes**, si es que el módulo lleva tiempo en producción y
  "funciona" — si es así, la causa sería exactamente que alguien complementa manualmente
  los grupos de este módulo con los de `leulit_tarea`/`project` por fuera de lo que el
  módulo declara, lo cual confirmaría el hallazgo crítico #1 como deuda oculta en vez de
  bug latente sin explotar.
