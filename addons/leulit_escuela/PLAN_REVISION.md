# Revisión de `leulit_escuela` — Odoo 17 Community

Revisión estática (sin entorno Odoo disponible — todo verificado leyendo código, imports, `_inherit`,
manifest y grep exhaustivo sobre el módulo). Alcance: **solo** `addons/leulit_escuela/`. Cuando un
hallazgo depende de código de otro módulo (`leulit`, `leulit_operaciones`, `leulit_planificacion`)
se señala pero no se toca.

## 1. Resumen ejecutivo

- **Críticos: 3** — falta total de `ir.rule` (alumnos con CRUD sobre datos de todos los demás
  alumnos), wizard "Histórico de Partes" roto por tipo de campo erróneo, wizard de vuelo que filtra
  con `sudo()` y vuelca el resultado (que bypasea las reglas de registro) en un `UserError` visible
  al usuario normal.
- **Altos: 5** — bug de variable shadowing que anula el filtro por alumno en el informe de prácticas
  firmado, `self.write()` en vez de `item.write()` en 2 de 3 implementaciones de `do_done_course`,
  crash garantizado en `get_alumnos_activos`, 3 threads en background con cursor sin cerrar y sin
  `try/except`, hardcode de margen (90 días) que ignora el campo configurable `margen_dy`.
- **Medios: 8** / **Bajos: 7** — antipatrón sistemático de `search([])` + bucle Python para computed
  `search=`, SQL por `.format()`/`%` en vez de parámetros, división por cero potencial, logging con
  `_logger.error` para trazas informativas, imports muertos, modelo duplicado/legacy sin aclarar
  vigencia.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `security.xml` (todo el fichero, ausencia de `ir.rule`) | Ningún modelo del módulo tiene record rule; todo el acceso son `ir.model.access` a `leulit.RBase`, que heredan prácticamente todos los empleados (incl. alumnos, ver `leulit_alumno.alta_alumno`) | Un alumno (grupo `REscuela_base` + `RBase`) accede al modelo `leulit.parte_escuela`/`leulit.alumno`/`leulit.rel_alumno_evaluacion` por cualquier vía que no sea el menú "Partes escuela (A)" (URL directa, XML-RPC, la propia acción sin dominio `leulit_20200908_1552_action`) y lee/edita/borra partes, notas y perfiles de **cualquier otro alumno** | Añadir `ir.rule` a nivel `leulit.RBase` que restrinja `leulit.parte_escuela`/`leulit.rel_alumno_evaluacion`/`leulit.alumno` a los propios registros del usuario cuando no tenga `REscuela_responsable`/`ROperaciones_gestor`, con bypass explícito para los grupos de gestión (mismo patrón `RBase`+bypass descrito en `CLAUDE.md`, aplicado con cuidado para no romper accesos legítimos de profesor/responsable) |
| Crítico | `models/leulit_informes_historial_popup.py:23` | `alumno_id` está tipado `comodel_name='leulit.piloto'` pero el único caller (`leulit_alumno.metodo_historial_a_ejecutar`, línea 177) pasa `default_alumno_id: self.id` de un **`leulit.alumno`** | Un usuario pulsa "Historial" desde la ficha de alumno → el wizard intenta poner por defecto un id de `leulit.alumno` en un M2O a `leulit.piloto`: o revienta por FK inexistente, o (peor) casualmente existe ese id en `leulit_piloto` y asocia el informe al piloto equivocado | Cambiar `comodel_name` a `'leulit.alumno'` y ajustar el dominio del `search()` en `leulit_informes_historial_popup.py:40-42` (ya usa `alumnos` que es un `leulit.alumno`, así que hoy es coherente con alumno, no con piloto) |
| Crítico | `models/leulit_vuelo.py:35-51,56-73,85-101` | El `UserError` de diagnóstico incluye resultados de `self.env['leulit.alumno'].sudo().search(...)` / `leulit.profesor.sudo().search(...)`, es decir, datos obtenidos **saltándose las reglas de registro del usuario actual**, mostrados literalmente en el mensaje de error | Cualquier usuario sin permisos para ver cierto alumno/profesor dispara el camino de error (falta verificado/alumno o profesor no resoluble) y ve en el propio diálogo de error IDs y nombres que sus reglas de acceso deberían ocultarle | Quitar las búsquedas `.sudo()` del mensaje de usuario; si se necesita para depuración, loguear con `_logger.debug/error` (sin `sudo` o solo en logs de servidor) y mostrar al usuario un mensaje corto sin datos con `sudo()` |

