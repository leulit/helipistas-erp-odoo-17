# Revisión de código — `leulit_hide_menus`

Revisión estática (sin entorno Odoo ejecutable) de todo el addon: `__manifest__.py`, `__init__.py`
y `views/hide_menus.xml`. El módulo no tiene modelos, controladores, wizards, crons ni reports —
es puramente datos declarativos XML que reasignan `groups_id`/`sequence` sobre `ir.ui.menu` de
otros módulos.

## 1. Resumen ejecutivo

**5 hallazgos**: 1 crítico, 1 alto, 1 medio, 2 bajos. El hallazgo crítico es un `depends` de
manifest incompleto (13 módulos referenciados por xmlid en `views/hide_menus.xml` que no están
declarados) — funciona hoy porque esos módulos ya están instalados en las BBDD dev/prod actuales,
pero **romperá con `ValueError: External ID not found`** en cualquier instalación limpia, incluida
la migración a Odoo 18 ya planificada. El hallazgo alto es de gobernanza de seguridad: este módulo
solo oculta menús en la UI, no restringe los modelos subyacentes — no debe asumirse como control de
acceso por sí solo.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `__manifest__.py:10-16` + `views/hide_menus.xml` (líneas 18, 22, 26, 30, 34, 42, 46, 50, 54, 58, 62, 66, 70) | `depends` no incluye los 13 módulos cuyos xmlids se referencian en el XML (`hr_timesheet`, `website`, `mass_mailing`, `utm`, `fleet`, `contacts`, `hr`, `sale`, `account`, `document_knowledge`, `stock`, `maintenance`, `repair`) | Instalación limpia de `leulit_hide_menus` (p. ej. la migración a Odoo 18) o un `-u all` donde el grafo de dependencias no garantice que esos módulos ya cargaron sus datos | Añadir los 13 módulos a `depends` |
| Alto | `views/hide_menus.xml` (todo el fichero) | El módulo solo actúa sobre `ir.ui.menu.groups_id` (visibilidad de menú en la UI); no toca `ir.model.access.csv` ni `ir.rule` de los modelos subyacentes (`hr.employee`, `sale.order`, `account.move`, `stock.quant`, `crm.lead`, etc.) | Un usuario sin el menú visible pero con acceso ORM al modelo (por otro menú ya concedido, URL directa `#action=`, informe, smart button, o XML-RPC) puede seguir leyendo/escribiendo esos datos | No es un fix de este módulo (fuera de alcance) — documentar explícitamente que esto es ocultación de UI, no control de acceso, y auditar en los módulos dueños de cada modelo que exista una restricción real equivalente |
| Medio | `__manifest__.py:24` | `"application": True` en un módulo sin vistas/menús propios ni icono (`static/description/icon.png` no existe) — infla el listado de Apps con una entrada técnica genérica | Un administrador filtra "Apps" en Ajustes > Apps y ve una entrada sin icono ni función de negocio propia | Cambiar a `"application": False`, igual que el módulo análogo `leulit_groups_manager` |
| Bajo | `views/hide_menus.xml:65` y `:69` | Comentario XML `<!-- Mantenimiento -->` duplicado: la segunda instancia (línea 69) es sobre `repair.menu_repair_order`, no mantenimiento | Ninguno funcional — solo confunde al mantenedor que lea el fichero | Renombrar el segundo comentario a `<!-- Reparaciones -->` |
| Bajo | `__manifest__.py:5,21` | Claves de manifest obsoletas/vacías: `"css": []` (clave heredada de Odoo <8, ignorada por el bundling de assets actual) y `"description": "\n    "` sin contenido real | Ninguno funcional — ruido en el manifest | Eliminar `"css"` y rellenar o vaciar `"description"` de forma consistente |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Crítico] `depends` de manifest incompleto — riesgo de `ValueError: External ID not found`

**Contexto.** `__manifest__.py` declara:

```python
'depends': [
    'mail',
    'calendar',
    'project',
    'crm',
    'leulit',
],
```

Pero `views/hide_menus.xml` referencia `ref()`/xmlid de **13 módulos que no están en esa lista**:

