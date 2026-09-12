# Revisión de código — `addons/leulit_camo/`

Fecha: 2026-09-10
Alcance: todos los ficheros del addon (`__manifest__.py`, `models/leulit_camo_worker.py`,
`security.xml`, `menu.xml`, `views/leulit_camo_worker.xml`, `views/project_task.xml`).
Sin entorno Odoo disponible: todo lo aquí afirmado se justifica por lectura de código,
imports, `_inherits`/`depends` y comparación con el patrón hermano
`leulit_taller/models/leulit_mecanico.py` (mismo autor/plantilla, mismo `_inherits`).

## 1. Resumen ejecutivo

- **Crítico: 1** — borrado en cascada del `res.partner` compartido al hacer `unlink()`
  de `leulit.camo_worker`, combinado con permiso de borrado abierto a `leulit.RBase`.
- **Alto: 3** — permisos CRUD completos sin `ir.rule` sobre datos PII/regulatorios;
  campo `user_id` no-`store`d con búsqueda O(n) en Python; falta de constraint que
  evite fichas CAMO duplicadas por contacto.
- **Medio: 2** — posible `ValueError` en el compute `_userId` si un contacto tiene
  más de un usuario activo; campos de emergencia que probablemente queden siempre
  vacíos para contactos sin usuario Odoo.
- **Bajo: 3** — imports muertos, clave de manifest obsoleta, atributo redundante en vista.

El módulo es pequeño (un solo modelo de negocio, `leulit.camo_worker`, más una
vista/acción sobre `project.task` ya existente en `leulit_taller`), pero comparte
el patrón `_inherits = {'res.partner': ...}` de otros modelos del proyecto
(`leulit.mecanico`, `leulit.piloto`, `leulit.alumno`, `leulit.operador`) sin replicar
las salvaguardas que esos modelos hermanos sí tienen (p.ej. `store=True` en el
`user_id` computado de `leulit.mecanico`).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_camo_worker.py:15,44` + `security.xml:11` | `unlink()` de `leulit.camo_worker` borra en cascada el `res.partner` delegado (comportamiento estándar de `_inherits` en Odoo) | Un usuario con `leulit.RBase` (rol muy extendido, ver `CLAUDE.md`) borra una ficha CAMO; si ese mismo `res.partner` es también piloto, proveedor o contacto de otro módulo, su identidad desaparece de todo el ERP | Quitar `perm_unlink` a `RBase` y/o sobrescribir `unlink()` en el modelo para bloquear o redirigir a archivado (`active=False`) |
| Alto | `security.xml:4-12` | Única regla de acceso: CRUD completo (incl. `unlink`) para `leulit.RBase`, sin `ir.rule` de fila, sobre datos PII y regulatorios (dirección, VAT, contacto de emergencia, RGA/PRA, certificaciones) | Cualquier empleado con `RBase` (prácticamente todos, según `CLAUDE.md`) puede leer/editar/borrar fichas de personal CAMO | Confirmar con el usuario si procede restringir a un grupo CAMO específico (pregunta abierta, ver sección 5) |
| Alto | `models/leulit_camo_worker.py:25-43` | `user_id` es `compute` **sin** `store=True`, con `search='_search_user_id'` que hace `self.search([])` (carga TODAS las fichas) y luego, por cada una, `worker.partner_id.user_ids` (N+1 queries) para montar el dominio `in` | Cualquier búsqueda/filtro por "Usuario" en la vista, o un dominio `[('user_id', ...)]` desde otro sitio | Añadir `store=True` (como hace `leulit_mecanico.py:31`) y eliminar `_search_user_id`, o al menos sustituir el bucle Python por una consulta agregada |
| Alto | `models/leulit_camo_worker.py:44` | No hay `_sql_constraints` que impida dos `leulit.camo_worker` para el mismo `partner_id` | Se crean dos fichas CAMO para el mismo contacto con datos RGA/PRA/certificaciones distintos y contradictorios | `_sql_constraints = [('partner_uniq', 'unique(partner_id)', 'Ya existe un trabajador CAMO para este contacto.')]` |
| Medio | `models/leulit_camo_worker.py:20-24` | `item.user_id = item.partner_id.user_ids` asigna un recordset potencialmente multi-registro a un campo Many2one | Un `res.partner` queda vinculado a más de un `res.users` activo (login duplicado/heredado) → `ValueError` de la ORM al no aceptar >1 registro en un Many2one | `item.user_id = item.partner_id.user_ids[:1]` (o `fields.first(...)`) |
| Medio | `models/leulit_camo_worker.py:46-47` | `emergency_contact_empl`/`emergency_phone_empl` son `related` a través de `user_id.employee_id`; sólo se rellenan si el contacto CAMO tiene además un `res.users` con `hr.employee` | Un certificador/mecánico CAMO que es solo `res.partner` (sin login Odoo) verá siempre vacía la pestaña "Emergencia" | Confirmar si es diseño intencional (fuente única en RRHH) o debería ser `Char` editable como en `leulit_mecanico.py:34-35` (pregunta abierta, sección 5) |
| Bajo | `models/leulit_camo_worker.py:3-7` | Imports sin usar: `tools`, `registry`, `exceptions`, `AccessError`, `RedirectWarning`, `ValidationError`, `datetime`, `_logger`, `utilitylib`, `_` | — | Eliminar imports no usados |
| Bajo | `__manifest__.py:20` | `"css": []` es una clave de manifest obsoleta desde Odoo 8+/assets bundles | — | Eliminar la clave |
| Bajo | `views/leulit_camo_worker.xml:31` | `readonly="1"` explícito sobre un campo `compute` sin `inverse` (ya es readonly implícitamente) | — | Cosmético, se puede dejar o quitar por claridad |

## 3. Hallazgos críticos/altos desarrollados

### C1 — Borrado en cascada del `res.partner` compartido (CRÍTICO)

```python
# models/leulit_camo_worker.py
class LeulitCamoWorker(models.Model):
    _name           = "leulit.camo_worker"
    _inherits       = {'res.partner': 'partner_id'}
    ...
    partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto',
                                  required=True, ondelete='cascade')
