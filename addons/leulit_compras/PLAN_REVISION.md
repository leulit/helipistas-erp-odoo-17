# Revisión de `addons/leulit_compras/` — informe de hallazgos

Fecha de revisión: 2026-09-10. Revisor: agente Claude (revisión de código, sin ejecución de Odoo).

## 1. Resumen ejecutivo

El módulo es minúsculo: `__init__.py` vacío, `__manifest__.py` y un único
`views/menu.xml` (16 líneas, un `<menuitem>`). No hay modelos, wizards,
controladores, crons, reports, ni `security/`. El código en sí no tiene bugs
de Python (no hay Python). El único hallazgo con peso real es de **seguridad/
diseño**: el `<menuitem>` no lleva `groups`, y hay precedente directo en este
mismo repo (código comentado en `leulit_comercial/menu.xml`) de la misma
funcionalidad implementada *con* `groups` explícito — indicio de que su
ausencia aquí puede ser una regresión, no una decisión consciente.

**Recuento**: 0 críticos · 1 alto (a confirmar contigo, ver sección 5) ·
1 medio · 2 bajos.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Alto (a confirmar) | `views/menu.xml:8-14` | `<menuitem>` sin `groups=`, a diferencia del precedente comentado en `leulit_comercial/menu.xml:10-14` que sí restringía a `purchase.group_purchase_manager,purchase.group_purchase_user` | Cualquier usuario interno con acceso a la app Compras (incluidos roles sin permisos de facturación) ve el menú "Facturas de compra"; si además tiene lectura sobre `account.move` por otra vía, accede a datos de facturación sin pasar por un grupo pensado para ello | Añadir `groups="purchase.group_purchase_user"` (o el grupo que decidáis) al `<menuitem>`, replicando el patrón ya usado en `leulit_comercial/menu.xml:14` |
| Medio | `__manifest__.py:9-12` | `depends` no incluye `leulit`, rompiendo la convención del repo ("todo módulo `leulit_*` depende de `leulit`", ver `CLAUDE.md` del proyecto) | Ninguno en runtime (el módulo no usa nada de `leulit`) — es una cuestión de convención/mantenibilidad, no un fallo funcional | Confirmar si es intencional (módulo puramente de vistas, sin necesidad real de `leulit`) o si se debe añadir la dependencia por consistencia |
| Bajo | `views/menu.xml:11` | `parent="purchase.menu_procurement_management"` — distinto del `parent="purchase.menu_purchase_root"` usado en el precedente comentado de `leulit_comercial/menu.xml:13` para la misma feature | N/A — no es un error de código, es un cambio de ubicación en el árbol de menús respecto al intento anterior | Confirmar que la nueva ubicación (dentro de "Pedidos") es la deseada frente a la antigua (raíz de la app) |
| Bajo | `__manifest__.py`, `views/menu.xml` | No verificable sin entorno: existencia real y `sequence`/`groups` de los xmlids `purchase.menu_procurement_management` y `account.action_move_in_invoice_type` en el core Odoo 17 instalado | Si alguno de los dos xmlid no existiera o hubiera cambiado de módulo/nombre en la versión de core instalada, `./upd_module.sh leulit_compras dev --install` fallaría con `ValueError: External ID not found` | Ejecutar la instalación en `dev` y confirmar que carga sin error (ver sección 5) |

## 3. Hallazgos desarrollados

### 3.1 [Alto, a confirmar] Menú sin `groups` — posible regresión de visibilidad

**Código actual** (`addons/leulit_compras/views/menu.xml:8-14`):

```xml
<menuitem
    id="menu_leulit_compras_facturas"
    name="Facturas de compra"
    parent="purchase.menu_procurement_management"
    action="account.action_move_in_invoice_type"
    sequence="10"
/>
```