| Línea | xmlid referenciado | Módulo que lo define | ¿Está en `depends`? |
|---|---|---|---|
| 18 | `hr_timesheet.timesheet_menu_root` | `hr_timesheet` | No |
| 22 | `website.menu_website_configuration` | `website` | No |
| 26 | `mass_mailing.mass_mailing_menu_root` | `mass_mailing` | No |
| 30 | `utm.menu_link_tracker_root` | `utm` | No |
| 34 | `fleet.menu_root` | `fleet` | No |
| 42 | `contacts.menu_contacts` | `contacts` | No |
| 46 | `hr.menu_hr_root` | `hr` | No |
| 50 | `sale.sale_menu_root` | `sale` | No |
| 54 | `account.menu_finance` | `account` | No |
| 58 | `document_knowledge.menu_document_root` | `document_knowledge` (vendorizado en `addons/third-party-addons/document_knowledge`, confirmado su xmlid en `views/document_knowledge.xml:34`) | No |
| 62 | `stock.menu_stock_root` | `stock` | No |
| 66 | `maintenance.menu_maintenance_title` | `maintenance` | No |
| 70 | `repair.menu_repair_order` | `repair` | No |

(`base.menu_management` en la línea 38 es correcto sin declarar dependencia — `base` siempre está
cargado.)

**Por qué falla.** Odoo determina el orden de carga de módulos a partir del grafo de dependencias
declarado en `depends`. Sin una arista explícita hacia `sale`, `stock`, `hr`, etc., el orden entre
`leulit_hide_menus` y esos módulos **no está garantizado** en una instalación desde cero (p. ej.
`odoo -i leulit_hide_menus` en una BBDD nueva, o `-u all`). Si `leulit_hide_menus` se procesa antes
de que, por ejemplo, `stock` haya cargado sus datos, `ref('stock.menu_stock_root')` lanza
`ValueError: External ID not found in the system: stock.menu_stock_root` y aborta la carga del
módulo. Además, en una instalación mínima donde alguno de esos módulos (especialmente
`document_knowledge`, que es de terceros, no core) simplemente no esté instalado, el fallo es
determinista.

**Por qué no se ha visto en prod/dev hoy.** Las bases de datos actuales ya tienen todos esos
módulos instalados desde hace tiempo, y los xmlids persisten en `ir.model.data`
independientemente del grafo de la ejecución de actualización en curso — por eso
`./upd_module.sh leulit_hide_menus dev` funciona hoy sin problema. El riesgo es específicamente
para instalaciones nuevas — y el proyecto ya tiene planificada una migración a Odoo 18
(`t3.xlarge`, ventana de 24h) donde este módulo se instalará de cero.

**Fix propuesto** (diff sobre `__manifest__.py`):

```diff
     'depends': [
         'mail',
         'calendar',
         'project',
         'crm',
         'leulit',
+        'hr',
+        'hr_timesheet',
+        'sale',
+        'account',
+        'stock',
+        'website',
+        'mass_mailing',
+        'utm',
+        'fleet',
+        'contacts',
+        'maintenance',
+        'repair',
+        'document_knowledge',
     ],
```

Nota: `document_knowledge` es un módulo de terceros vendorizado en este repo
(`addons/third-party-addons/document_knowledge`), no un módulo core de Odoo — confirmar con el
usuario si se quiere mantener esa dependencia dura (si algún día se retira ese addon vendorizado,
`leulit_hide_menus` dejaría de instalar) o si se prefiere quitar esa entrada del XML.

### 3.2 [Alto] Ocultar un menú no restringe el modelo subyacente

**Contexto.** Todas las modificaciones de este módulo son sobre `ir.ui.menu.groups_id`
(`eval="[(6, 0, [ref(...)])]"`), por ejemplo:

```xml
<record id="stock.menu_stock_root" model="ir.ui.menu">
    <field name="groups_id" eval="[(6, 0, [ref('leulit.RBase_hide')])]"/>
</record>
```

`groups_id` en `ir.ui.menu` solo controla si el menú aparece en la interfaz para un usuario dado.
No es una capa de seguridad ORM: no afecta a `ir.model.access.csv`, `ir.rule`, controladores HTTP,
XML-RPC/JSON-RPC, ni a otros menús/acciones que apunten al mismo modelo y sí sigan siendo visibles
para ese usuario (por ejemplo, un smart button, un campo relacionado, o un informe).

