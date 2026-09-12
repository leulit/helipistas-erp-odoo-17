# Revisión de código — addons/leulit

Revisión estática (sin entorno Odoo real) de modelos, vistas, seguridad, wizards y reports del
módulo fundacional `leulit`. Alcance estricto: `addons/leulit/`.

## 1. Resumen ejecutivo

- **Crítico: 3** — un `ir.rule` abre todos los adjuntos de la BD a casi cualquier usuario
  (`RBase`), un botón "Adjuntos" sin domain que hereda ese agujero, y un bypass de autorización
  multi-registro en `leulit.historial_circular`.
- **Alto: 4** — informe de checklist roto (`object.name` inexistente), `write()` que revienta en
  edición múltiple, cuentas contables creadas siempre en `company_id=1` (ignora multi-compañía),
  y un menú completo (`Migración > Errores de importación`) nunca cargado por el manifest.
- **Medio: 10** — constraint muerto que sigue lanzando una query en cada factura, computes que no
  asignan valor en todos los casos, creates en bucle (N+1), `eval()` duplicado y sin uso, ids
  hardcodeados, `except:` genérico, fichero de config muerto con campo inexistente.
- **Bajo: ~4** — assets JS/XML huérfanos, funciones duplicadas/con firma API v7 muertas en
  `utilitylib.py`, wizard sin menú de acceso.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `security.xml:126-138` | `ir.rule` con `domain_force=[(1,'=',1)]` para `RBase` en `ir.attachment` | Cualquier usuario con `RBase` (casi todos) hace `search/read/write/unlink` sobre `ir.attachment` y ve/borra adjuntos de cualquier otro usuario/compañía | Restringir el domain a huérfanos (`res_id=False`) y/o a la compañía del usuario, igual que ya hace `check()` en Python |
