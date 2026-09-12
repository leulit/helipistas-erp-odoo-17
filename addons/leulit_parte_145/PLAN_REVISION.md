# Revisión de código — `addons/leulit_parte_145`

Revisión estática (sin entorno Odoo disponible) de todo el addon: modelos, vistas, seguridad,
menús. El módulo no contiene controladores, wizards, cron jobs ni informes QWeb — no hay nada
que revisar en esas categorías.

Alcance verificado por lectura: `git log`/`git show` para el histórico del addon, y `grep`
exhaustivo repo-wide (excluyendo `third-party-addons`) para todo hallazgo que dependa de
ficheros fuera de `leulit_parte_145` (confirmado, no asumido).

## 1. Resumen ejecutivo

**18 hallazgos**: 4 críticos, 4 altos, 7 medios, 3 bajos. Los críticos dejan **completamente
inoperativo** el módulo MEL (sin `ir.model.access` en absoluto) y los dos modelos de informe
basados en vista SQL (`init()` comentado desde el primer commit del addon, sin tabla en BD), y
generan un `IndexError` no controlado al calcular `descfabricante` con datos que no casan con
las 4 claves fijas del selection. Varios hallazgos críticos/altos tienen impacto confirmado en
otros módulos (`leulit_seguridad`, `leulit_calidad`, `leulit_taller`, `leulit_esignature`) sin
tocarlos, tal como exige el alcance. Hay 6 dudas de negocio que requieren confirmación tuya
antes de intervenir (sección 5).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_helicoptero_oilreport.py:29-61` | `init()` que crea la vista SQL está comentado desde el primer commit; con `_auto=False` no hay tabla en BD | Abrir menú Calidad → "Análisis consumo aceite", o cualquier `search`/`read` sobre `leulit.helicoptero_oilreport` | Descomentar `init()` y revisar que los campos de `leulit.vuelo` referenciados sigan existiendo (fuera de este módulo) |
| Crítico | `models/leulit_control_wb_report.py:30-49` | Igual que arriba para `leulit.informes_control_wb_report`, además usado como comodel m2m en `leulit_calidad/models/leulit_calidad_control_wb_report.py:317` | Abrir la acción `leulit_20201109_1149_action`, o cualquier operación desde `leulit_calidad` sobre ese campo m2m | Descomentar `init()` |
| Crítico | `security.xml` (ausente) | No existe ningún `ir.model.access` para `leulit.mel`, `leulit.mel_ata`, `leulit.mel_tipo_operacion`, `leulit.revision_mel` (grep repo-wide sin resultados) | Cualquier usuario no superusuario abre el menú MEL, o el campo `melref`/`tipomel` en `leulit_seguridad/views/leulit_anomalia.xml:92-93` | Añadir registros `ir.model.access` para los 4 modelos, con los mismos grupos usados en `leulit_lines_mel` (que sí los tiene) |
| Crítico | `models/leulit_helicoptero.py:40-45` | `_get_desc_fabricante` hace `matching[0][1]` sin comprobar que `matching` no esté vacío | `item.fabricante` no coincide con ninguna de las 4 claves fijas de `_get_fabricantes()` (dato migrado/legacy, o vacío) → `IndexError` no controlado | Comprobar `matching` antes de indexar y devolver `''`/`False` si no hay coincidencia |
| Alto | `models/leulit_helicoptero.py:74-87` | `except:` desnudo alrededor de una consulta SQL cruda; si la query falla deja el cursor de la transacción en estado abortado sin loguear nada | Un fallo real en la consulta (columna renombrada, DDL concurrente) hace que TODAS las operaciones ORM posteriores en la misma request fallen con un error distinto y sin traza del origen | `except Exception: _logger.exception(...)` como mínimo; idealmente no envolver en try/except o usar `self.env.cr.savepoint()` |
| Alto | `views/leulit_mel.xml:78`, `views/leulit_revision_mel.xml:31`, `views/leulit_control_wb_report.xml:24` | Las 3 `ir.actions.act_window` no están enlazadas a ningún `menuitem` en todo el repo (grep confirma) | Las pantallas MEL, Revisión MEL y Control W&B son inalcanzables desde el menú | Añadir `menuitem` para cada acción, o confirmar si es intencional (acceso solo vía otro módulo/smart-button que no existe hoy) |
| Alto | `models/leulit_helicoptero.py:206`; `views/leulit_helicoptero.xml:94` | El campo mágico `write_uid` se redefine con `readonly=False` y se muestra en el form sin `readonly="1"` | Cualquier usuario con permiso de escritura sobre `leulit.helicoptero` abre el form y cambia "Modificado por:" a otro usuario | Quitar la redefinición del campo (usar el `write_uid` estándar, ya readonly) o al menos poner `readonly="1"` en la vista |
| Alto | `security.xml:3-47` | `perm_unlink=1` en 4 grupos (`RBase_hide`, `ROperaciones_gestor`, `RTaller_base`, `RCAMO_base`) sobre `leulit.helicoptero`, que ya tiene el flag `baja` para baja lógica, sin `unlink()` sobreescrito | Cualquier usuario de esos 4 roles borra físicamente una aeronave con historial de vuelos/mantenimiento asociado | Quitar `perm_unlink` salvo para un grupo estrecho, o sobreescribir `unlink()` para bloquear/avisar si hay registros relacionados |
| Medio | `models/leulit_mel_ata.py:18-28` | `ata_name` es compute sin `@api.depends('num','name')` | Editar `num` o `name` de un `leulit.mel_ata` existente; `ata_name` puede quedar obsoleto en caché hasta que algo más invalide el registro | Añadir `@api.depends('num', 'name')` |
| Medio | `models/leulit_helicoptero.py:17-24,48-71,90-99,102-108,74-87` | Patrón N+1: cada compute hace una `search()`/SQL por registro en vez de una sola consulta batched sobre `self.ids` | Listar varios helicópteros en `leulit_20200626_1201_tree` o `leulit_20230516_1258_tree` dispara 1 query por fila y por campo calculado | Reescribir los 5 computes para hacer una única consulta agrupada por `helicoptero_id` sobre `self.ids` y mapear resultados |
| Medio | `views/leulit_helicoptero_oilreport.xml:11-17` | Filtros de búsqueda con 7 matrículas literales (`EC-GUC`, `EC-GVG`...) hardcodeadas | La flota cambia (alta/baja de aeronave) y el filtro no se entera; no falla, simplemente deja de ser útil silenciosamente | Sustituir por un `group_by`/filtro dinámico sobre `helicoptero_id`, o generar los filtros desde datos en vez de hardcodearlos |
| Medio | `security.xml:48-56,57-74` | `leulit.RBase` (rol base, prácticamente todo empleado) tiene CRUD completo sobre `leulit.modelohelicoptero` (dato maestro); y `perm_create/write/unlink=1` sobre los 2 modelos vista-SQL que nunca pueden escribirse (no tienen tabla) | Cualquier empleado con `RBase` crea/borra modelos de helicóptero; los permisos de escritura en las vistas SQL son papel mojado engañoso | Restringir CRUD de `modelohelicoptero` a roles de gestión; dejar `perm_create/write/unlink=0` en los 2 modelos de solo lectura |
| Medio | `models/leulit_helicoptero.py:92` | `_calc_oil_helicoptero` construye SQL con `%r` (interpolación de string) en vez de parámetros, a diferencia de `_calc_landings_helicoptero` 12 líneas antes que sí usa `%s` parametrizado | No explotable hoy (`item.id` es int controlado por el ORM), pero es un patrón peligroso si se copia con un valor no controlado | Reescribir con `self._cr.execute("... WHERE helicoptero_id = %s ...", (item.id,))` |
| Medio | `views/leulit_helicoptero.xml:180-186` | Acción `leulit_20201125_1125_action` no fija `view_id` habiendo 3 tree views distintas registradas para `leulit.helicoptero` | Menú Taller → "Listado de Aeronaves" puede mostrar una vista distinta a la esperada según resolución por defecto de Odoo | Fijar explícitamente `view_id` |
| Bajo | `groups.xml:11-14` | Grupo `RM145_base` definido y sin ninguna referencia en todo el repo (grep) | — | Confirmar si es un grupo abandonado y eliminarlo, o si falta cablearlo a algo |
| Bajo | todos los `models/*.py` | Imports sin usar (`tools`, `exceptions`, `registry`, `AccessError`, `UserError`, `RedirectWarning`, `ValidationError`, `datetime` según fichero) | — | Limpieza cuando se toque cada fichero por otro motivo |
| Bajo | `models/leulit_modelo.py:38` | `performance_altura_velocidad = fields.Image(...)` sin `max_width`/`max_height` | Subir una imagen muy grande infla el tamaño de la tabla sin redimensionar | Añadir límites de tamaño al campo `Image` |

## 3. Hallazgos críticos/altos — detalle

### 3.1 Vistas SQL sin `init()` activo (Crítico)

`models/leulit_helicoptero_oilreport.py` y `models/leulit_control_wb_report.py` definen
`_auto = False` (modelo respaldado por una vista SQL, no por una tabla normal) pero el método
`init()` que crea esa vista está **comentado por completo**, y así ha estado desde el primer
commit que introdujo estos ficheros en este repo (`2d7a48187`, 28-ago-2025 — no es una
regresión reciente, es un artefacto de migración que nunca se completó):

```python
# def init(self):
#     tools.drop_view_if_exists(self._cr, 'leulit_helicoptero_oilreport')
#     self._cr.execute("""
#         CREATE OR REPLACE VIEW leulit_helicoptero_oilreport AS (
#             ...
#         )""")
```

Sin `init()`, Odoo no crea ninguna tabla ni vista para este `_name` en la base de datos. Cualquier
`search`/`read`/`browse` sobre `leulit.helicoptero_oilreport` o
`leulit.informes_control_wb_report` falla con `psycopg2.errors.UndefinedTable` ("relation ...
does not exist"). Esto rompe:
- El menú Calidad → "Análisis consumo aceite" (`menu.xml:48-54`, acción `leulit_20201109_1131_action`).
- Cualquier acceso a `leulit.informes_control_wb_report`, incluido el campo m2m
  `helicoptero_ids` en `addons/leulit_calidad/models/leulit_calidad_control_wb_report.py:317`
  (fuera de alcance, no tocado — solo señalado).

**Nota de alcance**: si en producción estos modelos "funcionan" hoy es porque la vista SQL
quedó creada en la BD de una instalación anterior a este commit y nunca se ha vuelto a hacer
`-i`/reinstalación completa (coherente con que producción va meses por detrás de main). En
cualquier instalación nueva, o si alguien ejecuta `-i leulit_parte_145` desde cero, esto falla
de inmediato.

**Fix propuesto** (revisar antes de aplicar — ver duda F en sección 5, los campos de
`leulit.vuelo` que referencia el SQL viven fuera de este módulo):

```diff
-    # def init(self):
-    #     tools.drop_view_if_exists(self._cr, 'leulit_helicoptero_oilreport')
-    #     self._cr.execute("""
-    #         CREATE OR REPLACE VIEW leulit_helicoptero_oilreport AS ( ... )""")
+    def init(self):
+        tools.drop_view_if_exists(self._cr, 'leulit_helicoptero_oilreport')
+        self._cr.execute("""
+            CREATE OR REPLACE VIEW leulit_helicoptero_oilreport AS ( ... )""")
```

### 3.2 `leulit.mel`, `leulit.mel_ata`, `leulit.mel_tipo_operacion`, `leulit.revision_mel` sin `ir.model.access` (Crítico)

`security.xml` solo da acceso a `leulit.lines_mel` (líneas 75-83). Los otros 4 modelos MEL no
tienen ningún registro `ir.model.access` en todo el repo (confirmado por grep sobre
`model_leulit_mel`, `model_leulit_mel_ata`, `model_leulit_mel_tipo_operacion`,
`model_leulit_revision_mel` — cero resultados). Sin acceso, cualquier usuario no-superusuario
(incluido un Administrador normal, que no es `uid=1`) recibe `AccessError` al tocar estos
modelos.

Impacto confirmado fuera de este módulo: `addons/leulit_seguridad/views/leulit_anomalia.xml:92-93`
muestra el campo `melref` (Many2one a `leulit.mel`) en el formulario de anomalías:

```xml
<field name="melref" domain="[('helicoptero_ids','in',[helicoptero_id])]" .../>
<field name="linemel_id" domain="[('mel_id','=',melref)]" .../>
```

Cualquier usuario abriendo ese formulario, o desplegando ese desplegable, dispara el
`AccessError` — un módulo distinto (`leulit_seguridad`) queda roto por un hueco de seguridad en
este módulo.

**Fix propuesto** (mismo patrón que el registro existente para `leulit.lines_mel`):

```xml
<record id="leulit_mel_access_permission" model="ir.model.access">
    <field name="name">Mel Access</field>
    <field name="model_id" ref="model_leulit_mel"/>
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
<!-- + análogo para model_leulit_mel_ata, model_leulit_mel_tipo_operacion, model_leulit_revision_mel -->
```

Confirmar contigo el grupo destinatario correcto (¿`RBase` como el resto del módulo, o un rol
más restringido dado que MEL es de seguridad de vuelo? — ver duda en sección 5 si aplica).

### 3.3 `IndexError` en `_get_desc_fabricante` (Crítico)

```python
# models/leulit_helicoptero.py:40-45
@api.depends('fabricante')
def _get_desc_fabricante(self):
    lista = self._get_fabricantes()
    for item in self:
        matching = [s for s in lista if item.fabricante in s]
        item.descfabricante = matching[0][1]
```

`_get_fabricantes()` solo admite 4 claves fijas (`robinson`, `eurocopter`, `guimbal`, `dji`). Si
`item.fabricante` es `False` o cualquier valor que no sea exactamente una de esas 4 claves
(dato legado/migrado con otra codificación, por ejemplo), `matching` queda vacío y
`matching[0]` lanza `IndexError` sin capturar.

`descfabricante` no se usa en ninguna vista de este módulo, pero sí se lee directamente desde
otros módulos (confirmado por grep, fuera de alcance — no tocados):
- `addons/leulit_taller/models/leulit_maintenance_crs.py:155`: `item.helicoptero.descfabricante.capitalize()`
- `addons/leulit_taller/models/leulit_maintenance_boroscopia.py:139`
- `addons/leulit_esignature/models/leulit_maintenance_crs.py:109`
- `addons/leulit_esignature/models/leulit_maintenance_boroscopia.py:112`

Un helicóptero con `fabricante` fuera de las 4 claves rompe la generación de informes CRS,
Boroscopia y su firma electrónica.

**Fix propuesto**:

```diff
     for item in self:
         matching = [s for s in lista if item.fabricante in s]
-        item.descfabricante = matching[0][1]
+        item.descfabricante = matching[0][1] if matching else ''
```

### 3.4 `write_uid` redefinido y editable en el form (Alto)

```python
# models/leulit_helicoptero.py:206
write_uid = fields.Many2one('res.users', 'by User', readonly=False)
```

```xml
<!-- views/leulit_helicoptero.xml:93-95 -->
<group col="2">
    <field name="write_uid" string="Modificado por:" options="{'no_create': True, 'edit': False, 'no_open':true}"/>
</group>
```

El campo mágico `write_uid` se redefine quitándole `readonly` (el estándar de Odoo lo define
`readonly=True`), y se muestra en el form sin `readonly="1"` propio de la vista. Las opciones
`no_create`/`edit`/`no_open` solo restringen la creación/navegación desde el widget, no la
edición del valor: el desplegable de selección de usuario sigue activo. Cualquier usuario con
permiso de escritura sobre `leulit.helicoptero` puede cambiar manualmente "Modificado por:" a
otro usuario, falseando el rastro de auditoría del registro (que además ya tiene chatter/
`mail.thread` para eso).

**Nota de incertidumbre** (no verificable sin entorno — ver sección 5, duda C): no puedo
confirmar sin ejecutar Odoo si al hacer `write()` el valor de `write_uid` enviado por el
cliente prevalece sobre el que el ORM asigna automáticamente, o si el mecanismo interno de
`_log_access` de Odoo lo sobreescribe después. Independientemente de eso, exponer el campo como
editable en el formulario ya es un problema por sí solo.

**Fix propuesto**: quitar la redefinición de `write_uid` (usar el campo mágico estándar) y, si
se quiere seguir mostrando "Modificado por:" en el form, usar `readonly="1"` explícito en la
vista.

## 4. Plan de acción priorizado

1. **[Crítico]** `security.xml` — añadir `ir.model.access` para `leulit.mel`, `leulit.mel_ata`,
   `leulit.mel_tipo_operacion`, `leulit.revision_mel` (bloquea el módulo MEL completo y rompe
   `leulit_seguridad`). Confirmar grupo destinatario antes de aplicar (duda sección 5).
2. **[Crítico]** `models/leulit_helicoptero_oilreport.py` y
   `models/leulit_control_wb_report.py` — descomentar/reescribir `init()`, verificando primero
   contra el modelo `leulit.vuelo` (fuera de este módulo) que los campos referenciados
   (`fechasalida`, `oilqty`, `airtime`, `helicoptero_id`) sigan existiendo tal cual.
3. **[Crítico]** `models/leulit_helicoptero.py:40-45` — blindar `_get_desc_fabricante` contra
   `matching` vacío.
4. **[Alto]** `views/leulit_mel.xml`, `views/leulit_revision_mel.xml`,
   `views/leulit_control_wb_report.xml` — decidir con el usuario si hay que añadir `menuitem`
   para las 3 acciones huérfanas o si el acceso es intencionalmente indirecto (duda sección 5).
5. **[Alto]** `models/leulit_helicoptero.py:74-87` — sustituir el `except:` desnudo por manejo
   explícito con logging.
6. **[Alto]** `models/leulit_helicoptero.py:206` + `views/leulit_helicoptero.xml:94` — revertir
   la redefinición de `write_uid` o forzar `readonly="1"` en la vista.
7. **[Alto]** `security.xml:12-47` — revisar el alcance de `perm_unlink=1` sobre
   `leulit.helicoptero` en los 4 grupos; considerar bloquear `unlink()` o restringirlo.
8. **[Medio]** `models/leulit_mel_ata.py:28` — añadir `@api.depends('num','name')` a `ata_name`.
9. **[Medio]** `models/leulit_helicoptero.py` — batchear los 5 computes con patrón N+1
   (`_compute_last_parte_dates`, `get_airtime_vuelos`/`_calc_airtime_helicoptero`,
   `_calc_oil_helicoptero`, `_date_last_vol`, `_calc_landings_helicoptero`).
10. **[Medio]** `security.xml:48-74` — ajustar permisos de `leulit.modelohelicoptero` (CRUD
    completo para `RBase` es excesivo para un dato maestro) y de los 2 modelos vista-SQL
    (quitar create/write/unlink ya que nunca pueden persistir).
11. **[Medio]** `views/leulit_helicoptero_oilreport.xml:11-17` — sustituir filtros de
    matrícula hardcodeados por algo dinámico.
12. **[Medio]** `models/leulit_helicoptero.py:92` — parametrizar la consulta de
    `_calc_oil_helicoptero` (quitar `%r`).
13. **[Medio]** `views/leulit_helicoptero.xml:180-186` — fijar `view_id` explícito en
    `leulit_20201125_1125_action`.
14. **[Bajo]** `groups.xml:11-14` — decidir si `RM145_base` se elimina o se cablea.
15. **[Bajo]** limpieza de imports no usados en `models/*.py`, cuando se toquen esos ficheros
    por otro motivo.
16. **[Bajo]** `models/leulit_modelo.py:38` — añadir límites de tamaño al campo `Image`.

## 5. Dudas / no verificable sin entorno

Estas decisiones no se pueden cerrar solo leyendo el código; necesito tu confirmación antes de
convertir cualquiera de ellas en una tarea del plan de acción:

- **A. Visibilidad de `is_privado`**: `leulit_helicoptero.py:210` tiene un booleano
  `is_privado` pero no hay ningún `ir.rule` que restrinja qué usuarios ven las aeronaves
  privadas — ¿es solo una etiqueta informativa, o debería haber una barrera de acceso real que
  falta?
- **B. `compute_sudo=True` + `.sudo()` explícito en `_compute_last_parte_dates`**
  (`leulit_helicoptero.py:17-24`, usado en `views/leulit_helicoptero.xml` acción
  `leulit_20230516_1258_action`): esto expone la fecha y aeropuerto del último parte de vuelo
  cerrado de **cualquier** helicóptero a **cualquier** usuario con acceso de lectura al
  modelo, sin pasar por las reglas de registro de `leulit.vuelo`. ¿Es un dashboard
  intencionalmente abierto, o una fuga de datos entre roles/compañías?
- **C. Precedencia real de `write_uid` enviado por el cliente** (hallazgo 3.4): si Odoo permite
  que el valor de `write_uid` recibido en `vals` prevalezca sobre el que el ORM asigna
  automáticamente, la severidad sube de "campo editable en UI" a "rastro de auditoría
  falsificable de forma persistente". Requiere probarlo en un entorno real (crear/editar un
  registro pasando `write_uid` explícito y comprobar qué queda grabado); no lo puedo confirmar
  por lectura de código de este addon.
- **D. `onchange_fechalastWB` solo actualiza `wblastmod` desde la UI**
  (`leulit_helicoptero.py:26-28`): cualquier escritura de `fechalastWB` que no pase por el
  onchange del formulario (importación, script, otra API) no actualiza `wblastmod`, que es
  precisamente el campo que el informe de cumplimiento "Control Integridad de datos de carga y
  centrado" usa para acreditar cuándo se introdujo el dato en el ERP. ¿Es intencional que solo
  cuente la edición manual, o debería reforzarse a nivel de `write()`/constraint?
- **E. Listados "Aeronaves" sin filtrar `baja`**: las acciones `leulit_20201103_1049_action`
  (Helipistas) y `leulit_20230516_1258_action` (Operaciones) muestran todas las aeronaves sin
  excluir las dadas de baja, a diferencia de los menús CAMO dedicados y de la acción de
  oilreport, que sí filtran. ¿Es deliberado (Operaciones necesita ver todo) o un descuido?
- **F. Contenido exacto del `init()` a restaurar** (hallazgo 3.1): el SQL comentado referencia
  columnas de `leulit.vuelo` (`fechasalida`, `oilqty`, `airtime`, `helicoptero_id`) que viven en
  otro módulo (`leulit_actividad`/`leulit_operaciones`, fuera de alcance). No he verificado que
  esos nombres de columna sigan vigentes hoy — antes de descomentar el `init()` hay que
  confirmarlo contra el modelo actual de `leulit.vuelo`.