**Escenario concreto.** Un usuario con solo `RBase_hide` (la inmensa mayoría de la plantilla, según
`addons/leulit/groups.xml:21-25` y el patrón usado en todo el repo — p. ej.
`addons/leulit_operaciones/menu.xml:240`) no ve el menú "Inventario" (`stock.menu_stock_root`,
línea 62) ni "Facturación" (`account.menu_finance`, línea 54). Si ese mismo usuario tiene acceso a
`stock.quant`/`account.move` por cualquier otra vía (URL directa `/odoo/action-<id>`, un widget
`many2one` que abra el registro, un informe imprimible, o una llamada XML-RPC externa) y las reglas
de acceso de esos modelos no restringen independientemente su grupo, seguirá pudiendo leer/escribir
esos datos con normalidad — el menú oculto no es una barrera real.

**No es un bug de este módulo** — es una limitación inherente del mecanismo `ir.ui.menu.groups_id`
y está fuera de alcance arreglarlo aquí (viviría en `ir.model.access.csv`/`ir.rule` de `leulit`,
`leulit_comercial`, `leulit_almacen`, o de los módulos core `hr`/`sale`/`account`/`stock`/`crm`).
Se documenta como hallazgo de seguridad porque el nombre y el propósito del módulo
("Hide specific menus for certain user groups") puede llevar a asumir erróneamente que sustituye
un control de acceso real. Recomendación: auditar en un trabajo aparte que los modelos detrás de
cada menú ocultado tengan `ir.model.access.csv`/`ir.rule` coherentes con la intención (self-service
de RRHH, financiero, CRM comercial, almacén) — no se ha hecho en esta revisión porque cae fuera del
alcance de `addons/leulit_hide_menus/`.

## 4. Plan de acción priorizado

1. **[Crítico]** `__manifest__.py:10-16` — añadir a `depends` los 13 módulos listados en 3.1
   (`hr`, `hr_timesheet`, `sale`, `account`, `stock`, `website`, `mass_mailing`, `utm`, `fleet`,
   `contacts`, `maintenance`, `repair`, `document_knowledge`), confirmando antes con el usuario si
   `document_knowledge` sigue vigente como dependencia dura. Hacerlo **antes** de cualquier
   instalación limpia (incluida la migración a Odoo 18).
2. **[Alto]** Fuera de este módulo — abrir una auditoría específica (otra tarea/otro módulo) de
   `ir.model.access.csv`/`ir.rule` para los modelos detrás de los menús ocultados, si la intención
   real es restringir acceso y no solo limpiar la UI.
3. **[Medio]** `__manifest__.py:24` — cambiar `"application": True` a `False`.
4. **[Bajo]** `views/hide_menus.xml:69` — corregir el comentario duplicado a "Reparaciones".
5. **[Bajo]** `__manifest__.py:5,21` — eliminar `"css": []` y limpiar `"description"`.

## 5. Dudas / no verificable sin entorno

- **`base.menu_management` (línea 38).** El comentario del código dice "Apps" y así lo he asumido,
  pero no he podido confirmarlo consultando una instancia Odoo 17 real ni el código fuente de
  `base` (no disponible en este entorno). Si ese xmlid correspondiera en realidad al menú raíz de
  "Ajustes" (`base.menu_administration` es el que yo esperaría para eso) en vez de al submenú de
  Apps, restringirlo a `leulit.RolIT_developer` ocultaría Ajustes generales a todos los usuarios
  salvo IT — una regresión funcional severa. Recomiendo verificar en el entorno de pruebas
  (`docker/docker-compose.yml`, `localhost:8070`) con un usuario sin `RolIT_developer` antes de dar
  este comportamiento por bueno (aunque, al ser un registro ya existente y presumiblemente en
  producción desde hace tiempo sin quejas reportadas, es más probable que el comentario sea
  correcto).
- **El fallo `ValueError: External ID not found` del hallazgo 3.1** es una deducción a partir del
  grafo de dependencias de Odoo y de la ausencia de esas claves en `depends`; no he podido
  ejecutar `odoo -i leulit_hide_menus` sobre una base de datos limpia en este entorno (no hay
  Odoo/Postgres local) para confirmarlo empíricamente. Recomiendo reproducirlo en un entorno
  desechable antes de la migración a Odoo 18.
- **Alcance del hallazgo 3.2** depende de configuración (`ir.model.access.csv`/`ir.rule`) que vive
  en otros módulos fuera de `addons/leulit_hide_menus/`; no se ha auditado ese código en esta
  revisión, solo se señala el riesgo conceptual.