| Alto | `models/leulit_wizard_report_practicas_curso.py:39-40` | `for item in parte.rel_curso_alumno:` reutiliza el nombre `item` (ya usado por el `for item in self:` externo) y compara `item.alumno.id == item.alumno.id` — tautología siempre `True` | Se imprime el informe firmable de prácticas para un alumno con varios alumnos en el mismo parte de escuela: el filtro que debería restringir el sílabus/estado "verificado" al alumno del wizard nunca filtra, y el nombre final (`item.alumno.name`) puede quedar apuntando al último `rel_curso_alumno` recorrido en vez de al alumno del wizard | Usar `self.alumno.id == item.alumno.id` (igual que hace correctamente `leulit_wizard_report_teoricas_curso.py:40`) y renombrar la variable del bucle interno para no shadowear (p.ej. `for linea in parte.rel_curso_alumno:`) |
| Alto | `models/leulit_pf_accion_last_done.py:39,47` y `models/leulit_perfil_formacion_accion_last_done.py:110,117` | `do_done_course()` hace `self.write(...)` en vez de `item.write(...)` dentro de `for item in self:` | Si algún día se invoca `do_done_course()` sobre un recordset con más de un registro (server action, llamada RPC en lote, botón sobre selección múltiple), escribe `done_date`/`is_last` en **todos** los registros de `self`, no solo en `item` | `item.write({'done_date': ..., 'is_last': True})`, igual que la implementación correcta en `leulit_perfil_formacion_curso_last_done.py:56,64` |
| Alto | `models/leulit_rel_alumno_curso.py:82` | `item.fecha_finalizacion >= period_start` se evalúa **antes** que el `or item.fecha_finalizacion == False` del mismo `if`; cuando `fecha_finalizacion` es `False` (alumno activo, caso normal) Python compara `bool >= date` y lanza `TypeError` | Cualquier llamada a `get_alumnos_activos()` (método público, alcanzable por RPC aunque hoy no tenga caller interno) con al menos un alumno sin `fecha_finalizacion` | `if (item.fecha_finalizacion is False or item.fecha_finalizacion >= period_start):` |
| Alto | `models/leulit_alumno.py:545-548`, `models/leulit_parte_escuela.py:604-607`, `models/leulit_rel_parte_escuela_cursos_alumnos.py:137-139` | 3 métodos `run_*` lanzan un thread que abre `self.pool.cursor()` y nunca lo cierra, sin `try/except`, con `api.Environment.manage()` (no-op en Odoo ≥15) y sin `thread.daemon = True` | Cada ejecución de `sincronizar_horas`, `get_partes_error` o `upd_set_rel_vuelo` deja una conexión a Postgres abierta indefinidamente; si el bucle lanza una excepción a mitad, el cursor tampoco se cierra ni se hace rollback — fuga de conexiones acumulativa | Reescribir con el patrón correcto ya existente en `addons/leulit/models/res_partner.py:82-107` (`with registry(dbname).cursor() as new_cr:` + `try/except` + `thread.daemon = True`) |
| Alto | `models/leulit_perfil_formacion_accion_last_done.py:38` | `r = range(0, 90)` — hardcodea 90 días en vez de usar `pfc.margen_dy` (campo configurable, existe y se usa en las 2 implementaciones hermanas) | Cualquier acción de perfil de formación cuyo `margen_dy` sea distinto de 90 calcula mal si la fecha de realización "cae dentro del margen" y debe redondearse a la fecha prevista | Sustituir `range(0, 90)` por `range(0, pfc.margen_dy)` (o `+1`, ver duda en sección 5 sobre inclusión del límite) |