| Crítico | `adjuntos.xml:19-26` | Acción `leulit_20211114_2153_action` sin `domain` | Botón "Adjuntos" en cualquier ficha (p.ej. `leulit_escuela/views/leulit_asignatura.xml`) abre la lista de **todos** los adjuntos de la BD, no solo los del registro | Añadir `domain` filtrando por `res_model`/`res_id` del contexto |
| Crítico | `models/leulit_historial_circular.py:17-48` | `unlink()`/`write()` hacen `for item in self:` pero `return super().unlink()/write(vals)` actúa sobre todo `self` y corta en el primer registro | Selección múltiple de filas de distintas circulares: si la primera pasa el check de autor, se borran/escriben TODAS sin comprobar las demás | Aplicar el check y la operación registro a registro, acumulando el resultado, sin `return` prematuro |
| Alto | `report/ir_actions_report.xml:10,21` | `print_report_name` usa `object.name`, pero `leulit.checklist`/`leulit.checklist_template` no tienen campo `name` (usan `descriptor`) | Pulsar "Imprimir" en un checklist/plantilla | Cambiar a `object.descriptor` |
| Alto | `models/leulit_checklist.py:96-108` | `write()` usa `self.id`/`self.template` sobre un recordset potencialmente multi-registro | Edición múltiple en la vista tree de `leulit.checklist` con `template` en los valores | Iterar `for rec in self:` y operar por registro |
| Alto | `models/res_partner.py:57-80` | `get_next_accounts()` crea `account.account` con `company_id: 1` fijo (+ `user_type_id`, ver Dudas) | Pulsar "Asignar cuentas" sobre un partner de la compañía Icarus (id=2) | Usar `self.env.company.id` / `item.company_id.id` en vez del literal `1` |
| Alto | `__manifest__.py:30-54` + `views/err_import.xml` | `views/err_import.xml` no está en `data` del manifest | El menú "Migración > Errores de importación" nunca se crea aunque el modelo tiene permisos | Añadir `"views/err_import.xml"` a `data` (o confirmar que se quiere descartar la feature) |
| Medio | `models/account_move.py:15-22` | `_check_invoice_date_from_others` hace `search()` en cada `invoice_date` de factura de venta pero solo `break`, nunca `raise` | Cualquier alta/edición de fecha en una `out_invoice` | Restaurar el `raise ValidationError` si la regla es intencional, o eliminar el constraint muerto |
| Medio | `models/account_analytic_line.py:27-33` | `_compute_date_time_end` hace auto-asignación (`= record.date_time_end`) cuando faltan dependencias, en vez de limpiar el campo | `unit_amount` se pone a 0 tras haber tenido valor: `date_time_end` queda con el valor viejo | `record.date_time_end = False` en el `else` |
| Medio | `models/sale_order.py:17-21` | `_get_full_name` (`store=True`) no asigna `item.full_name` cuando falta `name` o `partner_id` | Presupuesto nuevo sin `partner_id` aún asignado | Asignar siempre, con fallback: `item.full_name = ... if ... else (item.name or '')` |
| Medio | `models/leulit_circular.py:24-46` | `enviarEmail()`: SQL crudo + `send_mail` por destinatario en bucle, sin try/except individual | Un email inválido en el historial detiene el envío a los destinatarios restantes | Envolver cada iteración en try/except y usar `write()` ORM en vez de SQL crudo |
| Medio | `models/leulit_circular.py:49-79` | `create_historial_circular` crea `leulit.historial_circular` uno a uno dentro de un bucle | Circular dirigida a un área/curso con muchos destinatarios | Acumular dicts y usar `create([...])` en batch |
| Medio | `utilitylib.py:1198-1206` / `models/leulit_circular.py:13-16` | Función `condition()` duplicada, basada en `eval()` sobre strings construidos | Sin call-sites actuales (código muerto), pero es una trampa de inyección si se reutiliza | Eliminar ambas copias o sustituir por comparadores explícitos, sin `eval` |
| Medio | `models/res_partner.py:141` y `:50` | Ids hardcodeados: `country_id` `default=68`, `sel_groups_1_9_10: 10` | Restaurar/migrar la BD a otra instancia donde esos ids no coincidan con España / el grupo esperado | Usar `env.ref('base.es').id` y referencias por xmlid en vez de literales |
| Medio | `models/res_partner.py:42-55` | `except:` genérico en `create_user_by_partner`, descarta la excepción real | Falla la creación de usuario por cualquier motivo (login duplicado, etc.) | `except Exception as e:` + `_logger.exception` antes de relanzar `UserError` |
| Medio | `views/ir_config_parameter.xml` (fichero completo) | No está en el manifest (muerto) y filtra por `check_hlp`, campo que no existe en ningún módulo del repo | Si algún día se añade al manifest sin el campo, rompe la actualización del módulo | Definir el campo `check_hlp` en un override de `ir.config_parameter` antes de activar el fichero, o borrarlo si ya no aplica |
| Medio | `roles_2026.xml` (fichero completo) | Jerarquía de roles nueva, completa, pero comentada en el manifest y sin `ir.model.access`/menús que la usen | — (dato en reposo, no se ejecuta) | Ver sección "Dudas" — decidir si se termina de cablear o se retira |
| Bajo | `static/src/js/leulit.js`, `canvas2image.js`, `widget_keyboard_disabled.js/.xml`, `widget_semaforo_cell.js`/`semaforo_cell.xml` | Ficheros no referenciados por ningún `assets` de ningún manifest del repo | — | Eliminarlos o cablearlos si tienen uso previsto |
| Bajo | `utilitylib.py` (múltiples líneas) | `hlp_float_time_convert`/`leulit_float_time_convert` duplicadas idénticas; `decimal_time_from_datetime` definida dos veces (la segunda pisa la primera); varias funciones con firma vieja `(self, cr, uid, ...)` sin call-sites reales | — | Eliminar duplicados y funciones muertas de la era API v7 |
| Bajo | `models/leulit_documento_migrar_wizard.py` + `views/leulit_documento.xml:59-64` | `leulit_documento_migrar_wizard_action` no tiene `menuitem` en todo el repo, pese a que el docstring dice "se lanza desde el menú Ajustes" | — | Añadir el `menuitem` bajo Ajustes, o corregir el docstring |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 CRÍTICO — `ir.rule` abre todos los adjuntos a `RBase` (`security.xml:125-138`)