```
```xml
<!-- security.xml -->
<record id="leulit_20240613_1308_access_permission" model="ir.model.access">
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

En Odoo, el `unlink()` genérico de un modelo con `_inherits` borra también el
registro del modelo padre delegado (`res.partner` en este caso) una vez borrado
el hijo — es el comportamiento documentado de `_inherits`, no algo específico de
este módulo. `res.partner` es una entidad compartida en todo el ERP (puede ser
piloto en `leulit.vuelo`, contacto comercial, proveedor de `leulit_almacen`,
etc.). Con `perm_unlink=1` para `leulit.RBase` — un grupo que, según el propio
`CLAUDE.md` del proyecto, es heredado por prácticamente cualquier rol
privilegiado — cualquier empleado puede borrar una ficha CAMO y, con ella, el
`res.partner` subyacente, con efectos en cascada fuera del control de este
módulo (fallos de integridad referencial o borrados adicionales según los
`ondelete` de esas otras relaciones).

Nótese que el propio proyecto ya es consciente de este tipo de problema: el
modelo `leulit.documento` (`leulit/models/leulit_documento.py:42-47`)
sobrescribe `unlink()` explícitamente para evitar adjuntos huérfanos al
borrar. `leulit.camo_worker` no tiene ninguna salvaguarda equivalente.

**Fix propuesto (dentro del alcance del módulo):**
```python
def unlink(self):
    # Evitar que borrar la ficha CAMO borre en cascada el res.partner
    # compartido (puede ser piloto, proveedor, contacto comercial, etc.
    # en otros módulos). Preferir archivar.
    raise UserError(_("No se puede eliminar una ficha de trabajador CAMO; "
                       "archívela (desmarque 'Active') en su lugar."))
```
o, alternativamente, restringir `perm_unlink` a un grupo específico en
`security.xml` en vez de `leulit.RBase`. Cuál de las dos opciones (o ambas)
es la deseada depende de una decisión de negocio — ver sección 5.

### A1 — Permisos CRUD completos sin `ir.rule` sobre datos sensibles (ALTO)