| Medio | `models/leulit_parte_escuela.py:139-150` (`updateTiempos`) | `tiempo = self.tiempo / nitems` sin comprobar `nitems == 0` | Un parte de escuela con `rel_curso_alumno` cuyas líneas no casan con la condición `GROUP BY` de la SQL (datos huérfanos/inconsistentes) produce `ZeroDivisionError` | Comprobar `if nitems: tiempo = self.tiempo / nitems` |
| Medio | `models/leulit_perfil_formacion.py:35-63` (`check_cursos_acciones`) usa `item.alumno.name` como clave de `dict` | Dos alumnos con el mismo nombre (o alumno sin nombre → clave `False`) mezclan sus cursos/acciones pendientes en el mismo email de aviso | Usar `item.alumno.id` como clave (o tupla `(id, name)`) |
| Medio | `models/leulit_parte_escuela.py:178-279`, `leulit_perfil_formacion_curso.py:229-301`, `leulit_rel_alumno_curso.py:45-55`, `leulit_curso.py:80-92`, `leulit_parte_escuela.py:242-248` (`_search_uid_in_alumnos`), etc. | Antipatrón repetido: `search=` de un campo computado que hace `for item in self.search([]):` — trae **toda la tabla** a Python y filtra registro a registro | Cualquier filtro por estos campos computados (usado en vistas search/tree) con la tabla creciendo se vuelve progresivamente más lento; ya son ~10 ocurrencias en el módulo | Reescribir como dominio SQL directo cuando sea posible, o al menos limitar el `search([])` con los campos estrictamente necesarios (`read_group`/`mapped` en vez de bucle Python) |
| Medio | `models/leulit_rel_parte_escuela_cursos_alumnos.py:93-126` (`get_partes_alumno_by_curso_and_silabus_fechas`), `leulit_alumno.py:22-31,255-279,283-308,312-346` | SQL construida con `.format()`/`%` en vez de parámetros (`%s`) de `cursor.execute` | Los valores son en la práctica IDs internos (no input directo de usuario), así que el riesgo de inyección es bajo hoy, pero es un patrón frágil: cualquier futuro caller que pase un string sin sanear (p.ej. un `sesion` o `tipo` que llegase de un wizard con campo de texto libre) abre una inyección SQL real | Migrar a `self._cr.execute(sql, (params...))` con placeholders `%s` |
| Medio | `models/leulit_perfil_formacion_curso_last_done.py:19-48` vs `leulit_pf_accion_last_done.py:17-31` vs `leulit_perfil_formacion_accion_last_done.py:18-47` | 3 implementaciones casi idénticas de `_calc_fecha_last_done` con `range(0, marge_dy+1)`, `range(0, margen_dy)` y `range(0, 90)` respectivamente — comportamiento distinto para el mismo concepto de negocio | Ver hallazgo Alto anterior + sección 5 (duda de regla de negocio) | Unificar en un único método compartido (p.ej. en un mixin o util) una vez aclarado el criterio correcto |
| Medio | `models/popup_replicar_acciones_pf.py` vs `models/leulit_popup_replicar_pf_acciones.py` | Dos wizards casi duplicados que replican "acciones" de perfil de formación: uno opera sobre el modelo legacy `leulit.perfil_formacion_accion`/campo `acciones`, el otro sobre el modelo nuevo `leulit.pf_accion`/campo `acciones_new`. Ambos siguen activos y con acceso en `security.xml` | Confusión de mantenimiento: un desarrollador que toque "replicar acciones" puede editar el wizard equivocado sin que ningún test lo detecte | Ver sección 5 (duda: ¿migración a `acciones_new` completada? ¿se puede retirar el wizard/modelo legacy?) |
| Medio | `models/leulit_report_curso_pf.py:131` | `items_rpeca = items_rpeca[0]` reasigna dentro del propio `for item_rpeca in items_rpeca:` el nombre de la variable que se está iterando | No rompe la iteración (Python ya capturó el iterador), pero es código confuso/muerto que puede inducir a error en el próximo cambio | Eliminar la línea (no se usa después) |
| Medio | `models/leulit_perfil_formacion_curso_last_done.py:58-66` (`do_done_course`, rama `actualizarTodos`) | `item = self.create(...)` dentro del bucle interno reasigna la variable de bucle externo `item` | Efecto inocuo hoy (el `for item in self:` externo la reasigna en la siguiente vuelta), pero es una fuente de bugs si se añade código tras el bucle interno que siga usando `item` esperando el registro original | Usar un nombre distinto para el registro creado (`nuevo = self.create(...)`) |

| Bajo | `models/leulit_parte_escuela.py:3-4` | `from optparse import check_builtin` / `from tabnanny import check` — imports de stdlib sin relación con el fichero (existen y no rompen el import, pero no se usan) | — | Eliminar imports no usados |
| Bajo | Múltiples ficheros (`leulit_parte_escuela.py`, `leulit_alumno.py`, `leulit_rel_parte_escuela_cursos_alumnos.py`, `popup_rel_parte_escuela_cursos_alumnos.py`, `popup_replicar_cursos_pf.py`...) | Uso extensivo de `_logger.error(...)` para trazas puramente informativas ("start thread", "Contexto perfil_formacion...", banners `"="*80` con emojis ✓/✗) | Ensucia el log de producción a nivel ERROR y dificulta detectar errores reales; en `leulit_popup_rel_parte_escuela_cursos_alumnos.py` cada `create`/`write`/`default_get` genera varias líneas de log con el contenido de `vals` (podría incluir comentarios/valoraciones de alumnos) | Bajar a `_logger.debug()`/`_logger.info()` según corresponda; revisar si el logging detallado de vals de wizard sigue siendo necesario tras el debug que lo motivó |
| Bajo | `models/leulit_curso_template.py:38-39` | Labels de `ato_mo`/`ato_mi` cruzadas: `ato_mo = fields.Boolean('ATO MI')` y `ato_mi = fields.Boolean('ATO MO')` | El campo técnico `ato_mo` muestra en pantalla la etiqueta "ATO MI" y viceversa | Intercambiar las cadenas de label |
| Bajo | `models/leulit_profesor.py:20-39` | Mensaje de `ValidationError` con emojis y formato de "ayuda al usuario" (⚠️/✅) atípico frente al resto del módulo, y lógica de guarda (`'name' not in vals and 'partner_id' not in vals`) que no cubre el caso `vals['name'] == ''` (string vacío) | Crear un profesor con `name=''` explícito pasa la guarda y delega en `_inherits` de `res.partner`, que puede aceptar el nombre vacío según sus propias reglas | Añadir `or not vals.get('name')` a la condición si se quiere bloquear también nombre vacío |
| Bajo | `models/leulit_asignatura.py:24-41,57-62` | Bloques grandes de código comentado (versión API antigua `cr,uid,ids,context`) | Ruido, dificulta lectura | Eliminar código muerto comentado |
| Bajo | `models/leulit_perfil_formacion_curso.py:167` (`done_course`) | `raise UserError(_('Invalid Action!'), _('No existe ningún parte cerrado y verificado para este curso'))` — `UserError`/`_()` con dos argumentos posicionales; en Odoo 17 `UserError.__init__` solo espera un mensaje | Comportamiento exacto depende de la versión de `odoo.exceptions.UserError` instalada; en muchas versiones el segundo argumento se ignora silenciosamente en vez de fallar, por lo que el usuario nunca ve "No existe ningún parte..." | Unificar en un solo string: `raise UserError(_('No existe ningún parte cerrado y verificado para este curso'))` |
| Bajo | `security.xml` completo | Todas las reglas de `ir.model.access` usan `id` autogenerado tipo `leulit_YYYYMMDD_HHMM_access_permission` sin relación con el modelo — dificulta encontrar el permiso de un modelo dado | Cosmético | No crítico, mencionar como mejora de mantenibilidad si se retoca el fichero por el hallazgo crítico de `ir.rule` |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] Ausencia total de `ir.rule` — alumnos con acceso a datos de otros alumnos

