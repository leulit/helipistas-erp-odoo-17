# Revisión — `leulit_activity_date_history`

Revisión estática (sin entorno Odoo real) de todo el addon: `__manifest__.py`,
`models/leulit_activity_date_history.py`, `models/mail_activity.py`,
`security.xml`, `views/leulit_activity_date_history.xml`, `views/mail_activity.xml`,
`menu.xml`.

Dependencias declaradas (`__manifest__.py`): `leulit`, `leulit_planificacion`, `mail`.

## 1. Resumen ejecutivo

9 hallazgos: **2 críticos**, **2 altos**, **3 medios**, **2 bajos**. Los dos
críticos son estructurales: el `ondelete='cascade'` en `activity_id` hace que
el propio historial desaparezca justo cuando una actividad se completa (se
pierde el dato que se supone hay que auditar), y `perm_write=1` para
`leulit.RBase` permite que cualquier usuario del ERP reescriba a posteriori
el historial vía RPC/modo desarrollador, anulando su valor como auditoría.
Los altos son un falso positivo en la detección de cambio de fecha por
comparar tipos distintos (`date` vs valor crudo de `vals`), y una posible
fuga de confidencialidad entre módulos al no heredar el control de acceso de
`mail.activity` sobre el registro origen.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_activity_date_history.py:18` | `activity_id` con `ondelete='cascade'` | Cualquier actividad que se marca como "Hecha" (comportamiento estándar de `mail.activity`, módulo `mail` core) borra el `mail.activity`, y por cascada, TODO su historial de cambios de fecha | `ondelete='set null'` + campo no `required`, conservando los campos `related(store=True)` ya desnormalizados |
| Crítico | `security.xml:9-10` | `perm_write=1` (y `perm_create=1` directo, no vía `sudo`) para `leulit.RBase` | Cualquier usuario con rol operativo (prácticamente todos, ver `CLAUDE.md`: RBase es la base de la jerarquía) edita un registro de historial por RPC/import/modo desarrollador, saltándose `edit="false"` de las vistas (una restricción solo de UI) | `perm_write=0`, `perm_create=0` para `RBase`; crear el registro con `sudo()` desde `mail_activity.py` |
| Alto | `models/mail_activity.py:21` | `record.date_deadline != vals['date_deadline']` compara un `date` Python con el valor crudo de `vals` (con frecuencia `str` cuando la llamada viene del cliente web/JSON-RPC) | Un `write()` que reenvía `date_deadline` sin cambio real de valor pero con tipo distinto genera una fila de historial falsa ("cambió" cuando no cambió) | Normalizar ambos lados con `fields.Date.to_date(...)` antes de comparar |
| Alto | `security.xml:7` + `menu.xml:11` | Sin `ir.rule`, cualquier `RBase` puede leer el histórico (incluido `res_name`, `res_model`, `nota`) de actividades ligadas a registros a los que ese usuario no tendría acceso (HR, calidad/seguridad, CAMO...) | Usuario sin acceso a `hr.employee`/`mgmtsystem.action` etc. abre el menú del módulo y ve fecha/nota de actividades de esos modelos | Restringir `group_id` a un grupo más acotado, o añadir `ir.rule` que replique el control de acceso de `mail.activity` sobre `res_model`/`res_id` (ver duda al final) |
| Medio | `models/mail_activity.py:20-27` | `create()` en bucle, una fila a la vez, dentro de `for record in self` | `write()` masivo sobre muchos `mail.activity` a la vez (p.ej. replanificación en bloque desde `leulit_planificacion`) genera N `INSERT` + N cómputos de los `related(store=True)` en vez de 1 `create()` por lote | Acumular en `vals_list` y hacer un único `self.env[...].create(vals_list)` fuera del bucle |
| Medio | `models/leulit_activity_date_history.py:35-36` | `fecha_nueva` es `required=True`; si `vals['date_deadline']` llega `False`/`None` mientras `record.date_deadline` tiene valor, el `create()` de historial revienta con `ValidationError` antes de llegar a `super().write()` | Un `write({'date_deadline': False, ...})` sobre una actividad con fecha previa (solo alcanzable si algo bypassea el `required=True` que ya tiene `date_deadline` en `mail.activity` core) aborta el `write()` completo, incluidos otros campos del mismo `vals` | Guardar el histórico solo si `vals['date_deadline']` es también verdadero; si no, registrar el "borrado de fecha" con semántica propia o simplemente omitir la fila |
| Medio | `models/leulit_activity_date_history.py:14-19` | `activity_id` (Many2one) sin `index=True` explícito | Tabla que crece con cada cambio de fecha y se consulta por `activity_id` en cada apertura del popup de actividad (`date_history_ids`) | Añadir `index=True` al campo |
| Bajo | `models/leulit_activity_date_history.py:49`, `views/leulit_activity_date_history.xml:18,44`, `views/mail_activity.xml:19` | Campo `nota` expuesto en las 3 vistas pero nunca escrito por ningún código del módulo (todas las vistas son `create="false"`/`edit="false"`) | Ningún flujo actual permite rellenarlo — campo muerto que confunde al usuario ("¿por qué siempre está vacío?") | Cablearlo (p.ej. pedir motivo al reprogramar manualmente) o eliminarlo |
| Bajo | (módulo completo) | Sin carpeta `tests/` | Un módulo cuyo único propósito es integridad de datos de auditoría no tiene ningún `TransactionCase` que fije el comportamiento esperado (p.ej. "mismo valor no genera fila") | Añadir 2-3 tests mínimos: cambio real crea 1 fila, mismo valor no crea fila, borrado de actividad no debería perder el histórico |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Crítico] `ondelete='cascade'` borra el historial justo cuando más importa

`models/leulit_activity_date_history.py:14-19`:

```python
activity_id = fields.Many2one(
    comodel_name='mail.activity',
    string='Actividad',
    required=True,
    ondelete='cascade'
)
```

El comportamiento estándar de `mail.activity` en Odoo (módulo core `mail`,
fuera del alcance de este addon y **no verificable leyendo este repo**
porque `mail` no está vendorizado en `addons/`) es que al marcar una
actividad como "Hecha" (`action_feedback`/`_action_done()`), el registro
`mail.activity` se elimina (se convierte en un `mail.message` de log). Con
`ondelete='cascade'`, ese `unlink()` se propaga por FK y borra en cascada
**todas** las filas de `leulit.activity.date.history` de esa actividad — es
decir, el historial de "cuántas veces se pospuso esta fecha límite" se
pierde exactamente en el momento en que la actividad se cierra, que es
cuando más útil sería revisarlo (auditoría post-mortem, CAMO, calidad...).
Esto vacía de contenido el propósito declarado del módulo para toda
actividad que llegue a completarse con normalidad.

**Fix propuesto** (dentro del alcance del módulo; requiere migración de
esquema porque cambia una columna `NOT NULL` + el tipo de `ondelete`, por
tanto `./upd_module.sh leulit_activity_date_history <entorno> --stop`):

```diff
     activity_id = fields.Many2one(
         comodel_name='mail.activity',
         string='Actividad',
-        required=True,
-        ondelete='cascade'
+        required=False,
+        index=True,
+        ondelete='set null'
     )
