# Revisión de `addons/leulit_ventas/` — informe de hallazgos

Fecha de revisión: 2026-09-10. Revisor: agente Claude (revisión de código, sin ejecución de Odoo).

## 1. Resumen ejecutivo

El módulo es minúsculo: `__init__.py` vacío, `__manifest__.py` y un único
`views/menu.xml` (16 líneas, un `<menuitem>`). No hay modelos, wizards,
controladores, crons, reports, ni `security/` — no hay Python que revisar.
Es el gemelo exacto de `addons/leulit_compras/` (mismo commit `4a6d767d`,
mismo patrón, ya revisado en `addons/leulit_compras/PLAN_REVISION.md`): los
mismos hallazgos aplican aquí con los nombres cambiados. El único hallazgo
con peso real es de **seguridad/diseño**: el `<menuitem>` no lleva `groups`,
y hay precedente directo en este mismo repo (código comentado en
`leulit_comercial/menu.xml`) de la misma funcionalidad implementada *con*
`groups` explícito.

**Recuento**: 0 críticos · 1 alto (a confirmar contigo, ver sección 5) ·
1 medio · 3 bajos.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Alto (a confirmar) | `views/menu.xml:8-14` | `<menuitem>` sin `groups=`, a diferencia del precedente comentado en `leulit_comercial/menu.xml:4-8` que sí restringía a `sales_team.group_sale_salesman` | Cualquier usuario interno con acceso a la app Ventas (incluidos roles sin permisos de facturación) ve el menú "Facturas de Ventas"; si además tiene lectura sobre `account.move` por otra vía, accede a datos de facturación sin pasar por un grupo pensado para ello | Añadir `groups="sales_team.group_sale_salesman"` (o el grupo que decidáis) al `<menuitem>`, replicando el patrón ya usado en `leulit_comercial/menu.xml:8` |
| Medio | `__manifest__.py:9-12` | `depends` no incluye `leulit`, rompiendo la convención del repo ("todo módulo `leulit_*` depende de `leulit`", ver `CLAUDE.md` del proyecto) | Ninguno en runtime (el módulo no usa nada de `leulit`) — es una cuestión de convención/mantenibilidad, no un fallo funcional | Confirmar si es intencional (módulo puramente de vistas) o si se debe añadir la dependencia por consistencia |
| Bajo | `views/menu.xml:11` | `parent="sale.sale_order_menu"` — distinto del `parent="sale.sale_menu_root"` usado en el precedente comentado de `leulit_comercial/menu.xml:7` para la misma feature | N/A — no es un error de código, es un cambio de ubicación en el árbol de menús respecto al intento anterior | Confirmar que la nueva ubicación (dentro de "Pedidos") es la deseada frente a la antigua (raíz de la app) |
| Bajo | `views/menu.xml:10` vs `leulit_compras/views/menu.xml:10` | Inconsistencia de nomenclatura entre los dos módulos gemelos creados en el mismo commit: aquí `"Facturas de Ventas"` (plural, "V" mayúscula), en `leulit_compras` `"Facturas de compra"` (singular, minúscula) — y el precedente comentado de `leulit_comercial` usaba `"Facturas de venta"` (singular) | N/A — cosmético, pero dos módulos hermanos con distinto criterio de naming es ruido de mantenibilidad | Unificar criterio, p. ej. `"Facturas de venta"` para simetría con `"Facturas de compra"` |
| Bajo | `__manifest__.py`, `views/menu.xml` | No verificable sin entorno: existencia real y `sequence` de los xmlids `sale.sale_order_menu` y `account.action_move_out_invoice_type` en el core Odoo 17 instalado, y si `sale.sale_order_menu` es realmente un contenedor (y no un ítem hoja con acción propia) | Si algún xmlid no existiera o hubiera cambiado, `./upd_module.sh leulit_ventas dev --install` fallaría con `ValueError: External ID not found`; si `sale.sale_order_menu` fuera un ítem hoja, el nuevo menú aparecería anidado bajo él en vez de como hermano entre "Pedidos" y "Equipos de ventas" como dice el comentario | Ejecutar la instalación en `dev` y confirmar que carga sin error y en la posición esperada (ver sección 5) |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Alto, a confirmar] Menú sin `groups` — posible regresión de visibilidad

**Código actual** (`addons/leulit_ventas/views/menu.xml:8-14`):

```xml
<menuitem
    id="menu_leulit_ventas_facturas"
    name="Facturas de Ventas"
    parent="sale.sale_order_menu"
    action="account.action_move_out_invoice_type"
    sequence="25"
/>
```

