# Revisión de código — `leulit_calidad`

Revisión estática (sin entorno Odoo disponible) de todo el addon: `__manifest__.py`,
`models/leulit_calidad_worker.py`, `models/leulit_calidad_control_wb_report.py`,
`security.xml`, `menu.xml`, `views/leulit_calidad_worker.xml`,
`views/leulit_calidad_control_wb_report.xml`. El módulo depende de `leulit` y
`leulit_operaciones` (manifest); no hay `security/ir.model.access.csv`, ni
controladores, ni cron jobs, ni wizards adicionales — solo un `TransientModel`
(wizard de impresión) y un modelo `_inherits` de `res.partner`.

## 1. Resumen ejecutivo

10 hallazgos: **2 críticos**, **2 altos**, **6 medios**, **6 bajos/mantenibilidad**
(algunos hallazgos bajos se agrupan). Los dos críticos son un `ValueError:
Expected singleton` reproducible en `leulit_calidad_worker.py` cuando un
partner tiene más de un usuario vinculado, y una plantilla QWeb con sintaxis
Mako residual (`%if/%else/%endif`) que corrompe el CSS del informe de
"Control de Carga y Centrado". Hay además 4 decisiones/dudas que requieren
confirmación del usuario antes de cerrarse (sección 5).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_calidad_worker.py:20-24` | `_userId` asigna `partner_id.user_ids` (recordset) directo a un Many2one | Partner del worker con ≥2 `res.users` vinculados (portal+interno, reactivación) → `ValueError: Expected singleton` al leer/abrir/guardar el registro | `item.user_id = item.partner_id.user_ids[:1]` |
| Crítico | `models/leulit_calidad_worker.py:25-40` | `_search_user_id` hace `worker.partner_id.user_ids.id` sobre un recordset potencialmente multi-registro | Mismo escenario anterior, disparado al buscar/filtrar/agrupar por `user_id` | `user_ids = worker.partner_id.user_ids; user_id = user_ids[:1].id if user_ids else False` |
| Crítico | `views/leulit_calidad_control_wb_report.xml:92-96` | `%if hashcode: / %else: / %endif` dentro de `<style>` — sintaxis Mako, QWeb no la interpreta | Cualquier generación del informe "Control de Carga y Centrado" | Sustituir por `t-if`/`t-else` reales o resolver el valor en Python y usar `t-attf-style` |
| Alto | `security.xml:14-22` | `leulit.RBase` (prácticamente todos los empleados) tiene `perm_write`+`perm_unlink` sobre `leulit.calidad_worker`, sin `ir.rule` | Cualquier empleado puede borrar/editar el registro de otro trabajador de Calidad, incluidos `firma`/`sello` (usados para firmar documentos Parte-145 en otros módulos) | Restringir a un grupo "Calidad"/HR + `ir.rule` de autoedición si aplica (ver dudas) |
| Alto | `views/leulit_calidad_control_wb_report.xml:521` | `style="width:90%%"` — doble `%` inválido en CSS | Al renderizar la tabla de detalle de cada vuelo | Cambiar a `width:90%` |
| Medio | `models/leulit_calidad_control_wb_report.py:18-41` | `imprimir()` crea un `ir.actions.report` con `sudo().create()` si no lo encuentra, duplicando la definición ya declarada en XML | Si el registro `ir.actions.report` no existe (borrado manual, fallo de carga de datos) | Eliminar el fallback; si el dato XML falta, debe fallar explícito (o reinstalar el módulo), no crear con `sudo()` desde código de wizard |
| Medio | `models/leulit_calidad_control_wb_report.py:317` | `helicoptero_ids` apunta a `leulit.informes_control_wb_report` (modelo de `leulit_parte_145`) sin declarar esa dependencia en `__manifest__.py` | Funciona hoy solo porque `leulit_operaciones` depende transitivamente de `leulit_parte_145`; se rompería si esa cadena cambia | Añadir `"leulit_parte_145"` a `depends` en `__manifest__.py` |
| Medio | `models/leulit_calidad_worker.py:25-40` | `_search_user_id` hace `self.search([])` + filtrado en Python en vez de dominio ORM | Cada búsqueda/filtro/`group_by` por `user_id` en la vista de Calidad Worker, escala mal con el nº de trabajadores | Reescribir con dominio ORM, p.ej. `[('partner_id.user_ids', operator, value)]` |
| Medio | `views/leulit_calidad_control_wb_report.xml:14,20` (dominios) + `models/leulit_calidad_control_wb_report.py:45-315` | Sin límite de selección en `helicoptero_ids`/`vuelo_ids`; cada vuelo genera ~3 páginas QWeb con ~150 campos | Selección de muchos vuelos/helicópteros en el wizard → generación PDF síncrona lenta o con timeout | Añadir aviso/validación de tamaño de selección, o paginar/generar en background |
| Medio | `models/leulit_calidad_control_wb_report.py:45-315` | Sin `self.ensure_one()`; `vuelos_cont`/`texto`/`fecha`/`lugar` se toman del último `item` del bucle mientras `helicopteros`/`vuelos` acumulan de todos | Si `_get_data_to_print_control_wb` se invoca alguna vez sobre un wizard con más de un registro en `self` | Añadir `self.ensure_one()` al inicio del método |
| Medio | `models/leulit_calidad_control_wb_report.py:64-65` | No se valida que `vuelo_id.weight_and_balance_id` esté informado antes de incluir el vuelo | Vuelo `cerrado` sin peso y centrado completado → informe de auditoría con todo a cero, sin aviso | Filtrar o marcar visualmente los vuelos sin `weight_and_balance_id` |
| Bajo | `models/leulit_calidad_control_wb_report.py:3-4`, `models/leulit_calidad_worker.py:3-6` | Imports sin usar (`api, tools, exceptions, registry, AccessError, UserError, RedirectWarning, ValidationError`, `datetime` en worker) | — | Limpiar imports |
| Bajo | `models/leulit_calidad_control_wb_report.py:51-62` | Se reutiliza el nombre `helicoptero` para el recordset del bucle y luego para el dict — shadowing confuso | — | Renombrar el dict a `helicoptero_vals` |
| Bajo | `security.xml` (fichero completo) | Convención del repo es `security/ir.model.access.csv`; aquí es XML en la raíz del módulo | — | Migrar a CSV bajo `security/` para consistencia (opcional, cosmético) |
| Bajo | `views/leulit_calidad_control_wb_report.xml:93,95,175,235,279,508` | URLs de imagen hardcodeadas a un bucket S3 concreto, sin fallback | Bucket inaccesible durante generación de PDF (red, permisos, caída regional) | Sin acción urgente; documentar el riesgo o migrar a asset del módulo |
| Bajo | `models/leulit_calidad_control_wb_report.py:15` | Sin `self.ensure_one()` al inicio de `imprimir()` | — | Añadirlo por higiene defensiva |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Crítico] `ValueError: Expected singleton` en `user_id` (compute + search)

`models/leulit_calidad_worker.py:20-40`:

```python
@api.depends('partner_id')
def _userId(self):
    for item in self:
        item.user_id = item.partner_id.user_ids   # (A)