```xml
<record id="leulit_20251114_1130_attachment_orphan_rule" model="ir.rule">
    <field name="name">RBase: Allow attachments (full access)</field>
    <field name="model_id" ref="base.model_ir_attachment"/>
    <field name="groups" eval="[(4, ref('leulit.RBase'))]"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

`RBase` es el rol raíz del que cuelgan, vía `implied_ids`, prácticamente todos los roles
funcionales del ERP (documentado en `CLAUDE.md`: "virtualmente todo rol funcional encadena hasta
`RBase`"). Un `domain_force` de `[(1,'=',1)]` no restringe ninguna fila: cualquier query ORM
(`search`, `read`, `write`, `unlink`) sobre `ir.attachment` hecha por cualquier usuario con
`RBase` ve y puede modificar/borrar **absolutamente todos** los adjuntos de la base de datos,
incluidos los de otros usuarios, otros módulos (nóminas, e-signature, CAMO...) y otras compañías
(Helipistas/Icarus).

El override Python en `models/ir_attachment.py` (`check()`) es mucho más cuidadoso: solo abre el
acceso a adjuntos **huérfanos** (`res_id` vacío) para `RBase`. Pero `check()` solo se invoca en
las rutas de descarga/lectura directa de adjuntos (`/web/content`, `/web/image`...); el `ir.rule`
en cambio se aplica a **todo** el resto de accesos ORM (listados, `read_group`, exportaciones,
`search_read` desde cualquier vista), donde el `check()` no interviene. El resultado es que el
`ir.rule` es mucho más permisivo que el comentario de la propia regla ("adjuntos huérfanos")
sugiere, y contradice la intención documentada en `ir_attachment.py`.

**Fix propuesto** (a validar con el usuario, ver Dudas — puede haber una razón de negocio para
el acceso amplio):

```xml
<field name="domain_force">[('res_id', '=', False)]</field>
```

o, si además se quiere acotar por compañía:

```xml
<field name="domain_force">['|', ('res_id', '=', False), ('company_id', 'in', company_ids)]</field>
```

### 3.2 CRÍTICO — Botón "Adjuntos" sin `domain` (`adjuntos.xml:19-26`)

```xml
<record id="leulit_20211114_2153_action" model="ir.actions.act_window">
    <field name="name">Listado adjuntos modelo acción</field>
    <field name="res_model">ir.attachment</field>
    <field name="view_mode">tree</field>
    <field name="view_id" ref="leulit.leulit_20211114_2150_view"/>
    <!--field name="domain">[('res_id','=',active_id),('default_res_model': context.get('default_res_model'))]</field-->
</record>
```

El propio fichero deja comentada (y con sintaxis rota) la línea de `domain` que el desarrollador
original pretendía añadir. Esta acción se usa como botón "Adjuntos" desde otros módulos, p. ej.
`addons/leulit_escuela/views/leulit_asignatura.xml:13-14`:

```xml
<button class="oe_stat_button" icon="fa-file-o" type="action"
    name="%(leulit.leulit_20211114_2153_action)d" string="Adjuntos"
    context="{'default_res_id': id, 'default_res_model': 'leulit.asignatura'}"/>
```

El `context` solo fija valores por defecto para **crear** un adjunto nuevo desde la lista; no
filtra los ya existentes. Sin `domain` en la acción, la tabla que se abre es el `ir.attachment`
completo — combinado con el hallazgo 3.1, cualquier usuario que pulse ese botón ve todos los
adjuntos de todos los módulos y compañías.

**Fix propuesto** (en `addons/leulit/adjuntos.xml`, dentro de alcance):

```xml
<field name="domain">[('res_model','=',context.get('default_res_model')),('res_id','=',context.get('default_res_id'))]</field>
```

*(Nota: el botón concreto que dispara el bug vive en `leulit_escuela`, fuera de alcance de esta
revisión — no se toca, solo se señala como consumidor del bug real, que está en `leulit`.)*

### 3.3 CRÍTICO — Bypass de autorización multi-registro en `leulit.historial_circular`

`models/leulit_historial_circular.py:17-48`:

```python
def unlink(self):
    for item in self:
        if item.circular_id.autor_id.id == self.env.uid:
            return super().unlink()
        else:
            raise UserError('El usuario no esta autorizado a realizar esta modificación')