`security.xml` da acceso CRUD completo (incluido `perm_unlink=1`) a `leulit.RBase` sobre
`leulit.parte_escuela`, `leulit.alumno`, `leulit.rel_alumno_evaluacion`, `leulit.perfil_formacion*`,
etc. No hay ni un solo `ir.rule` en el módulo (`grep -rl ir.rule addons/leulit_escuela` → vacío).

`leulit_alumno.alta_alumno()` (línea 505-522) da de alta a cada alumno con, entre otros, el grupo
`group_base` ("Base", categoría "Rol Base" — es decir `leulit.RBase` o equivalente), además de
`group_escuela` ("Alumno", `REscuela_base`). Por tanto **todo alumno dado de alta por este flujo
tiene RBase** y, con ello, acceso CRUD sin restricción de fila a los modelos de arriba.

La única barrera hoy es un filtro a nivel de `ir.actions.act_window`:

```xml
<!-- views/leulit_parte_escuela.xml -->
<record model="ir.actions.act_window" id="leulit_20201021_1102_action">
    <field name="domain">[('uid_in_alumnos','=',True)]</field>
    ...
</record>
```
```xml
<!-- menu.xml -->
<menuitem id="leulit_20201021_1102_menuitem" ... groups="REscuela_base"/>
```

frente a la acción sin restricción usada en el menú genérico "Partes escuela":

```xml
<record id="leulit_20200908_1552_action" model="ir.actions.act_window">
    <field name="name">Partes escuela</field>
    <field name="res_model">leulit.parte_escuela</field>
    <field name="view_mode">tree,form</field>
    <!-- sin domain, sin groups -->
</record>
```

Un dominio de `ir.actions.act_window` **no es una medida de seguridad**: no se aplica a llamadas
XML-RPC/JSON-RPC directas, a otra acción/menú que apunte al mismo modelo, ni impide teclear la URL
del backend con otro `action`. Con las ACL actuales, cualquier usuario con `RBase` puede leer,
modificar o **borrar** partes de escuela, notas de evaluación (`leulit.rel_alumno_evaluacion`,
`nota`, `resultado`) y perfiles de formación de cualquier otro alumno.

**Fix propuesto** (a validar contigo antes de aplicar, ver duda 5.1): añadir `ir.rule` del tipo

```xml
<record id="leulit_rule_parte_escuela_propio" model="ir.rule">
    <field name="name">Parte escuela: solo propio salvo responsable/gestor</field>
    <field name="model_id" ref="model_leulit_parte_escuela"/>
    <field name="domain_force">[('uid_in_alumnos','=',True)]</field>
    <field name="groups" eval="[(4, ref('leulit_escuela.REscuela_base'))]"/>
</record>
<record id="leulit_rule_parte_escuela_responsable" model="ir.rule">
    <field name="name">Parte escuela: acceso total responsable</field>
    <field name="model_id" ref="model_leulit_parte_escuela"/>
    <field name="domain_force">[(1,'=',1)]</field>
    <field name="groups" eval="[(4, ref('leulit_escuela.REscuela_responsable'))]"/>
</record>
```

replicando el patrón "regla restrictiva en el grupo base + regla `(1,'=',1)` explícita en el grupo
privilegiado" ya documentado en `CLAUDE.md` para `RBase`/`hr.employee`. **Ojo**: ese mismo documento
advierte que ese patrón rompió `hr.employee` porque se usa como modelo de lookup transversal
(calendarios, dropdowns...); hay que comprobar primero si `leulit.parte_escuela`/`leulit.alumno` se
usan igual desde otros módulos (`leulit_operaciones`, `leulit_planificacion`) antes de aplicar la
regla, para no repetir el incidente `e85e8f1a`.

### 3.2 [CRÍTICO] `leulit.informes_historial_popup.alumno_id` apunta al modelo equivocado

```python
# models/leulit_informes_historial_popup.py
alumno_id = fields.Many2one(comodel_name='leulit.piloto', string='Alumno')
...
idspartes = self.env['leulit.parte_escuela'].search([
    ('alumnos', 'in', [item.alumno_id.id]), ...  # 'alumnos' es One2many a leulit.alumno
])
```