def _search_user_id(self, operator, value):
    all_workers = self.search([])
    matching_ids = []
    for worker in all_workers:
        if worker.partner_id and worker.partner_id.user_ids:
            user_id = worker.partner_id.user_ids.id if worker.partner_id.user_ids else False  # (B)
            ...
```

`res.partner.user_ids` es un `One2many` estándar de Odoo hacia `res.users`
(`inverse_name='partner_id'`) y **no está acotado a un único registro** — un
partner puede terminar con más de un usuario vinculado (usuario interno +
portal sobre el mismo contacto, o un usuario reactivado dejando un histórico).
En (A), asignar un recordset de más de un registro a un campo `Many2one`
dispara `ValueError: Expected singleton` dentro de
`Many2one.convert_to_cache`, porque internamente se llama `.id` sobre el
recordset. En (B) ocurre exactamente lo mismo de forma explícita.

Como `user_id` es un campo `compute` **no almacenado** (`store` no está a
`True`), se recalcula en cada lectura — incluido el render de
`<field name="user_id" readonly="1"/>` en `views/leulit_calidad_worker.xml:29`.
Es decir: en cuanto un worker tenga un partner con ≥2 usuarios, **el
formulario del registro deja de poder abrirse** (error 500), y cualquier
búsqueda/agrupación por `user_id` en la vista tree también falla.

Fix propuesto (dentro del alcance del módulo):

```python
@api.depends('partner_id')
def _userId(self):
    for item in self:
        item.user_id = item.partner_id.user_ids[:1]