```xml
<record id="leulit_20240613_1308_access_permission" model="ir.model.access">
    <field name="name">LeulitCamoWorker</field>
    <field name="model_id" ref="model_leulit_camo_worker"/>
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```
Es la única regla de acceso del módulo. No hay `ir.rule` de fila. El modelo
expone (vía `_inherits`) dirección, VAT, teléfono, y (vía `related`) contacto
y teléfono de emergencia del empleado, además de campos propios del dominio
CAMO (`rga`, `pra`, `certificaciones_ids`, fechas de certificador). El mismo
patrón exacto existe en `leulit_taller/security.xml:67-75` para
`leulit.mecanico`, así que no es una desviación nueva introducida por este
módulo — pero sigue siendo una superficie de acceso amplia para datos de
personal regulados por Parte-145/CAMO. Se traslada como pregunta abierta en
la sección 5 en vez de decidir un fix unilateral.

### A2 — `user_id` no-`store`d + búsqueda O(n) en Python (ALTO)

```python
@api.depends('partner_id')
def _userId(self):
    for item in self:
        item.user_id = item.partner_id.user_ids

def _search_user_id(self, operator, value):
    # Buscar workers por su user_id
    all_workers = self.search([])
    matching_ids = []
    for worker in all_workers:
        if worker.partner_id and worker.partner_id.user_ids:
            user_id = worker.partner_id.user_ids.id if worker.partner_id.user_ids else False
            if operator == '=' and user_id == value:
                matching_ids.append(worker.id)
            ...
    return [('id', 'in', matching_ids)]

user_id = fields.Many2one(compute='_userId', search='_search_user_id',
                           string='Usuario', comodel_name='res.users')
```
Comparar con el modelo hermano `leulit_taller/models/leulit_mecanico.py:31`:
```python
user_id = fields.Many2one(compute=_userId, string='Usuario',
                           comodel_name='res.users', store=True)
```
`leulit.mecanico` resuelve el mismo caso (usuario derivado del contacto)
almacenando el compute, lo que lo convierte en una columna SQL real,
indexable y filtrable sin código adicional. `leulit_camo_worker.py` en su
lugar reimplementa la búsqueda a mano: `self.search([])` trae **todas** las
fichas CAMO activas a memoria y, por cada una, accede a
`worker.partner_id.user_ids` (una query adicional por ficha, patrón N+1) sólo
para construir un `[('id', 'in', [...])]`. Además, al no estar almacenado,
cualquier dominio o `order_by` con ruta punteada (`user_id.name`, etc.) sobre
este modelo fallará porque la ORM no puede hacer el JOIN SQL implícito a
través de un campo no almacenado.

Con el volumen de personal CAMO de este operador (decenas, no miles de
fichas) el impacto práctico hoy es bajo, pero es un anti-patrón claro y sin
motivo aparente frente a la alternativa ya usada en el propio proyecto.

**Fix propuesto:**
```python
user_id = fields.Many2one(compute='_userId', string='Usuario',
                           comodel_name='res.users', store=True)
```
y eliminar `_search_user_id` por completo (ya no hace falta).

### A3 — Sin constraint de unicidad `partner_id` (ALTO)

```python
partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto',
                              required=True, ondelete='cascade')
```
Nada impide crear dos `leulit.camo_worker` para el mismo `partner_id`, cada
uno con su propio `rga`/`pra`/`certificaciones_ids`/fechas de certificador
potencialmente distintos y contradictorios entre sí (los dos serían
"la ficha CAMO de la misma persona").

**Fix propuesto:**
```python
_sql_constraints = [
    ('partner_uniq', 'unique(partner_id)',
     'Ya existe un trabajador CAMO para este contacto.'),
]
```

## 4. Plan de acción (orden de ejecución sugerido)

1. **[Crítico]** `security.xml` + `models/leulit_camo_worker.py` — decidir y
   aplicar la salvaguarda contra el borrado en cascada del `res.partner`
   (restringir `perm_unlink`, sobrescribir `unlink()`, o ambas). Requiere
   decisión de negocio previa (sección 5, pregunta 1).