def write(self, vals):
    for item in self:
        circular = False
        if 'circular_id' in vals:
            circular = self.env['leulit.circular'].browse(vals['circular_id'])
        if item.circular_id:
            circular = item.circular_id
        if circular:
            if circular.autor_id.id == self.env.uid:
                return super().write(vals)
        if item.user_id.id == self.env.uid:
            if 'recibido' in vals or 'leido' in vals or 'entendido' in vals or 'enviado' in vals:
                return super().write(vals)
        else:
            raise UserError('El usuario no esta autorizado a realizar esta modificación')
```

El `for item in self:` solo evalúa realmente el **primer** registro: en cuanto entra en un
`return`, el método termina — pero ese `return super().unlink()`/`write(vals)` opera sobre **todo
`self`**, no sobre `item`. Escenario concreto: el usuario selecciona en la vista lista varias
filas de `leulit.historial_circular` que pertenecen a circulares de **distintos** autores y pulsa
borrar. Si la primera fila de la selección pertenece a una circular de la que el usuario actual
es autor, `unlink()` borra **todas** las filas seleccionadas sin comprobar las demás — bypass de
autorización sobre los registros 2..n.

Además, si la primera fila no cumple ningún `if` de `write()` (p. ej. `item.user_id.id ==
self.env.uid` pero `vals` no trae ninguno de los 4 campos permitidos), el bucle sigue a la
siguiente iteración sin `return` ni `raise`; si ningún registro dispara un `return`, el método
cae al final de la función y devuelve `None` implícitamente — un `write()` que no escribe nada,
no avisa de nada y devuelve un valor no estándar (Odoo espera `True`/booleano) al cliente web.

**Fix propuesto:**

```python
def unlink(self):
    for item in self:
        if item.circular_id.autor_id.id != self.env.uid:
            raise UserError('El usuario no esta autorizado a realizar esta modificación')
    return super().unlink()

def write(self, vals):
    campos_permitidos = {'recibido', 'leido', 'entendido', 'enviado'}
    for item in self:
        circular = self.env['leulit.circular'].browse(vals['circular_id']) if 'circular_id' in vals else item.circular_id
        autorizado = (circular and circular.autor_id.id == self.env.uid) or (
            item.user_id.id == self.env.uid and campos_permitidos & set(vals.keys())
        )
        if not autorizado:
            raise UserError('El usuario no esta autorizado a realizar esta modificación')
    return super().write(vals)
```

### 3.4 ALTO — Informe de checklist roto: `object.name` no existe

`report/ir_actions_report.xml:10` y `:21`:

```xml
<field name="print_report_name">'Informe Checklist-%s' % (object.name or '')</field>
...
<field name="print_report_name">'Informe Plantilla Checklist-%s' % (object.name or '')</field>
```

Ni `leulit.checklist` ni `leulit.checklist_template` (`models/leulit_checklist.py`,
`models/leulit_checklist_template.py`) declaran un campo `name`; ambos usan `_rec_name =
"descriptor"` y solo tienen el campo `descriptor`. `print_report_name` se evalúa contra el
registro real al generar/descargar el PDF; acceder a `object.name` sobre un modelo sin ese campo
lanza `AttributeError`.

**Fix propuesto:**

```xml
<field name="print_report_name">'Informe Checklist-%s' % (object.descriptor or '')</field>
```

Relacionado (confianza media, no verificable sin ejecutar): en `checklist_print_report()`
(`models/leulit_checklist.py:21-38` y equivalente en `leulit_checklist_template.py`) la llamada es

```python
return self.env.ref('leulit.report_leulit_checklist').report_action([], data=data)
```

pasando una lista de ids **vacía** en vez de `rec.ids`. Si el mecanismo de `report_action` usa
esos ids para resolver `object` al evaluar `print_report_name`, esto agravaría el fallo anterior
incluso si se corrige el nombre del campo. Recomiendo pasar `rec.ids` explícitamente y confirmarlo
imprimiendo un checklist en el entorno de pruebas.

### 3.5 ALTO — `write()` de `leulit.checklist` rompe en edición múltiple

`models/leulit_checklist.py:96-108`:

```python
def write(self, vals):
    if 'template' in vals:
        template = self.env['leulit.checklist_template'].browse(vals['template'])
        tmpvalues = self.getTemplateValues(template)
        vals.update(tmpvalues)
    result = super(leulit_checklist, self).write(vals)
    attachment_to_remove = self.env['ir.attachment'].search([('res_model', '=', 'leulit.checklist'),('res_id', '=', self.id)])
    attachment_to_remove.unlink()
    if self.template:
        ...