```python
# models/leulit_alumno.py:172-187 (único caller)
def metodo_historial_a_ejecutar(self):
    ...
    context = {'default_alumno_id': self.id}   # self es leulit.alumno, no leulit.piloto
    return {..., 'res_model': 'leulit.informes_historial_popup', ...}
```

`self.id` es un id de `leulit.alumno`; el campo destino espera un id de `leulit.piloto`. Además,
la vista del wizard (`views/leulit_informes_historial_popup.xml`) ni siquiera muestra `alumno_id`
en el formulario, así que hoy el default nunca llega a validarse contra la FK real de forma visible
al usuario, pero si Odoo intenta persistirlo (p.ej. al guardar el wizard antes de imprimir) fallará
por FK inexistente, o si por coincidencia numérica existe ese id en `leulit_piloto`, el informe
"Histórico de Partes" listará los partes de un alumno completamente distinto al que el usuario pidió.

**Fix propuesto**:
```diff
- alumno_id = fields.Many2one(comodel_name='leulit.piloto', string='Alumno')
+ alumno_id = fields.Many2one(comodel_name='leulit.alumno', string='Alumno')
```
(el resto del `_get_report_values` ya usa `alumno_id.id` contra el campo `alumnos` de
`leulit.parte_escuela`, que es `leulit.alumno`, así que no requiere más cambios). Sería recomendable
además exponer `alumno_id` en la vista del wizard como campo de solo lectura, para que quede
trazable qué alumno se está imprimiendo.

### 3.3 [CRÍTICO] Fuga de datos vía `sudo()` en mensajes de error (`leulit_vuelo.py`)

```python
# models/leulit_vuelo.py:30-51 (uno de los tres bloques equivalentes)
if not aluveri:
    partner = item.verificado.partner_id
    alumnos_by_partner = self.env['leulit.alumno'].search([('partner_id', '=', partner.id)])
    alumnos_by_partner_sudo = self.env['leulit.alumno'].sudo().search([('partner_id', '=', partner.id)])
    ...
    msg = (
        "No se pudo resolver el Alumno desde 'verificado'.\n\n"
        ...
        "Detalles de búsqueda con sudo (sin reglas de registro):\n"
        f"- leulit.alumno por partner_id={partner.id}: {alumnos_by_partner_sudo.ids}\n\n"
        f"Usuario actual: id={self.env.user.id} login={self.env.user.login}\n"
    )
    raise UserError(_(msg))
```

Este bloque de diagnóstico (claramente añadido para depurar un incidente puntual, a juzgar por el
texto en español dirigido a un desarrollador) usa `.sudo()` explícitamente **para poder mostrarle al
usuario datos que sus propias reglas de acceso no le dejarían ver**, y lo hace dentro de un
`UserError` que cualquier usuario final puede disparar simplemente teniendo datos inconsistentes en
un vuelo (alumno/verificado sin `leulit.alumno` asociado, o profesor no resoluble). Se repite en tres
puntos: alumno vía `verificado` (líneas 30-51), alumno directo (líneas 56-73) y profesor (líneas
85-101).

**Fix propuesto**: eliminar las búsquedas `.sudo()` del mensaje visible; si el diagnóstico sigue
siendo necesario, volcarlo únicamente a `_logger.error()` (visible solo en logs de servidor, no al
usuario) y mostrar al usuario un `UserError` genérico y corto.

### 3.4 [ALTO] Filtro roto en el informe firmable de prácticas (`leulit_wizard_report_practicas_curso.py`)

```python
# models/leulit_wizard_report_practicas_curso.py:31-66
for item in self:
    cursos_data = []
    for curso in item.cursos:
        partes = parte_escuela_instance.search([...])
        vuelos = []
        for parte in partes:
            strsilabus = ""
            verificado = True
            for item in parte.rel_curso_alumno:              # <-- reasigna 'item'
                if item.alumno.id == item.alumno.id:          # <-- siempre True
                    if not item.verificado:
                        verificado = False
                    if item.rel_silabus.name:
                        strsilabus = strsilabus + item.rel_silabus.name + "<br/>"
            vuelos.append({..., 'nombrealumno': item.alumno.name, ...})
    datos['alumno_nombre'] = item.alumno.name   # puede no ser ya el alumno del wizard
```

Compárese con la versión correcta del wizard hermano:

```python
# models/leulit_wizard_report_teoricas_curso.py:39-44
for item in parte.rel_curso_alumno:
    if self.alumno.id == item.alumno.id:        # compara contra self.alumno, no se shadowea
        ...
```

En "prácticas", el bucle interno reutiliza el nombre `item` del bucle externo (`for item in self`),
así que `item.alumno.id == item.alumno.id` compara el valor consigo mismo — siempre `True` — y el
filtro por el alumno seleccionado en el wizard nunca actúa. Efecto: en un parte con varios alumnos
(vuelo con más de un alumno/verificado), el sílabus y el estado "verificado" que se imprimen pueden
corresponder a un alumno distinto del indicado en el wizard, y `datos['alumno_nombre']` puede quedar
apuntando al último `rel_curso_alumno` recorrido, no al alumno del wizard. Esto afecta a un
documento que puede firmarse (`firmar=True`, hashcode) como constancia formal de horas de vuelo.