```

Los campos `activity_type_id`, `res_model`, `res_name` ya son
`related(..., store=True)`: al ser un `SET NULL` a nivel de FK/SQL (no un
recompute vía ORM), el último valor almacenado en esas columnas **no se
borra** cuando `activity_id` pasa a `NULL` — así el historial sigue siendo
legible (qué tipo de actividad, qué registro, qué fechas) aunque la
actividad origen ya no exista. Si se prefiere no perder ni siquiera el
vínculo por id, una alternativa es guardar además `activity_id_int =
fields.Integer(...)` como copia no-FK del id original antes de que se
pierda la referencia.

### 3.2 [Crítico] El propio historial de auditoría es editable por cualquier usuario operativo

`security.xml:4-12`:

```xml
<record id="leulit_activity_date_history_access" model="ir.model.access">
    <field name="name">Histórico cambios fecha actividad</field>
    <field name="model_id" ref="model_leulit_activity_date_history"/>
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="0"/>
</record>
```

Según `CLAUDE.md` del proyecto, `leulit.RBase` es el grupo raíz del que
cuelgan por `implied_ids` prácticamente todos los roles funcionales del
ERP — es, en la práctica, "cualquier usuario autenticado con un rol de
negocio". Con `perm_write=1` a nivel de `ir.model.access`, ese universo de
usuarios puede modificar `fecha_anterior`, `fecha_nueva`, `fecha_cambio`,
`usuario_id` y `nota` de cualquier fila del histórico. Las vistas
(`views/leulit_activity_date_history.xml`) ponen `edit="false"` en el
`<tree>` y el `<form>`, pero eso es **solo una restricción de UI** — no
protege frente a una llamada XML-RPC/JSON-RPC externa, la función de
importación estándar de Odoo sobre el modelo, o el toggle de "editar" que
el modo desarrollador ofrece sobre formularios marcados `edit="false"`.
Resultado: un registro pensado como pista de auditoría inmutable puede
falsificarse después de los hechos.

Además, el hecho de que `perm_create=1` sea necesario para `RBase` viene de
que `mail_activity.py:22` crea el registro de historial en el `env` del
usuario que hace el `write()`, no vía `sudo()` — así que hoy el permiso de
creación está acoplado al de un usuario cualquiera, en vez de acotarse a la
propia lógica del módulo.

**Fix propuesto:**

`security.xml`:
```diff
-        <field name="perm_read" eval="1"/>
-        <field name="perm_create" eval="1"/>
-        <field name="perm_write" eval="1"/>
-        <field name="perm_unlink" eval="0"/>
+        <field name="perm_read" eval="1"/>
+        <field name="perm_create" eval="0"/>
+        <field name="perm_write" eval="0"/>
+        <field name="perm_unlink" eval="0"/>
```

`models/mail_activity.py`:
```diff
-                    self.env['leulit.activity.date.history'].create({
+                    self.env['leulit.activity.date.history'].sudo().create({
                         'activity_id': record.id,
                         'fecha_anterior': record.date_deadline,
                         'fecha_nueva': vals['date_deadline'],
                         'usuario_id': self.env.uid,
                     })
```

Con esto, ningún usuario (ni siquiera vía RPC) puede crear/editar filas de
historial directamente; solo se generan como efecto secundario controlado
del `write()` sobre `mail.activity`, con `sudo()` cubriendo el permiso de
creación que ya no depende del rol del usuario que dispara el cambio.

### 3.3 [Alto] Falso positivo en la detección de cambio por comparación de tipos distintos

`models/mail_activity.py:18-27`:

```python
def write(self, vals):
    if 'date_deadline' in vals:
        for record in self:
            if record.date_deadline and record.date_deadline != vals['date_deadline']:
                self.env['leulit.activity.date.history'].create({
                    'activity_id': record.id,
                    'fecha_anterior': record.date_deadline,
                    'fecha_nueva': vals['date_deadline'],
                    'usuario_id': self.env.uid,
                })
    return super(MailActivity, self).write(vals)
```

`record.date_deadline` es siempre un objeto `datetime.date` de Python (ya
convertido por el ORM al leer el recordset). `vals['date_deadline']`, en
cambio, es el valor **crudo** tal como llega a `write()`: cuando la llamada
viene del cliente web (JSON-RPC) suele ser una cadena `'YYYY-MM-DD'`;
cuando viene de código Python de otro módulo puede ser un `date` o una
cadena, según cómo se haya construido el `vals`. `date(2026,9,10) !=
'2026-09-10'` es siempre `True` en Python aunque representen la misma
fecha, así que cualquier `write()` que reenvíe `date_deadline` con el mismo
valor pero como cadena genera una fila de historial "fantasma" (aparenta un
cambio que no existió). Esto es especialmente probable en escrituras que
vienen de otros módulos del propio repo con varios campos a la vez (p.ej.
flujos de `leulit_planificacion` que recalculan y reescriben actividades),
no solo desde el formulario de usuario.

**Fix propuesto:**

```diff
+from odoo import fields as odoo_fields
...
     def write(self, vals):
         if 'date_deadline' in vals:
+            nueva_fecha = fields.Date.to_date(vals['date_deadline'])
             for record in self:
-                if record.date_deadline and record.date_deadline != vals['date_deadline']:
+                if record.date_deadline and record.date_deadline != nueva_fecha:
                     self.env['leulit.activity.date.history'].create({
                         'activity_id': record.id,
                         'fecha_anterior': record.date_deadline,
-                        'fecha_nueva': vals['date_deadline'],
+                        'fecha_nueva': nueva_fecha,
                         'usuario_id': self.env.uid,
                     })
         return super(MailActivity, self).write(vals)
```

(`fields.Date.to_date` ya está disponible vía el import existente `from
odoo import models, fields, api`, no hace falta un import nuevo — se deja
arriba solo para señalar de dónde sale.)

### 3.4 [Alto] Posible fuga de confidencialidad entre módulos (visibilidad no heredada de `mail.activity`)

`security.xml:7` (`group_id` = `leulit.RBase`) + `menu.xml:11`
(`groups="leulit.RBase"`), sin ningún `ir.rule` en el módulo.

`mail.activity` en Odoo core aplica su propio filtrado de acceso basado en
si el usuario tiene permiso de lectura sobre el `res_model`/`res_id` al que
está ligada la actividad (comportamiento estándar y documentado de
`mail.activity`, pero **no verificable leyendo este repo**: el módulo
`mail` no está vendorizado en `addons/`, así que esta afirmación se marca
también en la sección de dudas). `leulit.activity.date.history`, al ser un
modelo nuevo e independiente, no hereda ese filtrado: solo tiene el ACL
plano de `RBase`. Cualquier usuario con ese grupo (la base de casi todos
los roles, ver `CLAUDE.md`) puede abrir el menú
`leulit_activity_date_history_menuitem` y leer `res_model`, `res_name`,
`fecha_anterior`, `fecha_nueva` y `nota` de actividades vinculadas a
**cualquier** modelo del ERP — incluidos los de módulos con datos sensibles
(`hr.employee`, `mgmtsystem.action` de calidad/seguridad, `leulit.camo`,
etc.), aunque ese usuario no tenga acceso al registro original.

**No se propone un fix cerrado aquí** porque replicar en un `ir.rule` (que
solo admite dominios declarativos) el filtrado dinámico que `mail.activity`
hace en Python no es directo, y decidir qué grupo debería tener acceso a
este histórico es una decisión de producto/negocio del proyecto. Ver
pregunta en la sección 5.

## 4. Plan de acción priorizado

1. **[Crítico]** `security.xml` + `models/mail_activity.py` — cerrar
   `perm_write`/`perm_create` de `RBase` a 0 y mover la creación del
   histórico a `sudo()` (§3.2). Sin cambio de esquema, se puede desplegar
   con `./upd_module.sh leulit_activity_date_history <entorno>` (solo XML +
   Python, sin `ALTER TABLE`).
2. **[Crítico]** `models/leulit_activity_date_history.py:14-19` — cambiar
   `activity_id` a `ondelete='set null'` / `required=False` (§3.1).
   Cambio de esquema → `./upd_module.sh leulit_activity_date_history
   <entorno> --stop`.
3. **[Alto]** `models/mail_activity.py:18-27` — normalizar tipos antes de
   comparar (`fields.Date.to_date`) para eliminar los falsos positivos
   (§3.3).
4. **[Alto]** `security.xml` / `menu.xml` — decidir con el usuario el
   alcance de visibilidad correcto (grupo más acotado y/o `ir.rule`) antes
   de tocar nada (§3.4, ver pregunta en §5).
5. **[Medio]** `models/mail_activity.py:18-27` — sustituir el `create()`
   en bucle por un único `create(vals_list)` batched.
6. **[Medio]** `models/leulit_activity_date_history.py:35-36` — no crear
   fila de historial si `vals['date_deadline']` es falsy, para no romper un
   `write()` legítimo por un `required=True` en cascada.
7. **[Medio]** `models/leulit_activity_date_history.py:14-19` — añadir
   `index=True` a `activity_id` (se puede incluir en el mismo cambio de
   esquema del punto 2, ahorrando un segundo `--stop`).
8. **[Bajo]** Decidir sobre el campo `nota`: cablearlo a un flujo real o
   eliminarlo de las 3 vistas que lo muestran vacío.
9. **[Bajo]** Añadir 2-3 tests (`tests/test_activity_date_history.py`,
   `TransactionCase`) que fijen el comportamiento de los puntos 3 y 6.

## 5. Dudas / no verificable sin entorno

- **Comportamiento real de `mail.activity` al completar una actividad**
  (`_action_done()`/`action_feedback()` del módulo core `mail`): la base
  del hallazgo crítico §3.1 (que la actividad se `unlink()`ea al marcarse
  como hecha) es el comportamiento estándar y ampliamente documentado de
  Odoo, pero el módulo `mail` no está vendorizado en este repo
  (`addons/third-party-addons/` solo trae OCA/community) y no hay Odoo
  instalado en este entorno, así que no he podido leer el código fuente
  exacto de la versión 17.0 Community para confirmarlo al 100%. Recomiendo
  confirmarlo en el entorno Docker de pruebas antes de aplicar el fix:
  crear una actividad, cambiarle la fecha (para generar una fila de
  historial), marcarla como "Hecho" y comprobar si la fila desaparece.
- **Filtrado de acceso propio de `mail.activity` por `res_model`/`res_id`**
  (base del hallazgo §3.4): mismo motivo — comportamiento estándar
  conocido de Odoo pero no verificable leyendo este repo. Si se confirma
  que existe, el `ir.rule` a replicar tendría que decidirse con el usuario
  (qué modelos/roles deben quedar filtrados).
- **Qué grupo debería tener acceso real al histórico** (§3.4 / plan de
  acción punto 4): esto es una decisión de producto (¿solo mandos/CAMO
  quality? ¿todo RBase pero solo de sus propios registros?) que no me
  corresponde cerrar por mi cuenta — lo dejo como pregunta abierta para el
  usuario.
- **Frecuencia real de `write()` masivos con `date_deadline` en `vals`
  desde otros módulos** (relevante para la severidad exacta del hallazgo de
  rendimiento §3, punto 5 del plan): he revisado los `write()`/lecturas de
  `date_deadline` sobre `mail.activity` visibles en
  `addons/leulit_planificacion` y no he encontrado un caso claro de
  escritura masiva hoy, pero no puedo descartar que exista en otros módulos
  del monorepo fuera del alcance de esta revisión (limitada a
  `addons/leulit_activity_date_history/`) ni en flujos futuros.