**Por qué importa**: en Odoo, la visibilidad de un `ir.ui.menu` se evalúa por
su propio campo `groups_id`, no por herencia del padre — un menú sin
`groups_id` es visible para cualquier usuario interno que pueda navegar hasta
él, independientemente de qué grupo tenga restringida la raíz de la app. Lo
único que "sube" en la jerarquía es lo contrario: un padre se muestra si
tiene al menos un hijo visible. Es decir, el razonamiento del mensaje de
commit `4a6d767d` ("las raíces de Compras y Ventas ya están gateadas a sus
grupos de administrador, así que la audiencia es la de los menús hermanos")
no se sostiene por sí solo: si algún hermano de este menú dentro de
`purchase.menu_procurement_management` tampoco lleva `groups` (plausible, es
el patrón estándar de core Odoo para submenús), entonces "la audiencia de los
menús hermanos" es en la práctica "cualquier usuario con acceso al menú
Compras", no un grupo administrador.

**Evidencia dentro de este mismo repo**: `addons/leulit_comercial/menu.xml`
contiene (comentado, inactivo) un intento anterior de exactamente esta misma
funcionalidad:

```xml
<menuitem id="leulit_20230321_1441_menuitem"
        name="Facturas de compra"
        action="account.action_move_in_invoice_type"
        parent="purchase.menu_purchase_root"
        sequence="10" groups="purchase.group_purchase_manager,purchase.group_purchase_user"/>
```

Esa versión anterior sí restringía explícitamente a
`purchase.group_purchase_manager,purchase.group_purchase_user`. La versión
nueva en `leulit_compras` reimplementa la misma idea sin esa restricción y
además cambia el `parent` (de `purchase.menu_purchase_root` a
`purchase.menu_procurement_management`). No puedo determinar solo leyendo
código si el cambio de criterio (quitar `groups`) fue una decisión deliberada
al crear el módulo nuevo o un descuido — de ahí que lo marque "a confirmar"
en vez de darlo por bug cerrado.

**Fix propuesto** (mínimo, replicando el patrón ya usado en el repo):

```diff
     <menuitem
         id="menu_leulit_compras_facturas"
         name="Facturas de compra"
         parent="purchase.menu_procurement_management"
         action="account.action_move_in_invoice_type"
         sequence="10"
+        groups="purchase.group_purchase_user"
     />
```

No propongo un grupo concreto de forma definitiva porque no sé qué audiencia
querías realmente (todo el equipo de compras, solo responsables, un rol
`leulit` específico...) — ver pregunta en la sección 5.

### 3.2 [Medio] Ausencia de dependencia de `leulit`

**Código actual** (`addons/leulit_compras/__manifest__.py:9-12`):

```python
"depends": [
    "purchase",
    "account",
],
```

Comparado con el resto de módulos `leulit_*` inspeccionados en este repo
(`leulit_almacen`, `leulit_comercial`, `leulit_planificacion`), todos
dependen de `leulit` aunque solo sea por convención/transitividad de roles.
`leulit_compras` no lo hace. Funcionalmente no es un bug — el módulo no
importa nada de `leulit.utilitylib` ni usa sus grupos — pero rompe el patrón
documentado en `CLAUDE.md` del proyecto ("every `leulit_*` module depends on
it"). Lo dejo como pregunta abierta en la sección 5 en vez de "corregirlo"
yo, porque añadir la dependencia sin necesidad real sería ruido.

## 4. Plan de acción (orden de prioridad)

1. **[Alto, a confirmar]** Decidir el grupo/audiencia correcto para
   `menu_leulit_compras_facturas` y añadir `groups="..."` en
   `views/menu.xml:8-14` — bloqueado hasta tu respuesta (sección 5).
2. **[Bajo, a confirmar]** Decidir si `parent` debe ser
   `purchase.menu_procurement_management` (actual) o
   `purchase.menu_purchase_root` (como el intento anterior comentado en
   `leulit_comercial`) — mismo bloqueo.
3. **[Medio, a confirmar]** Decidir si añadir `"leulit"` a `depends` en
   `__manifest__.py:9-12` por consistencia con el resto del repo, o dejarlo
   así por no ser necesario.
4. **[Verificación, sin código que tocar]** Instalar el módulo en `dev`
   (`./upd_module.sh leulit_compras dev --install`) y confirmar en el log que
   no hay `ValueError: External ID not found` para
   `purchase.menu_procurement_management` ni `account.action_move_in_invoice_type`,
   y que el menú aparece en la posición esperada (entre "Pedidos de compra" y
   "Proveedores").
5. **[Opcional, housekeeping fuera de alcance estricto]** El código comentado
   en `addons/leulit_comercial/menu.xml:3-22` (el intento anterior de esta
   misma feature, ya inerte) queda huérfano ahora que existe `leulit_compras`
   — señalado aquí porque afecta directamente a la decisión del punto 1, pero
   limpiarlo es un cambio en `leulit_comercial`, fuera del alcance de esta
   revisión; no lo toco sin que me lo pidas explícitamente.

## 5. Dudas / no verificable sin entorno

1. **¿El menú "Facturas de compra" debe ser visible para todos los usuarios
   con acceso a la app Compras, o solo para un subconjunto (p.ej.
   `purchase.group_purchase_manager`, como en el intento anterior comentado
   en `leulit_comercial`)?** Esto es una decisión de negocio/seguridad que no
   puedo resolver leyendo código: necesito saber a qué grupo de usuarios
   quieres exponer el listado de facturas de proveedor desde la app de
   Compras.
2. **¿El `parent` correcto es `purchase.menu_procurement_management` (el
   usado ahora) o `purchase.menu_purchase_root` (el usado en el intento
   anterior, ya comentado, de `leulit_comercial`)?** Cambia dónde aparece el
   menú en el árbol; no puedo evaluar cuál es "el correcto" sin saber la
   intención de UX.
3. **¿Fue intencional no depender de `leulit`?** No cambia el comportamiento,
   pero rompe la convención del repo; quiero confirmar antes de proponer
   tocarlo.
4. **Existencia real de los xmlids `purchase.menu_procurement_management` y
   `account.action_move_in_invoice_type` en el core Odoo 17 instalado en tu
   entorno.** Localicé un checkout de Odoo 17 en
   `/Users/emiloalvarez/Work/PROYECTOS/ODOO-SOURCES/odoo-17.0` en esta
   máquina, fuera del directorio de trabajo de esta revisión
   (`addons/leulit_compras/`), así que no lo he leído sin tu permiso. Si
   quieres que lo verifique contra ese código fuente en vez de (o además de)
   una instalación real en `dev`, dime y lo hago en una pasada aparte.
5. **`sequence="10"` y el comentario "entre 'Pedidos de compra' (6) y
   'Proveedores' (15)"** (`views/menu.xml:6-7,13`): no he podido confirmar
   los valores reales de `sequence` de esos menús hermanos en el core
   instalado — solo se puede verificar instalando el módulo y mirando el
   menú renderizado, o leyendo el core Odoo (ver punto 4).