**Fix propuesto**:
```diff
- for item in parte.rel_curso_alumno:
-     if item.alumno.id == item.alumno.id:
-         if not item.verificado:
+ for linea in parte.rel_curso_alumno:
+     if item.alumno.id == linea.alumno.id:
+         if not linea.verificado:
              verificado = False
-         if item.rel_silabus.name:
-             strsilabus = strsilabus + item.rel_silabus.name + "<br/>"
+         if linea.rel_silabus.name:
+             strsilabus = strsilabus + linea.rel_silabus.name + "<br/>"
```
(usando el `item` externo, que en este wizard es el propio registro `self`/wizard — cuidado con
mantener la referencia correcta al alumno del wizard, no del bucle).

### 3.5 [ALTO] `self.write()` en vez de `item.write()` en `do_done_course` (2 de 3 modelos)

```python
# models/leulit_pf_accion_last_done.py:33-49
def do_done_course(self):
    for item in self:
        fecha = self._calc_fecha_last_done(item.done_date, item.pf_accion.id)
        oldids = self.search([('pf_accion', '=', item.pf_accion.id)])
        oldids.write({'is_last': False})
        self.write({'done_date': item.done_date, 'is_last': True})   # <-- self, no item
        if item.actualizartodos == True:
            acciones = self.env['leulit.pf_accion'].search([...])
            for accion in acciones:
                ...
                if accion.id == item.pf_accion.id:
                    self.write({'done_date': item.done_date, 'is_last': True})   # <-- self, no item
                else:
                    self.create({...})
```

Idéntico patrón en `models/leulit_perfil_formacion_accion_last_done.py:101-118`. La implementación
correcta (referencia) es `models/leulit_perfil_formacion_curso_last_done.py:51-67`, que usa
`item.write(...)` en los mismos puntos. Hoy el bug está "enmascarado" porque los tres botones
"Guardar" que llaman a `do_done_course()` (`views/leulit_pf_accion.xml:100`,
`views/leulit_perfil_formacion_accion.xml:52,75`) abren el wizard con `target: 'new'` sobre un único
registro recién creado, así que `self == item` en la práctica. Pero es código objetivamente
incorrecto: cualquier llamada futura sobre un recordset de más de un registro (acción de servidor,
llamada RPC en lote) sobrescribiría `done_date`/`is_last` de **todos** los registros de `self` con
los valores del último `item` procesado.

**Fix propuesto**: sustituir `self.write(...)` por `item.write(...)` en las 4 líneas señaladas.

### 3.6 [ALTO] Crash garantizado en `get_alumnos_activos` con alumnos activos (sin `fecha_finalizacion`)

```python
# models/leulit_rel_alumno_curso.py:77-85
def get_alumnos_activos(self,period_end,period_start):
    lista = []
    items = self.search([])
    for item in items:
        if item.fecha_inscripcion <= period_end:
            if item.fecha_finalizacion >= period_start or item.fecha_finalizacion == False:
                if item.alumno_id.id not in lista:
                    lista.append(item.alumno_id.id)
    return len(lista)
```

Python evalúa siempre el primer operando de un `or`. Cuando `fecha_finalizacion` es `False` (caso
normal: alumno con curso todavía en curso, sin fecha de fin), `False >= period_start` compara `bool`
con `date` y lanza `TypeError: '>=' not supported between instances of 'bool' and 'datetime.date'`
(comprobado con Python 3.14 local, mismo comportamiento en cualquier CPython 3.x). No hay caller
interno en el repo (no aparece invocado desde ningún otro fichero de `leulit_escuela` ni del resto
del proyecto), pero es un método público de un modelo persistente, por tanto alcanzable vía
XML-RPC/JSON-RPC externo (el propio módulo expone otros métodos `xmlrpc_*` pensados para consumo
externo, p. ej. desde la app Flutter mencionada en la memoria del proyecto).

**Fix propuesto**:
```diff
- if item.fecha_finalizacion >= period_start or item.fecha_finalizacion == False:
+ if item.fecha_finalizacion is False or item.fecha_finalizacion >= period_start:
```

### 3.7 [ALTO] Threads en background con cursor sin cerrar (3 ocurrencias)

```python
# models/leulit_alumno.py:538-548 (idéntico patrón en leulit_parte_escuela.py:596-607
# y leulit_rel_parte_escuela_cursos_alumnos.py:130-139)
def sincronizar_horas(self):
    threaded_calculation = threading.Thread(target=self.run_sincronizar_horas, args=([]))
    threaded_calculation.start()          # sin daemon=True

def run_sincronizar_horas(self):
    with api.Environment.manage():        # no-op desde Odoo 15, no gestiona nada
        new_cr = self.pool.cursor()       # nunca se cierra
        self = self.with_env(self.env(cr=new_cr))
        for parte_escuela in self.env['leulit.parte_escuela'].search([]):
            ...
            self.env.cr.commit()          # sin try/except: una excepción deja el cursor abierto
```