**Por qué importa**: en Odoo, la visibilidad de un `ir.ui.menu` se evalúa por
su propio campo `groups_id`, no por herencia del padre — un menú sin
`groups_id` es visible para cualquier usuario interno que pueda navegar hasta
él, independientemente de qué grupo tenga restringida la raíz de la app. Lo
único que "sube" en la jerarquía es lo contrario: un padre se muestra si
tiene al menos un hijo visible. El mensaje del commit `4a6d767d` justifica la
ausencia de `groups` diciendo que "las raíces de Compras y Ventas ya están
gateadas a sus grupos de administrador, así que la audiencia es la de los
menús hermanos" — pero eso no se sostiene por sí solo: si algún hermano de
este menú dentro de `sale.sale_order_menu` tampoco lleva `groups` (plausible,
es el patrón estándar de core Odoo para submenús de "Pedidos"), entonces "la
audiencia de los menús hermanos" es en la práctica "cualquier usuario con
acceso al menú Ventas", no un grupo administrador. La visibilidad efectiva
del menú, en última instancia, sí queda acotada por si el usuario tiene
lectura sobre `account.move` (Odoo oculta automáticamente los ítems de menú
cuya acción apunta a un modelo sin acceso de lectura para el usuario) — pero
esa acotación depende de un `ir.model.access.csv`/regla que vive en otro
módulo (`account`, o el rol/grupo custom que en este ERP otorgue acceso a
`account.move`), fuera del alcance de `leulit_ventas`, y no es una protección
explícita ni documentada en este módulo.

**Evidencia dentro de este mismo repo**: `addons/leulit_comercial/menu.xml`
contiene (comentado, inactivo) un intento anterior de exactamente esta misma
funcionalidad:

```xml
<menuitem id="leulit_20230214_1233_menuitem"
        name="Facturas de venta"
        action="account.action_move_out_invoice_type"
        parent="sale.sale_menu_root"
        sequence="10" groups="sales_team.group_sale_salesman"/>
```

Esa versión anterior sí restringía explícitamente a
`sales_team.group_sale_salesman`. La versión nueva en `leulit_ventas`
reimplementa la misma idea sin esa restricción y además cambia el `parent`
(de `sale.sale_menu_root` a `sale.sale_order_menu`). No puedo determinar solo
leyendo código si quitar `groups` fue una decisión deliberada al crear el
módulo nuevo o un descuido — de ahí que lo marque "a confirmar" en vez de
darlo por bug cerrado. Es exactamente el mismo patrón que en el módulo gemelo
`leulit_compras` (ver `addons/leulit_compras/PLAN_REVISION.md §3.1`), así que
la decisión debería tomarse de forma consistente para ambos.

**Fix propuesto** (mínimo, replicando el patrón ya usado en el repo):

```diff
     <menuitem
         id="menu_leulit_ventas_facturas"
         name="Facturas de Ventas"
         parent="sale.sale_order_menu"
         action="account.action_move_out_invoice_type"
         sequence="25"
+        groups="sales_team.group_sale_salesman"
     />
```

No propongo un grupo concreto de forma definitiva porque no sé qué audiencia
querías realmente (todo el equipo de ventas, solo responsables, un rol
`leulit` específico...) — ver pregunta en la sección 5.

### 3.2 [Medio] Ausencia de dependencia de `leulit`

**Código actual** (`addons/leulit_ventas/__manifest__.py:9-12`):

```python
"depends": [
    "sale",
    "account",
],
```

Comparado con el resto de módulos `leulit_*` inspeccionados en este repo
(`leulit_almacen`, `leulit_comercial`, `leulit_planificacion`), todos
dependen de `leulit` aunque solo sea por convención/transitividad de roles.
`leulit_ventas` no lo hace (igual que su gemelo `leulit_compras`).
Funcionalmente no es un bug — el módulo no importa nada de
`leulit.utilitylib` ni usa sus grupos — pero rompe el patrón documentado en
`CLAUDE.md` del proyecto ("every `leulit_*` module depends on it"). Lo dejo
como pregunta abierta en la sección 5 en vez de "corregirlo" yo, porque
añadir la dependencia sin necesidad real sería ruido.

## 4. Plan de acción (orden de prioridad)

1. **[Alto, a confirmar]** Decidir el grupo/audiencia correcto para
   `menu_leulit_ventas_facturas` y añadir `groups="..."` en
   `views/menu.xml:8-14` — bloqueado hasta tu respuesta (sección 5). Tomar la
   misma decisión para el módulo gemelo `leulit_compras` a la vez, por
   consistencia.