def _search_user_id(self, operator, value):
    all_workers = self.search([])
    matching_ids = []
    for worker in all_workers:
        user = worker.partner_id.user_ids[:1]
        user_id = user.id if user else False
        if operator == '=' and user_id == value:
            matching_ids.append(worker.id)
        elif operator == '!=' and user_id != value:
            matching_ids.append(worker.id)
        elif operator == 'in' and user_id in value:
            matching_ids.append(worker.id)
        elif operator == 'not in' and user_id not in value:
            matching_ids.append(worker.id)
    return [('id', 'in', matching_ids)]
```

### 3.2 [Crítico] CSS roto por sintaxis Mako residual (`%if/%else/%endif`)

`views/leulit_calidad_control_wb_report.xml:90-100`, dentro del template
`carga_centrado_report_css`:

```xml
.page {
    %if hashcode:
        background: url(https://s3-eu-west-1.amazonaws.com/helimisc/helipistas-marca-agua.jpg) no-repeat 50% 50%;
    %else:
        background: url(https://s3-eu-west-1.amazonaws.com/helimisc/helipistas-marca-agua-informe-interno-2.jpg) no-repeat 50% 50%;
    %endif
    width: 29.7cm;
    height: 19cm;
    margin: 0.5cm 0.5cm 0.5cm 0.5cm;                 
}
```

Este `<template>` se renderiza con QWeb (`t-call="web.html_container"`), que
solo interpreta directivas `t-*` como atributos XML — nunca `%if:`/`%else:`
como texto plano dentro de un `<style>`. Además la variable `hashcode` **no
existe** en ningún momento: `_get_data_to_print_control_wb()`
(`models/leulit_calidad_control_wb_report.py:45-315`) nunca la añade al
diccionario `data`. Esto es un resto de una plantilla Mako/RML de OpenERP7 (el
propio proyecto tiene incidentes documentados de esa migración) nunca
adaptado a QWeb.

El resultado práctico: un parser CSS tolerante a errores descarta la
declaración inválida hasta el siguiente `;`, lo que en la práctica se come la
línea `background: url(...) ...;` completa (dos veces, para el `%if` y el
`%else`) y probablemente también `width: 29.7cm;` (porque `%endif` sin `:`
hace que el parser siga buscando el primer `:` disponible, que es el de
`width:`). Efecto: la marca de agua no se aplica y el tamaño de página
`.page` puede no aplicarse correctamente — en un informe de cumplimiento
normativo (Parte-145) de carga y centrado.

Fix propuesto: eliminar la ambigüedad y decidir server-side qué imagen de
fondo usar, pasándola como una clase o como URL ya resuelta en `data`:

```xml
<t t-if="hashcode">
    <style>.page { background: url(https://s3-eu-west-1.amazonaws.com/helimisc/helipistas-marca-agua.jpg) no-repeat 50% 50%; width: 29.7cm; height: 19cm; margin: 0.5cm; }</style>
</t>
<t t-else="">
    <style>.page { background: url(https://s3-eu-west-1.amazonaws.com/helimisc/helipistas-marca-agua-informe-interno-2.jpg) no-repeat 50% 50%; width: 29.7cm; height: 19cm; margin: 0.5cm; }</style>
</t>
```

(y añadir `hashcode` a `data` en `_get_data_to_print_control_wb`, o —si nunca
se usó realmente esa distinción interno/externo— simplificar a un único
`background` fijo). **Esto último es una decisión de negocio, ver sección 5.**

### 3.3 [Alto] Acceso total de `RBase` a `leulit.calidad_worker`, sin `ir.rule`

`security.xml:14-22`:

```xml
<record id="leulit_20250211_1119_access_permission" model="ir.model.access">
    <field name="name">Calidad Worker Access</field>
    <field name="model_id" ref="model_leulit_calidad_worker"/>
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

`leulit.RBase` es el grupo base al que, según `CLAUDE.md` de este repo,
prácticamente cualquier rol funcional encadena vía `implied_ids` — en la
práctica, casi todo empleado con acceso al ERP. No hay ningún `ir.rule`
definido en el módulo que acote qué registros de `leulit.calidad_worker`
puede ver/editar/borrar cada usuario. Combinado con `perm_unlink=1`, cualquier
empleado puede borrar la ficha de cualquier otro trabajador de Calidad —
incluidos los campos `firma`/`sello` (heredados de `res.partner` vía
`_inherits`), que en otros módulos del mismo repo (`leulit_esignature`, vía
`leulit_taller.leulit_mecanico`) se usan literalmente como la imagen de firma
y sello con la que se estampan documentos oficiales (p.ej. boroscopias). Si
`leulit.calidad_worker` se usa con el mismo propósito para el personal de
Calidad, cualquier empleado podría sobrescribir la firma/sello de otro
inspector.

No propongo aquí una política de acceso concreta porque implica una decisión
de negocio (¿quién debe poder editar/borrar la ficha de otro trabajador de
Calidad? ¿autoedición + un rol "responsable de calidad" con acceso total?) —
ver sección 5. Como referencia de patrón ya usado en el repo, `hr.employee`
documenta en `CLAUDE.md` un intento fallido de restringir por `ir.rule`
scoped a `RBase` que rompió otras pantallas; conviene no repetir ese error
aquí sin antes confirmar en qué otras vistas/flujos se lee
`leulit.calidad_worker` (búsqueda no realizada — fuera del alcance de esta
revisión, que se limita a los ficheros de `leulit_calidad/`).

### 3.4 [Alto] `width:90%%` — CSS inválido

`views/leulit_calidad_control_wb_report.xml:521`:

```xml
<td style="width:90%%">
```

Doble `%` — probablemente un resto de escapado de cadenas tipo `%`-format de
Python (`"width:90%%"` para producir `"width:90%"` con `%`-formatting), que
nunca se aplicó como tal porque QWeb no procesa `%`-formatting sobre atributos
estáticos. El valor `90%%` no es una longitud CSS válida; el navegador/
wkhtmltopdf lo ignora y la celda pierde el ancho del 90% previsto, afectando
el layout de la tabla de detalle de cada vuelo (columna que contiene la tabla
con Item/Masa/Localización/Momento). Fix trivial:

```xml
<td style="width:90%">
```

## 4. Plan de acción (orden recomendado)

1. **[Crítico]** `models/leulit_calidad_worker.py` — corregir `_userId` y
   `_search_user_id` para tolerar `partner_id.user_ids` con 0, 1 o más
   registros (usar `[:1]`). Sin dependencias de otros módulos, aplicable de
   inmediato.
2. **[Crítico]** `views/leulit_calidad_control_wb_report.xml` — eliminar el
   `%if hashcode:/%else:/%endif` Mako y sustituirlo por `t-if`/`t-else` reales
   (requiere antes resolver la duda 5.1: ¿se necesita esa distinción
   interno/externo o se puede fijar una sola imagen de fondo?).
3. **[Alto]** `views/leulit_calidad_control_wb_report.xml:521` — arreglar
   `width:90%%` → `width:90%`. Trivial, sin dependencias.
4. **[Alto]** `security.xml` — definir política de acceso para
   `leulit.calidad_worker` (grupo dedicado + `ir.rule`) una vez resuelta la
   duda 5.2.
5. **[Medio]** `models/leulit_calidad_control_wb_report.py` — quitar el
   fallback `sudo().create()` de `ir.actions.report` en `imprimir()`; si el
   dato XML falta, debe fallar con un `UserError` explícito en vez de crear
   silenciosamente un duplicado con privilegios elevados.
6. **[Medio]** `__manifest__.py` — añadir `"leulit_parte_145"` a `depends`
   (dependencia real, hoy solo transitiva vía `leulit_operaciones`).
7. **[Medio]** `models/leulit_calidad_worker.py` — reescribir
   `_search_user_id` con dominio ORM en vez de `search([]) `+ bucle Python.
8. **[Medio]** `models/leulit_calidad_control_wb_report.py` — añadir
   `self.ensure_one()` en `_get_data_to_print_control_wb` (y en `imprimir()`),
   y decidir cómo tratar vuelos `cerrado` sin `weight_and_balance_id` (duda
   5.3).
9. **[Medio]** Añadir validación/aviso de tamaño de selección en el wizard
   (`helicoptero_ids`/`vuelo_ids`) para evitar generación de PDFs
   desproporcionados.
10. **[Bajo]** Limpieza de imports sin usar en ambos ficheros Python.
11. **[Bajo]** Renombrar la variable `helicoptero` reutilizada como dict en
    `_get_data_to_print_control_wb` (línea 52) para evitar shadowing.
12. **[Bajo]** Opcional/cosmético: migrar `security.xml` a
    `security/ir.model.access.csv` para alinear con la convención del resto
    del repo.

## 5. Dudas / no verificable sin entorno

1. **`%if hashcode:` — ¿qué distinción se pretendía?** El código nunca pasa
   `hashcode` en `data`, así que hoy la rama `%else` es la única que "vería"
   ejecutarse cualquier lógica real (si se arreglase el `t-if`) porque
   `hashcode` siempre sería `False`/inexistente. Antes de tocar esto necesito
   saber: ¿se quería distinguir un informe "oficial" (con marca de agua) de
   uno "interno", como sugieren los dos nombres de fichero de imagen
   (`helipistas-marca-agua.jpg` vs `helipistas-marca-agua-informe-interno-2.jpg`)?
   Si es así, hay que decidir qué condición determina `hashcode` (¿un campo
   nuevo en el wizard? ¿un parámetro de la acción?) — eso es diseño de
   producto, no algo que pueda inferir solo leyendo el código.
2. **Política de acceso de `leulit.calidad_worker`.** ¿Quién debe poder
   crear/editar/borrar la ficha de un trabajador de Calidad? Actualmente es
   "todo `RBase`" sin restricción. ¿Se quiere limitar a un grupo
   "Responsable de Calidad" + autoedición del propio perfil, similar a otros
   módulos del repo? Y en particular, ¿`firma`/`sello` de este modelo se usan
   para firmar documentos oficiales (como en `leulit_taller.leulit_mecanico`
   vía `leulit_esignature`) o son solo informativos aquí? Eso cambia la
   severidad real del hallazgo 3.3.
3. **Vuelos cerrados sin `weight_and_balance_id`.** ¿Es una situación que
   puede darse en producción (flujo permite cerrar un vuelo sin peso y
   centrado) o está garantizado en otro módulo (`leulit_operaciones`) que
   todo vuelo `cerrado` tiene su W&B? Si está garantizado, el hallazgo medio
   nº 10 no aplica y se puede descartar; si no, conviene decidir si el
   informe debe excluir esos vuelos o marcarlos visualmente. No puedo
   verificarlo sin acceso al modelo `leulit.vuelo`/flujo de cierre (fuera del
   alcance de `leulit_calidad/`) ni a datos reales.
4. **Prefetch de `weight_and_balance_id` dentro del bucle de vuelos.**
   (`models/leulit_calidad_control_wb_report.py:63-299`) — Odoo normalmente
   propaga el `prefetch_ids` al atravesar un `Many2one` accedido dentro de un
   `for x in recordset:`, lo que evitaría el clásico N+1 al leer los ~150
   campos de `weight_and_balance` por vuelo. Tengo razonable confianza en que
   esto se comporta así (es un comportamiento documentado del ORM de Odoo),
   pero no lo puedo confirmar sin ejecutar el código con datos reales y
   `--log-level=debug_sql` o el profiler. Si al probar el informe con muchos
   vuelos seleccionados se observan tiempos altos, merece la pena perfilarlo
   antes de asumir que el prefetch automático lo cubre.
5. **Campos `hr.employee.emergency_contact`/`emergency_phone`**
   (`models/leulit_calidad_worker.py:46-47`, related hacia `employee_id`).
   Tengo confianza razonable en que son campos estándar del módulo `hr` de
   Odoo 17 Community (sección "Emergencia" de la ficha de empleado), pero el
   código fuente de `hr` no está vendorizado en este repo (es del core de
   Odoo) y no he podido grepearlo para confirmarlo al 100%. Si al actualizar
   el módulo (`./upd_module.sh leulit_calidad dev`) aparece un error de campo
   inexistente en ese `related`, es la primera pista a revisar.
6. **`calidad_worker.active` independiente de `partner_id.active`.** Como
   `LeulitCalidadWorker` define su propio campo `active` (línea 50) y usa
   `_inherits` hacia `res.partner`, Odoo **no** genera el proxy automático
   para `active` (porque ya existe localmente) — son dos flags de "activo"
   completamente independientes: archivar el worker no archiva el partner, y
   viceversa. Esto puede ser intencional (permite desactivar el "rol de
   trabajador de Calidad" sin tocar el contacto, que puede seguir usándose en
   otros documentos) o un efecto colateral no buscado del patrón `_inherits`.
   No lo marco como bug porque depende de la intención de negocio — decidir
   si es el comportamiento deseado.