Patrón correcto ya existente y documentado en el propio repo:

```python
# addons/leulit/models/res_partner.py:82-107
def _recalcular_complete_name_thread(self, dbname, uid):
    try:
        reg = registry(dbname)
        with reg.cursor() as new_cr:
            env = api.Environment(new_cr, uid, {})
            ...
    except Exception as e:
        _logger.error('Error en thread de recálculo: %s', str(e))
...
thread = threading.Thread(target=self._recalcular_complete_name_thread, args=(dbname, uid))
thread.daemon = True
thread.start()
```

Cada ejecución de `sincronizar_horas`, `get_partes_error` o `upd_set_rel_vuelo` fuga una conexión a
Postgres (nunca se llama `new_cr.close()`), y si el bucle interno lanza cualquier excepción el
`commit()`/`close()` final tampoco se ejecuta. Con uso repetido (son botones de
mantenimiento/recalculo, así que probablemente poco frecuentes, pero acumulativos) puede agotar el
pool de conexiones del contenedor Odoo.

**Fix propuesto**: reescribir los 3 métodos `run_*` siguiendo el patrón de `res_partner.py` citado
arriba (`with registry(dbname).cursor() as new_cr:` + `try/except` + `thread.daemon = True`, pasando
`dbname`/`uid` como argumentos del thread en vez de capturar `self`).

## 4. Plan de acción priorizado

1. **[Crítico]** Diseñar y añadir `ir.rule` para `leulit.parte_escuela`, `leulit.alumno`,
   `leulit.rel_alumno_evaluacion` y modelos de perfil de formación — **requiere confirmación previa
   contigo** sobre alcance (ver duda 5.1) antes de tocar `security.xml`.
2. **[Crítico]** `models/leulit_informes_historial_popup.py:23` — corregir `comodel_name` de
   `alumno_id` a `leulit.alumno`.
3. **[Crítico]** `models/leulit_vuelo.py` (3 bloques, líneas ~30-101) — quitar las búsquedas
   `.sudo()` del contenido de los `UserError`.
4. **[Alto]** `models/leulit_wizard_report_practicas_curso.py:39-40` — arreglar shadowing de `item`
   y comparación tautológica.
5. **[Alto]** `models/leulit_pf_accion_last_done.py:39,47` y
   `models/leulit_perfil_formacion_accion_last_done.py:110,117` — `self.write` → `item.write`.
6. **[Alto]** `models/leulit_rel_alumno_curso.py:82` — reordenar condición para evitar
   `TypeError` con `fecha_finalizacion=False`.
7. **[Alto]** `models/leulit_alumno.py`, `leulit_parte_escuela.py`,
   `leulit_rel_parte_escuela_cursos_alumnos.py` (3 métodos `run_*`) — reescribir con el patrón de
   cursor correcto (`with registry(dbname).cursor()`, `try/except`, `thread.daemon = True`).
8. **[Alto]** `models/leulit_perfil_formacion_accion_last_done.py:38` — usar `margen_dy` en vez de
   `90` hardcodeado (pendiente de confirmar criterio, ver duda 5.2).
9. **[Medio]** `models/leulit_parte_escuela.py:147` (`updateTiempos`) — guardar contra división por
   cero.
10. **[Medio]** `models/leulit_perfil_formacion.py` (`check_cursos_acciones`) — usar `alumno.id`
    como clave de diccionario en vez de `alumno.name`.
11. **[Medio]** Revisar y, donde sea razonable, sustituir el antipatrón `search([])` + bucle Python
    en los `search=` de campos computados (10 ocurrencias, ver tabla) por dominios SQL directos.
12. **[Medio]** Migrar las consultas SQL con `.format()`/`%` a `cursor.execute(sql, params)`
    parametrizado (`leulit_rel_parte_escuela_cursos_alumnos.py`, `leulit_alumno.py`).
13. **[Medio]** Unificar las 3 implementaciones de `_calc_fecha_last_done` una vez resuelta la duda
    5.2.
14. **[Medio]** Aclarar vigencia de `popup_replicar_acciones_pf.py` vs
    `leulit_popup_replicar_pf_acciones.py` (duda 5.3) y, si procede, retirar el legacy.
15. **[Bajo]** Limpieza: imports muertos (`leulit_parte_escuela.py:3-4`), bajar `_logger.error` a
    `debug`/`info` en logging de depuración, labels cruzadas en `leulit_curso_template.py:38-39`,
    código comentado muerto en `leulit_asignatura.py`, `UserError` con doble argumento en
    `leulit_perfil_formacion_curso.py:167`.

## 5. Dudas / no verificable sin entorno

### 5.1 Alcance de la regla de registro para `leulit.parte_escuela`/`leulit.alumno`