2. **[Bajo, a confirmar]** Decidir si `parent` debe ser
   `sale.sale_order_menu` (actual) o `sale.sale_menu_root` (como el intento
   anterior comentado en `leulit_comercial`) — mismo bloqueo.
3. **[Bajo]** Unificar el criterio de nomenclatura del menú
   ("Facturas de Ventas" vs "Facturas de venta"/"Facturas de compra") entre
   `leulit_ventas` y `leulit_compras`.
4. **[Medio, a confirmar]** Decidir si añadir `"leulit"` a `depends` en
   `__manifest__.py:9-12` por consistencia con el resto del repo, o dejarlo
   así por no ser necesario.
5. **[Verificación, sin código que tocar]** Instalar el módulo en `dev`
   (`./upd_module.sh leulit_ventas dev --install`) y confirmar en el log que
   no hay `ValueError: External ID not found` para `sale.sale_order_menu` ni
   `account.action_move_out_invoice_type`, y que el menú aparece en la
   posición esperada (entre "Pedidos" y "Equipos de ventas").
6. **[Opcional, housekeeping fuera de alcance estricto]** El código comentado
   en `addons/leulit_comercial/menu.xml:3-22` (el intento anterior de esta
   misma feature, ya inerte) queda huérfano ahora que existen `leulit_ventas`
   y `leulit_compras` — señalado aquí porque afecta directamente a la
   decisión del punto 1, pero limpiarlo es un cambio en `leulit_comercial`,
   fuera del alcance de esta revisión; no lo toco sin que me lo pidas
   explícitamente.

## 5. Dudas / no verificable sin entorno

1. **¿El menú "Facturas de Ventas" debe ser visible para todos los usuarios
   con acceso a la app Ventas, o solo para un subconjunto (p.ej.
   `sales_team.group_sale_salesman`, como en el intento anterior comentado en
   `leulit_comercial`)?** Esto es una decisión de negocio/seguridad que no
   puedo resolver leyendo código: necesito saber a qué grupo de usuarios
   quieres exponer el listado de facturas de cliente desde la app de Ventas.
2. **¿El `parent` correcto es `sale.sale_order_menu` (el usado ahora) o
   `sale.sale_menu_root` (el usado en el intento anterior, ya comentado, de
   `leulit_comercial`)?** Cambia dónde aparece el menú en el árbol; no puedo
   evaluar cuál es "el correcto" sin saber la intención de UX.
3. **¿Fue intencional no depender de `leulit`?** No cambia el comportamiento,
   pero rompe la convención del repo; quiero confirmar antes de proponer
   tocarlo.
4. **Existencia real de los xmlids `sale.sale_order_menu` y
   `account.action_move_out_invoice_type` en el core Odoo 17 instalado**, y
   si `sale.sale_order_menu` es un contenedor o un ítem hoja con acción
   propia (afecta a si el nuevo menú queda como hermano o como hijo anidado
   de "Pedidos"). Localicé un checkout de Odoo 17 en
   `/Users/emiloalvarez/Work/PROYECTOS/ODOO-SOURCES/odoo-17.0` en esta
   máquina, fuera del directorio de trabajo de esta revisión
   (`addons/leulit_ventas/`), así que no lo he leído sin tu permiso. Si
   quieres que lo verifique contra ese código fuente en vez de (o además de)
   una instalación real en `dev`, dime y lo hago en una pasada aparte.
5. **`sequence="25"` y el comentario "entre 'Pedidos' (20) y 'Equipos de
   ventas' (30)"** (`views/menu.xml:4-7,13`): no he podido confirmar los
   valores reales de `sequence` de esos menús hermanos en el core instalado —
   solo se puede verificar instalando el módulo y mirando el menú
   renderizado, o leyendo el core Odoo (ver punto 4).

## 6. Relación con `leulit_comercial` (nota del encargo)

`leulit_ventas` no toca `models/account_move.py` ni ningún otro Python de
`leulit_comercial` — es solo un `<menuitem>` que reutiliza la acción estándar
`account.action_move_out_invoice_type` tal cual. Por tanto, **no hereda** los
hallazgos críticos ya reportados en `addons/leulit_comercial/PLAN_REVISION.md`
(`sale.origin` sobre recordset multi-registro, `save_from_app()` sin control
de acceso): esos afectan a la creación/escritura de `account.move`, no a la
navegación de menú que añade este módulo. La única relación real es la de
diseño de menú ya cubierta en las secciones 3.1 y 5 (precedente comentado en
`leulit_comercial/menu.xml`).