2. **[Alto]** `models/leulit_camo_worker.py:43` — añadir `store=True` a
   `user_id` y eliminar `_search_user_id` (líneas 25-40). Cambio de esquema
   (nuevo campo almacenado) → requiere `./upd_module.sh leulit_camo dev
   --stop` al desplegar.
3. **[Alto]** `models/leulit_camo_worker.py:44` — añadir
   `_sql_constraints` de unicidad sobre `partner_id`. También requiere
   `--stop` (constraint SQL nueva); antes de desplegar en `prod`, comprobar
   si ya existen duplicados en datos reales (si los hay, la migración
   fallará y habrá que resolverlos a mano primero).
4. **[Alto]** `security.xml:4-12` — pendiente de decisión de negocio
   (sección 5, pregunta 2) sobre si restringir el grupo de acceso.
5. **[Medio]** `models/leulit_camo_worker.py:20-24` — blindar `_userId`
   contra el caso de >1 usuario activo (`item.partner_id.user_ids[:1]`).
   Cambio de solo lógica Python, sin DDL → sin `--stop`.
6. **[Medio]** `models/leulit_camo_worker.py:46-47` — pendiente de decisión
   de negocio (sección 5, pregunta 3) sobre el diseño de los campos de
   emergencia.
7. **[Bajo]** `models/leulit_camo_worker.py:3-7` — limpiar imports sin usar.
8. **[Bajo]** `__manifest__.py:20` — quitar la clave `"css": []` obsoleta.
9. **[Bajo]** `views/leulit_camo_worker.xml:31` — opcional, quitar
   `readonly="1"` redundante.

## 5. Dudas / no verificable sin entorno — necesitan tu decisión

1. **Alcance del borrado (`unlink`) de `leulit.camo_worker` (hallazgo C1).**
   ¿Debe poder borrarse una ficha CAMO en absoluto, sabiendo que hoy eso
   arrastra el `res.partner` compartido? Propongo por defecto bloquear el
   `unlink()` y forzar archivado (`active=False`), pero es una decisión de
   negocio (afecta al flujo de baja de personal CAMO) que no puedo tomar por
   mi cuenta.
2. **Grupo de acceso (hallazgo A1).** ¿La intención es que cualquier
   `leulit.RBase` pueda leer/editar/borrar fichas de personal CAMO (como ya
   ocurre hoy con `leulit.mecanico` en `leulit_taller`), o este módulo
   debería tener un grupo más restringido dado que expone PII (dirección,
   VAT, contacto de emergencia) y datos regulatorios (RGA/PRA,
   certificaciones)? Si se decide restringir, hay que definir el nuevo
   grupo en `leulit/groups.xml` (fuera del alcance de este módulo según las
   convenciones del proyecto) antes de tocar `leulit_camo/security.xml`.
3. **Diseño de los campos de emergencia (hallazgo M2).** ¿Es intencional que
   `emergency_contact_empl`/`emergency_phone_empl` dependan de que el
   contacto CAMO tenga también un `res.users`+`hr.employee` (fuente única en
   RRHH), aun sabiendo que probablemente muchos certificadores/mecánicos
   CAMO no tengan login Odoo y por tanto la pestaña "Emergencia" les quede
   siempre vacía? El modelo hermano `leulit.mecanico` usa en su lugar campos
   `Char` editables directamente en la ficha.
4. **Escenario de `ValueError` en `_userId` (hallazgo M1).** No he podido
   confirmar sin base de datos real si actualmente existe algún
   `res.partner` con más de un `res.users` activo vinculado (login
   duplicado/heredado). Si no ocurre hoy, el bug es latente; si ocurre,
   probablemente ya esté rompiendo la apertura de esa ficha en producción.
   Recomiendo comprobarlo en el entorno de pruebas antes de decidir la
   prioridad real de este arreglo.
5. **Impacto real de la búsqueda O(n) (hallazgo A2).** No he encontrado
   ningún sitio del repo (fuera del propio módulo) que filtre o busque por
   `user_id` en `leulit.camo_worker`, así que hoy el único disparador
   conocido es un filtro manual en la propia vista de lista. El fix
   (`store=True`) es barato y sin trade-offs aparentes, así que lo mantengo
   en el plan de acción con prioridad alta aunque el impacto actual medido
   sea bajo.