El hallazgo crítico 3.1 es indiscutible como *gap* (no hay ir.rule, el acceso es de facto abierto a
cualquier RBase), pero **la corrección concreta no la puedo cerrar solo leyendo código**: `CLAUDE.md`
documenta un incidente real (commit `e85e8f1a`, revertido) donde una regla similar sobre
`hr.employee` rompió calendarios/rosters para pilotos porque ese modelo se usa como lookup
transversal. Necesito confirmar contigo:
- ¿`leulit.alumno` y `leulit.parte_escuela` se consultan desde otros módulos (`leulit_operaciones`,
  `leulit_planificacion`, `leulit_actividad`) como referencia/lookup para usuarios que no son ni el
  propio alumno ni un responsable de escuela (p. ej. para mostrar nombre de alumno en un desplegable
  de vuelo)? Si es así, una regla restrictiva de fila podría romper esas vistas igual que pasó con
  `hr.employee`.
- ¿Qué grupos, además de `REscuela_responsable` y `ROperaciones_gestor`, deberían tener bypass total
  (profesores viendo alumnos de su curso, por ejemplo, no solo los suyos propios)?
- ¿Aplica la misma restricción a `leulit.rel_alumno_evaluacion` y a los modelos de perfil de
  formación (`leulit.perfil_formacion*`), o solo a partes de escuela?

### 5.2 Criterio correcto de margen en `_calc_fecha_last_done`

Existen 3 implementaciones con comportamiento distinto para lo que parece ser el mismo concepto de
negocio ("si la fecha de realización cae dentro del margen antes del vencimiento, redondear a la
fecha prevista"):
- `leulit_perfil_formacion_curso_last_done.py:39` → `range(0, pfc.marge_dy + 1)` (límite incluido)
- `leulit_pf_accion_last_done.py:22` → `range(0, pfa.margen_dy)` (límite excluido)
- `leulit_perfil_formacion_accion_last_done.py:38` → `range(0, 90)` (hardcodeado, ignora
  `margen_dy`)

No puedo determinar por el código cuál es la regla de negocio correcta (¿el margen debe ser
inclusivo o exclusivo? ¿por qué el tercero usa un valor fijo de 90 días en vez del campo
configurable?). Antes de "unificar" las tres implementaciones necesito que confirmes cuál es el
comportamiento deseado.

### 5.3 Vigencia de los wizards duplicados de "replicar acciones"

`models/popup_replicar_acciones_pf.py` (modelo `leulit.popup_replicar_acciones_pf`, opera sobre el
campo legacy `acciones`/modelo `leulit.perfil_formacion_accion`) y
`models/leulit_popup_replicar_pf_acciones.py` (modelo `leulit.popup_replicar_pf_acciones`, opera
sobre `acciones_new`/`leulit.pf_accion`) están **ambos** activos, con acceso en `security.xml` y
wireados en vistas (`views/leulit_perfil_formacion_accion.xml` usa el primero). No sé si esto es una
migración en curso (conviven sistema antiguo y nuevo a propósito, p. ej. porque hay perfiles antiguos
sin migrar a `pf_accion`) o si el primero es simplemente deuda técnica que se olvidó retirar. Antes
de tocarlo necesito que me confirmes el estado de esa migración.

### 5.4 Comportamiento de `wkf_act_cerrado` cuando el profesor no coincide con el usuario

`models/leulit_parte_escuela.py:35-38`:
```python
if item.profesor.id != self.env.user.partner_id.id:
    if item.isreadonly:
        check = False
        raise UserError(...)
```
Nótese que compara `item.profesor.id` (id de `leulit.profesor`) con
`self.env.user.partner_id.id` (id de `res.partner`) — son IDs de modelos distintos, por lo que esta
comparación **nunca es igual** salvo coincidencia numérica accidental, y el `if` de arriba
(`!=`) es casi siempre `True`. Sin embargo, dado que además está condicionado a `item.isreadonly`
(que ya considera si el usuario tiene el grupo `REscuela_responsable`), no tengo forma de verificar
sin ejecutar si esto es un bug (debería compararse contra `item.profesor.partner_id.id`) o si el
diseño ya contempla que casi siempre entra en el bloque y confía solo en `isreadonly`. Lo señalo
como posible bug de comparación de tipos (mismo patrón que el hallazgo crítico 3.2) pero no lo
incluyo en la tabla de hallazgos cerrados porque depende de una decisión de negocio que prefiero
confirmar contigo antes de tratarlo como corrección.

### 5.5 No verificable sin entorno real

- Todos los hallazgos de "antipatrón de rendimiento" (`search([])` + bucle Python en `search=`)
  están confirmados como código presente y como patrón O(n) por diseño, pero su impacto real
  (¿cuántos partes/alumnos hay en producción hoy?) solo se puede medir con la base de datos real.
- El comportamiento exacto de `UserError(_('Invalid Action!'), _('...'))` con dos argumentos
  (hallazgo bajo en `leulit_perfil_formacion_curso.py:167`) depende de la versión exacta de
  `odoo.exceptions.UserError` instalada; no he podido comprobar con Python si el segundo argumento
  se ignora o lanza `TypeError` sin la clase real de Odoo 17 disponible en este entorno.