```

`self.id` y `self.template` se acceden como si `self` fuera siempre un único registro. Si el
método se invoca sobre un recordset con más de un `id` (p. ej. edición múltiple desde la vista
tree de "Checklists" cuando se cambia `template` a varios registros seleccionados a la vez), Odoo
lanza `ValueError: Expected singleton` al intentar leer `self.id`/`self.template` sobre un
recordset multi-registro.

**Fix propuesto:**

```python
def write(self, vals):
    if 'template' in vals:
        template = self.env['leulit.checklist_template'].browse(vals['template'])
        vals.update(self.getTemplateValues(template))
    result = super().write(vals)
    for rec in self:
        self.env['ir.attachment'].search([
            ('res_model', '=', 'leulit.checklist'), ('res_id', '=', rec.id)
        ]).unlink()
        if rec.template:
            for attachment in self.env['ir.attachment'].search([
                ('res_model', '=', 'leulit.checklist_template'), ('res_id', '=', rec.template.id)
            ]):
                attachment.copy(default={'res_model': 'leulit.checklist', 'res_id': rec.id})
    return result
```

### 3.6 ALTO — `get_next_accounts()` ignora la compañía real del partner

`models/res_partner.py:57-80`:

```python
account_cobrar = self.env['account.account'].create({'code':str(codigo_max_cobrar+1),'name':item.name,'user_type_id':1,'reconcile':True,'company_id':1})
account_pagar = self.env['account.account'].create({'code':str(codigo_max_pagar+1),'name':item.name,'user_type_id':2,'reconcile':True,'company_id':1})
```

`company_id` está hardcodeado a `1` (Helipistas) sin importar en qué compañía trabaja el usuario
o a qué compañía pertenece realmente el `partner`. Este repositorio es explícitamente
multi-compañía (Helipistas=1, Icarus=2 — ver `CLAUDE.md`, sección `leulit_almacen`). Ejecutar
"Asignar cuentas" sobre un cliente/proveedor de Icarus crea sus cuentas contables por cobrar/pagar
en la compañía 1, lo que puede provocar inconsistencias contables entre compañías (cuentas
inaccesibles o mal filtradas al facturar desde Icarus).

**Fix propuesto** (pendiente de confirmar con el usuario si se corrige `user_type_id`, ver
Dudas):

```python
company_id = item.company_id.id or self.env.company.id
account_cobrar = self.env['account.account'].create({..., 'company_id': company_id})
account_pagar = self.env['account.account'].create({..., 'company_id': company_id})
```

### 3.7 ALTO — Menú "Errores de importación" nunca se carga

`__manifest__.py` (`data`) no incluye `"views/err_import.xml"`, a pesar de que ese fichero define
el modelo de vista/acción de `leulit.error_import` y todo el menú "Migración":

```python
"data": [
    "groups.xml",
    "security.xml",
    "paperformats.xml",
    "views/res_config_settings.xml",
    "views/res_partner.xml",
    "views/hr_expense_sheet.xml",
    "views/res_company.xml",
    "views/project_project_views.xml",
    "views/leulit_circular.xml",
    "views/actions.xml",
    "views/stock.xml",
    "views/sale_order.xml",
    "views/leulit_checklist.xml",
    "views/leulit_checklist_template.xml",
    "views/leulit_checklist_item.xml",
    "views/leulit_documento.xml",
    "views/hr_employee.xml",
    "report/leulit_report_checklist.xml",
    "report/ir_actions_report.xml",
    "adjuntos.xml",
    "menu.xml",
    "precision.xml"
],
```

`security.xml` sí concede permisos completos sobre `leulit.error_import` al grupo `RBase`
(`leulit_20211026_1023_model_access`), es decir: el modelo y sus permisos existen en la BD, pero
nadie puede llegar a la UI para usarlo porque su vista/acción/menú nunca se cargan.

**Fix propuesto:** añadir `"views/err_import.xml"` a `data`, tras confirmar con el usuario que el
menú "Migración > Errores de importación" sigue siendo necesario (ver Dudas).

## 4. Plan de acción priorizado

1. **[Crítico]** `security.xml` — acotar el `domain_force` del `ir.rule` de adjuntos a huérfanos
   (y/o compañía), no `[(1,'=',1)]`. *Requiere decisión de negocio, ver Dudas §5.1.*
2. **[Crítico]** `adjuntos.xml` — añadir `domain` a `leulit_20211114_2153_action`.
3. **[Crítico]** `models/leulit_historial_circular.py` — corregir `unlink()`/`write()` para
   evaluar autorización registro a registro sin `return` prematuro.
4. **[Alto]** `report/ir_actions_report.xml` — `object.name` → `object.descriptor` en los dos
   `print_report_name`.
5. **[Alto]** `models/leulit_checklist.py` — hacer `write()` seguro para multi-registro.
6. **[Alto]** `models/res_partner.py` — `get_next_accounts()`: usar la compañía real en vez de
   `company_id: 1`; verificar `user_type_id` en el entorno real (ver Dudas §5.2) antes de tocar
   nada más en ese método.
7. **[Alto]** `__manifest__.py` — decidir con el usuario si se restaura
   `"views/err_import.xml"` en `data` o se retira la feature (ver Dudas §5.3).
8. **[Medio]** `models/account_move.py` — decidir si se restaura la validación de
   `_check_invoice_date_from_others` o se borra el constraint muerto (ver Dudas §5.4).
9. **[Medio]** `models/account_analytic_line.py` — `_compute_date_time_end`: limpiar el campo en
   el `else` en vez de auto-asignarlo.
10. **[Medio]** `models/sale_order.py` — `_get_full_name`: asignar siempre un valor.
11. **[Medio]** `models/leulit_circular.py` — `enviarEmail()`: try/except por destinatario;
    `create_historial_circular()`: batch create.
12. **[Medio]** `models/res_partner.py` — sustituir ids hardcodeados (`country_id=68`,
    `sel_groups_1_9_10=10`) por `env.ref(...)`; capturar `Exception` con log en
    `create_user_by_partner`.
13. **[Medio]** Eliminar la función `condition()` (eval-based) duplicada en `utilitylib.py` y
    `models/leulit_circular.py`, sin uso actual.
14. **[Medio]** `views/ir_config_parameter.xml` — decidir con el usuario si se completa (definir
    `check_hlp`) o se borra (ver Dudas §5.5).
15. **[Medio]** `roles_2026.xml` — decidir con el usuario si se termina de cablear (accesos +
    menús) o se retira del repo (ver Dudas §5.6).
16. **[Bajo]** Limpiar assets JS/XML huérfanos (`leulit.js`, `canvas2image.js`,
    `widget_keyboard_disabled.*`, `widget_semaforo_cell.js`/`semaforo_cell.xml`) si se confirma
    que no tienen consumidores previstos.
17. **[Bajo]** `utilitylib.py` — eliminar duplicados (`hlp_float_time_convert` /
    `leulit_float_time_convert`, `decimal_time_from_datetime` definida dos veces) y funciones
    muertas de firma API v7 sin call-sites.
18. **[Bajo]** Añadir `menuitem` para `leulit_documento_migrar_wizard_action` bajo Ajustes, o
    corregir el docstring que dice que ya existe.

## 5. Dudas / no verificable sin entorno

**5.1 — Alcance real del acceso a adjuntos para `RBase`.** El `ir.rule` de `security.xml:126-138`
da acceso total a *todos* los `ir.attachment` para el grupo `RBase`. El comentario del propio
fichero dice que es "necesario porque varios modelos usan `_inherits` con `ir.attachment`
(`leulit.maintenance_manual`, etc.)" — un módulo fuera de este alcance. No puedo saber, sin
preguntarte, si esa amplitud es una decisión de negocio deliberada (aunque desproporcionada) o un
error de alcance al escribir la regla. Antes de estrechar el `domain_force` necesito que me
confirmes: ¿hay casos reales en producción donde un usuario `RBase` normal necesita leer/escribir
adjuntos que no son suyos ni huérfanos (más allá de `leulit.maintenance_manual`, que vive en otro
módulo)?

**5.2 — `user_type_id` en `account.account` (Odoo 17).** `models/res_partner.py:72-73` crea
`account.account` pasando `user_type_id: 1`/`2`. No tengo acceso al código fuente de Odoo core en
este entorno (no está vendorizado en el repo) para confirmar si en la versión de Odoo 17
Community instalada ese campo sigue existiendo o fue reemplazado por el `Selection` `account_type`
introducido en versiones recientes de Odoo. Si el campo ya no existe, `get_next_accounts()` falla
en cada ejecución con un error de campo inválido. Pide confirmación ejecutando en el entorno de
pruebas:

```python
env['account.account']._fields.get('user_type_id')  # o desde shell: odoo-bin shell -d productiu
```

**5.3 — `views/err_import.xml` fuera del manifest.** No sé si esto es un olvido (el fichero, el
modelo `leulit.error_import` y sus permisos existen y parecen terminados) o si la feature
"Migración > Errores de importación" se descartó a propósito y el fichero debería borrarse en vez
de re-añadirse. Pregúntame antes de tocar el manifest.

**5.4 — `_check_invoice_date_from_others` sin `raise`.** El código comentado
(`# raise ValidationError(...)`) sugiere que en algún momento se decidió desactivar esa
validación de negocio ("no permitir fecha de factura anterior a otra ya emitida") sin borrar el
método entero. No sé si la regla de negocio sigue siendo deseada (y solo falta reactivar el
`raise`) o si se abandonó y el método entero debería eliminarse. Es una decisión de negocio, no
puedo cerrarla por mi cuenta.

**5.5 — `views/ir_config_parameter.xml` / campo `check_hlp`.** Fichero muerto (ni en el manifest
ni con el campo `check_hlp` definido en ningún sitio del repo). No sé si formaba parte de un
desarrollo interrumpido de una pantalla de "Parámetros del Sistema" filtrados, o si es un resto
de una prueba. Pregúntame si quieres que se complete o se borre.

**5.6 — `roles_2026.xml`.** Jerarquía de roles nueva y completa (con el comentario "para permitir
un traspaso manual y controlado de usuarios al nuevo esquema"), pero comentada en el manifest y
sin ningún `ir.model.access`, `ir.rule` o menú que la consuma todavía. Por el nombre y la fecha
("06_2026", hoy es 2026-09-10) parece trabajo en curso para una migración de roles ya planificada
y no un error. Lo dejo fuera del plan de acción salvo que confirmes que quieres que se re-audite
como si fuera código activo.

**5.7 — Grupo `RBase_hide` en un menú real.** `views/res_partner.xml:46-53` da el menú
"contactos + cuentas" al grupo `leulit.RBase_hide` (que en `groups.xml` solo tiene el comentario
"Hide" y hereda de `RBase_employee`). No tengo contexto suficiente para saber si "Hide" es un rol
legítimo con ese nombre o si es un artefacto de otra funcionalidad (ocultar menús) reutilizado
aquí por error. Señalado, no incluido en el plan de acción.
