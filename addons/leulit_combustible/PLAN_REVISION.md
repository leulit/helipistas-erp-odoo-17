# Revisión `leulit_combustible` — Odoo 17 Community

Revisión estática (sin entorno Odoo ejecutable) de todo el addon: `__manifest__.py`,
`models/leulit_ctrl_combustible.py`, `models/leulit_ctrl_combustible_punto.py`,
`security.xml`, `menu.xml`, `views/leulit_ctrl_combustible.xml`,
`views/leulit_ctrl_combustible_punto.xml`. No hay controladores, wizards ni reports en
este módulo.

## 1. Resumen ejecutivo

**15 hallazgos**: 3 críticos, 3 altos, 5 medios, 4 bajos. Los tres críticos son bugs de
cálculo/funcionalidad demostrables leyendo el código (no interpretación de negocio): el
saldo de combustible por punto se sobrescribe en vez de acumularse, el cálculo Jet-A1 por
totalizador filtra con la fecha inicial de AV-Gas, y el aviso automático de combustible
bajo nunca se ejecuta porque no existe ningún `ir.cron` que lo invoque. Los altos son de
seguridad (el modelo de configuración de puntos y el de movimientos permiten CRUD total a
`leulit.RBase`, el grupo base que hereda casi todo el mundo, pese a que el menú sugiere
una restricción que el modelo no aplica) y de rendimiento (compute fields no
almacenados que lanzan `search()` sin límite ni cota temporal por cada registro).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_ctrl_combustible_punto.py:41-44,46-49` | `ctrl_cantidad` asigna (`=`) en vez de acumular (`+=`) el saldo AV-Gas/Jet-A1 | Un punto sin `control_totalizador` con ≥2 movimientos: el saldo mostrado es solo el del último movimiento, no la suma neta | Acumular en variable local y asignar una vez al final del bucle (igual que ya hace `ctrl_cantidad_aceite`) |
| Crítico | `models/leulit_ctrl_combustible_punto.py:74` | Filtro de fecha del bucle Jet-A1 usa `item.fecha_inicial_avgas` en lugar de `item.fecha_inicial_jeta` | Punto con `fecha_inicial_avgas` ≠ `fecha_inicial_jeta` (o `avgas=False` y por tanto `fecha_inicial_avgas` vacía) | Cambiar el campo del dominio a `item.fecha_inicial_jeta` |
| Crítico | `models/leulit_ctrl_combustible_punto.py:111-152` + módulo entero (sin `data/*cron*.xml`) | `cron_aviso_combustible()` está totalmente implementado pero no hay ningún `ir.cron` en el módulo que lo invoque, ni acción/botón manual | Un punto con `gestion_propia=True` cae por debajo del umbral de aviso: nunca se envía el email | Añadir `ir.cron` en `data/` apuntando a `model.cron_aviso_combustible()` e incluirlo en `__manifest__.py` → `data` |
| Alto | `security.xml:14-22` + `menu.xml:17-24` | `leulit.ctrl_combustible_punto` (config: umbrales de aviso, totalizadores iniciales, `flag_otro`) tiene `perm_write`/`perm_unlink`=1 para `leulit.RBase`; la restricción a `ROperaciones_responsable` solo existe en el `menuitem`, no en el modelo | Un usuario RBase sin `ROperaciones_responsable` accede al modelo por otra vista, URL directa o XML-RPC/JSON-RPC y modifica/borra puntos de control | Restringir `perm_write`/`perm_unlink` de ese `ir.model.access` al grupo `leulit.ROperaciones_responsable` (dejar `perm_read` a `RBase` si necesitan consultarlo) |
| Alto | `security.xml:4-12` | `leulit.ctrl_combustible` (histórico de movimientos, con `mail.thread`) da `perm_write`/`perm_unlink`=1 a `RBase` sin ningún `ir.rule` — cualquier usuario puede editar o borrar movimientos de combustible de otros usuarios | Un piloto borra o altera un registro de repostaje introducido por otro usuario; no queda rastro salvo el log de chatter (que también puede reescribirse solo por autor original en algunos casos) | Decisión de negocio requerida (ver sección Dudas) — posibles opciones: quitar `perm_unlink` a `RBase` y dejarlo solo a `ROperaciones_responsable`, o añadir `ir.rule` "solo su propio registro o responsable" |
| Alto | `models/leulit_ctrl_combustible_punto.py:33-58` | Compute fields `store=False` (`ctrl_cantidad`, `ctrl_cantidad_aceite`) ejecutan `search()` sin `limit` ni filtro de fecha, uno por punto y por tipo de combustible | Vista lista de "Puntos" con N puntos: hasta 6N queries de tabla completa de `leulit.ctrl_combustible`, coste creciente con el histórico | Acotar por fecha reciente si el negocio lo permite, o migrar a `store=True` + recomputo por `@api.depends` sobre creación/baja de `leulit.ctrl_combustible` (requiere `related`/inverso), o usar `read_group` para sumar en una sola query por tipo |
| Medio | `views/leulit_ctrl_combustible_punto.xml:37` | `flag_otro` oculto en el form solo a `leulit.RolIT_developer`, pero editable a nivel de modelo por cualquier `RBase` (mismo patrón que el hallazgo de seguridad anterior) | Usuario sin ese grupo edita el campo vía otra vista/API | Mismo fix que el hallazgo de `security.xml:14-22`: restringir el acceso de escritura al modelo, no solo ocultar el campo en la vista |
| Medio | `models/leulit_ctrl_combustible.py` y `..._punto.py` (ambos modelos completos) | Ningún modelo tiene `company_id`; el proyecto es multicompañía (`leulit_almacen` usa `res.company` id 1 y 2) | Si el combustible se gestiona por compañía, puntos/movimientos de una base se mezclan con los de otra | Ver pregunta en sección Dudas — no se puede confirmar sin conocer si el negocio requiere separación por compañía |
| Medio | `__manifest__.py:11` | Dependencia `leulit_operaciones` declarada pero sin ningún uso en el código del módulo (sin referencia a `leulit.vuelo` ni a ningún modelo de operaciones) | Ninguno directo — es una dependencia muerta que infla el grafo de instalación/actualización sin aportar nada hoy | Confirmar con el usuario si es preparación para integración futura (p.ej. combustible ligado a vuelos) o eliminarla del manifest |
| Medio | `models/leulit_ctrl_combustible.py:45-50` | `constraint_from_to_punto_equals` solo compara `from_punto == to_punto`; no cubre el caso "Otros" (ambos `Many2one` vacíos, texto libre `from_otros == to_otros`) | Usuario crea un movimiento con origen y destino "Otros" con el mismo texto libre | Ampliar la constraint para comparar también `from_otros`/`to_otros` cuando los `Many2one` correspondientes están vacíos |
| Medio | `models/leulit_ctrl_combustible.py` (campo `cantidad`) y `..._punto.py` (`from_otros`/`to_otros`) | No hay validación de `cantidad > 0` ni de que `from_otros`/`to_otros` estén rellenos cuando el punto asociado tiene `flag_otro=True` | Se guarda un movimiento con cantidad negativa/cero, o con el punto marcado "Otros" pero el campo de texto vacío | Añadir `@api.constrains` para ambos casos |
| Bajo | `models/leulit_ctrl_combustible_punto.py:112` | `_logger.error("cron_aviso_combustible")` usa nivel ERROR para un simple log de arranque de una ejecución normal | Cada ejecución del cron (una vez esté programado) aparece como error en los logs / puede disparar alertas de monitorización | Cambiar a `_logger.info(...)` o eliminar la línea |
| Bajo | `models/leulit_ctrl_combustible.py:3-8`, `models/leulit_ctrl_combustible_punto.py:3-8` | Imports sin usar en ambos ficheros: `tools, exceptions, registry, AccessError, UserError, RedirectWarning, datetime, threading`; `utilitylib` también sin usar en `leulit_ctrl_combustible.py` | Ninguno funcional — ruido de plantilla copiada de otro módulo | Eliminar los imports no usados |
| Bajo | `models/leulit_ctrl_combustible.py:20-26,40` | Campo `cantidad_ctrl` calculado pero no usado en ninguna vista del módulo ni referenciado en ningún otro sitio del repo | Cada lectura del registro recalcula un valor que nadie consume | Eliminar el campo y su compute, o exponerlo en la vista si tiene un uso previsto |
| Bajo | `models/leulit_ctrl_combustible.py:42` | `informado_por` es `readonly=True` sin excepción — nadie puede corregir el autor de un movimiento mal introducido, ni un responsable en nombre de otro usuario | Un pilot introduce el movimiento con su propio usuario por error y no puede corregirse desde el form | Permitir escritura condicionada a un grupo responsable (p.ej. `readonly` solo si no se pertenece a `ROperaciones_responsable`) |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] Saldo de combustible por punto: sobrescritura en vez de acumulación

`models/leulit_ctrl_combustible_punto.py:34-50`, método `ctrl_cantidad`:

```python
if item.avgas:
    for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'AV-Gas')]):
        if ctrl.from_punto.id == item.id:
            item.cantidad_ctrl_avgas = -ctrl.cantidad
        else:
            item.cantidad_ctrl_avgas = ctrl.cantidad
```

Cada iteración del bucle **reasigna** `item.cantidad_ctrl_avgas` en vez de acumular, así
que al terminar el bucle el campo solo contiene el signo/cantidad del **último** registro
devuelto por `search()` (orden por defecto del modelo `leulit.ctrl_combustible`: `_order =
"fecha DESC, hora DESC"`, es decir el movimiento más reciente), no el saldo neto de todos
los movimientos de ese punto. El mismo patrón se repite para `jeta` en las líneas 45-49.
Se confirma que es un bug de copia y no una decisión deliberada porque el método hermano
`ctrl_cantidad_aceite` (líneas 52-58), añadido después según el historial de git, sí
acumula correctamente con `+=`:

```python
for ctrl in self.env['leulit.ctrl_combustible'].search([('to_punto', '=', item.id),('tipo', '=', 'Aceite')]):
    item.cantidad_ctrl_aceite += ctrl.cantidad
```

**Impacto:** para cualquier punto de combustible gestionado sin totalizador
(`control_totalizador=False`), el valor "Cantidad AV-GAS"/"Cantidad Jet-A1" mostrado en el
formulario (`cantidad_ctrl_avgas`/`cantidad_ctrl_jeta`, visibles cuando
`invisible="((not avgas) or (control_totalizador))"`, ver
`views/leulit_ctrl_combustible_punto.xml:47,57`) no representa el combustible disponible
real. En un operador de helicópteros esto es un dato operativo/de seguridad.

**Fix propuesto** (diff, no aplicado):

```diff
             if item.avgas:
-                for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'AV-Gas')]):
-                    if ctrl.from_punto.id == item.id:
-                        item.cantidad_ctrl_avgas = -ctrl.cantidad
-                    else:
-                        item.cantidad_ctrl_avgas = ctrl.cantidad
+                total = 0
+                for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'AV-Gas')]):
+                    if ctrl.from_punto.id == item.id:
+                        total -= ctrl.cantidad
+                    else:
+                        total += ctrl.cantidad
+                item.cantidad_ctrl_avgas = total
             if item.jeta:
-                for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'Jeta')]):
-                    if ctrl.from_punto.id == item.id:
-                        item.cantidad_ctrl_jeta = -ctrl.cantidad
-                    else:
-                        item.cantidad_ctrl_jeta = ctrl.cantidad
+                total = 0
+                for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'Jeta')]):
+                    if ctrl.from_punto.id == item.id:
+                        total -= ctrl.cantidad
+                    else:
+                        total += ctrl.cantidad
+                item.cantidad_ctrl_jeta = total
```

### 3.2 [CRÍTICO] Cálculo Jet-A1 por totalizador usa la fecha inicial de AV-Gas

`models/leulit_ctrl_combustible_punto.py:60-77`, método `ctrl_cantidad_totalizador`:

```python
if item.jeta:
    cantidad = 0
    for ctrl in self.env['leulit.ctrl_combustible'].search([('to_punto', '=', item.id),('fecha', '>=', item.fecha_inicial_avgas),('tipo', '=', 'Jeta')]):
        cantidad += ctrl.cantidad
    cantidad += item.cantidad_inicial_jeta
    item.cantidad_ctrl_totalizador_jeta = item.totalizador_inicial_jeta + cantidad - item.last_totalizador_jeta
```

El bucle de acumulación para Jet-A1 filtra los movimientos con
`('fecha', '>=', item.fecha_inicial_avgas)` en vez de `item.fecha_inicial_jeta`, pese a
que el modelo define ambos campos por separado (líneas 94 y 102) precisamente porque un
punto puede empezar a gestionar cada combustible en una fecha distinta.

**Impacto:** en cualquier punto donde `fecha_inicial_avgas != fecha_inicial_jeta`, el
cálculo de `cantidad_ctrl_totalizador_jeta` incluye o excluye movimientos Jet-A1
incorrectamente. Caso extremo: un punto con `avgas=False` (no gestiona AV-Gas) tendrá
`fecha_inicial_avgas` vacío (`False`); el dominio `('fecha', '>=', False)` se evalúa en
PostgreSQL de forma no equivalente a "sin filtro" — no puede confirmarse el comportamiento
exacto sin ejecutar el ORM, pero en cualquier caso es un filtro semánticamente erróneo.

**Fix propuesto:**

```diff
             if item.jeta:
                 cantidad = 0
-                for ctrl in self.env['leulit.ctrl_combustible'].search([('to_punto', '=', item.id),('fecha', '>=', item.fecha_inicial_avgas),('tipo', '=', 'Jeta')]):
+                for ctrl in self.env['leulit.ctrl_combustible'].search([('to_punto', '=', item.id),('fecha', '>=', item.fecha_inicial_jeta),('tipo', '=', 'Jeta')]):
                     cantidad += ctrl.cantidad
```

### 3.3 [CRÍTICO] El aviso automático de combustible bajo nunca se ejecuta

`models/leulit_ctrl_combustible_punto.py:111-152` implementa `cron_aviso_combustible()`
completo: recorre los puntos con `gestion_propia=True`, calcula la cantidad disponible
(por totalizador o por control simple), compara contra `aviso_avgas`/`aviso_jeta`, y envía
un email usando la plantilla `leulit_combustible.leulit_aviso_combustible` (definida en
`views/leulit_ctrl_combustible_punto.xml:78-97`).

Sin embargo, en todo el módulo no hay **ningún** fichero de datos con un registro
`ir.cron` (`grep -rn "ir.cron" addons/leulit_combustible/` no devuelve nada), ni está
listado ningún fichero de cron en `__manifest__.py` → `data` (solo
`security.xml`, las dos vistas y `menu.xml`). Tampoco hay ningún botón/acción de servidor
en las vistas que invoque el método manualmente. El método es, por tanto, código muerto en
producción: la funcionalidad de aviso de bajo nivel de combustible parece existir pero
jamás se dispara.

**Fix propuesto** — nuevo fichero `data/leulit_combustible_cron.xml` (patrón ya usado en
el repo, ver p.ej. `addons/leulit_almacen/data/stock_warehouse_orderpoint_notify_stock_minimo.xml`):

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="ir_cron_leulit_combustible_aviso" model="ir.cron">
            <field name="name">LEULIT - Aviso de bajo nivel de combustible</field>
            <field name="model_id" ref="model_leulit_ctrl_combustible_punto"/>
            <field name="state">code</field>
            <field name="code">model.cron_aviso_combustible()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="numbercall">-1</field>
            <field name="active" eval="False"/>
        </record>
    </data>
</odoo>
```

y en `__manifest__.py`:

```diff
     "data": [
         "security.xml",
         "views/leulit_ctrl_combustible.xml",
         "views/leulit_ctrl_combustible_punto.xml",
+        "data/leulit_combustible_cron.xml",
         "menu.xml"
     ],
```

Se propone `active eval="False"` por defecto para que sea el usuario quien decida la
periodicidad y active el cron explícitamente en su entorno — es una decisión de negocio
(frecuencia del aviso) que no se puede fijar por mi cuenta (ver sección Dudas).

### 3.4 [ALTO] `leulit.ctrl_combustible_punto`: CRUD total para `RBase` pese a la restricción de menú

`security.xml:14-22`:

```xml
<record id="leulit_20250422_1047_access_permission" model="ir.model.access">
    <field name="name">Ctrl combustible punto Access</field>
    <field name="model_id" ref="model_leulit_ctrl_combustible_punto"/>
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

`leulit.RBase` es el grupo base del que casi todos los roles funcionales cuelgan vía
`implied_ids` (documentado en `CLAUDE.md` del repo). `menu.xml:17-24` restringe el acceso
al listado de "Puntos" a `groups="leulit.ROperaciones_responsable"`, dando la impresión de
que la configuración de puntos (umbrales de aviso, totalizadores iniciales, `flag_otro`)
está protegida — pero esa restricción es solo de visibilidad de menú, no de seguridad de
modelo. Cualquier usuario `RBase` puede escribir o borrar `leulit.ctrl_combustible_punto`
por otra vía (otra vista que enlace el modelo, la URL directa `/odoo/action-...`, o una
llamada XML-RPC/JSON-RPC externa). Es exactamente el patrón ya señalado como riesgo
conocido en este proyecto (grupo de menú ≠ seguridad de modelo).

**Fix propuesto:**

```diff
     <record id="leulit_20250422_1047_access_permission" model="ir.model.access">
         <field name="name">Ctrl combustible punto Access</field>
         <field name="model_id" ref="model_leulit_ctrl_combustible_punto"/>
-        <field name="group_id" ref="leulit.RBase"/>
-        <field name="perm_read" eval="1"/>
-        <field name="perm_create" eval="1"/>
-        <field name="perm_write" eval="1"/>
-        <field name="perm_unlink" eval="1"/>
+        <field name="group_id" ref="leulit.ROperaciones_responsable"/>
+        <field name="perm_read" eval="1"/>
+        <field name="perm_create" eval="1"/>
+        <field name="perm_write" eval="1"/>
+        <field name="perm_unlink" eval="1"/>
     </record>
+    <!-- Si otros roles (p.ej. pilotos) necesitan CONSULTAR los puntos para elegir
+         origen/destino en un movimiento, añadir aquí una segunda regla de solo lectura
+         para leulit.RBase (perm_create/write/unlink en 0) -->
```

Nótese que el modelo `leulit.ctrl_combustible` (movimientos) usa `from_punto`/`to_punto`
como `Many2one` hacia este modelo, así que **cualquier** usuario que pueda crear un
movimiento necesita como mínimo `perm_read` sobre `leulit.ctrl_combustible_punto` para que
el desplegable funcione — de ahí la nota de añadir una regla de solo lectura para `RBase`
si se restringe `group_id` como arriba.

### 3.5 [ALTO] `leulit.ctrl_combustible`: borrado/edición de movimientos de otros usuarios sin restricción

`security.xml:4-12` da `perm_write`/`perm_unlink`=1 a `leulit.RBase` sobre
`leulit.ctrl_combustible` sin ningún `ir.rule` que limite el dominio (p.ej. "solo mis
propios registros" o "solo si soy responsable"). El modelo hereda `mail.thread` (aporta
trazabilidad de cambios vía chatter) pero eso no impide el `unlink()` — que borra el
registro y su historial de mensajes junto con él. Cualquier usuario con acceso al módulo
puede borrar o modificar el movimiento de combustible introducido por otro compañero.

Este hallazgo se reporta pero **no se resuelve por cuenta propia**: recortar
`perm_write`/`perm_unlink` a todos los `RBase`, o añadir un `ir.rule`, cambia el
comportamiento funcional para todos los usuarios que hoy dependen de poder registrar y
corregir movimientos de combustible libremente — es una decisión de producto (ver Dudas).

### 3.6 [ALTO] Compute fields no almacenados con `search()` sin límite ni cota temporal

`models/leulit_ctrl_combustible_punto.py:33-58` (`ctrl_cantidad`, `ctrl_cantidad_aceite`):
por cada punto y por cada tipo de combustible gestionado (`avgas`, `jeta`, además de
`gestion_aceite`), se ejecuta un `search()` sin `limit` y sin cota de fecha sobre
`leulit.ctrl_combustible`. Al ser `store=False`, se recalculan en cada lectura (apertura de
la vista lista/formulario de "Puntos", cada refresco). Con N puntos configurados esto
significa hasta 6·N queries de escaneo del histórico completo por cada apertura de vista,
sin límite de crecimiento a medida que se acumulan años de movimientos.

**Fix propuesto (a validar con el usuario, cambia el modelo de datos):**
- Opción conservadora: añadir cota de fecha razonable (p.ej. últimos N días) si el negocio
  solo necesita el saldo actual y no el histórico completo — pero esto **cambia el
  resultado** salvo que se combine con un saldo inicial persistido, así que no es un fix
  neutro sin decisión de negocio.
- Opción estructural: pasar estos campos a `store=True` con recomputo dirigido por un
  campo inverso (`compute` + `inverse`/`related` desde `leulit.ctrl_combustible`) o
  mantenerlos no almacenados pero sustituir el bucle Python por `read_group`/`_read_group`
  agrupando por `from_punto`/`to_punto` y sumando en una sola consulta por tipo, en vez de
  iterar registro a registro.

## 4. Plan de acción priorizado

1. **[CRÍTICO]** Corregir `ctrl_cantidad` en `models/leulit_ctrl_combustible_punto.py:34-50` para acumular (`+=`) en vez de sobrescribir.
2. **[CRÍTICO]** Corregir el filtro de fecha Jet-A1 en `ctrl_cantidad_totalizador`, `models/leulit_ctrl_combustible_punto.py:74` (`fecha_inicial_avgas` → `fecha_inicial_jeta`).
3. **[CRÍTICO]** Registrar `cron_aviso_combustible` con un `ir.cron` nuevo (`data/leulit_combustible_cron.xml`) y añadirlo a `__manifest__.py`; confirmar con el usuario la periodicidad deseada antes de activarlo por defecto.
4. **[ALTO]** Alinear `security.xml:14-22` (acceso a `leulit.ctrl_combustible_punto`) con la intención ya expresada en `menu.xml:23` restringiendo `group_id` a `leulit.ROperaciones_responsable`, añadiendo una regla de solo lectura para `RBase` si los pilotos necesitan el desplegable de puntos al crear movimientos.
5. **[ALTO]** Decidir con el usuario la política de `perm_unlink`/`perm_write` de `leulit.ctrl_combustible` (`security.xml:4-12`) antes de tocarla — ver Dudas.
6. **[ALTO]** Revisar el patrón de cómputo de `ctrl_cantidad`/`ctrl_cantidad_aceite` en `models/leulit_ctrl_combustible_punto.py:33-58` para evitar N+1 queries sin cota, una vez decidida la solución de negocio (store vs read_group vs ventana temporal).
7. **[MEDIO]** Igualar el fix del punto 4 para que `flag_otro` (`views/leulit_ctrl_combustible_punto.xml:37`) quede protegido también a nivel de modelo, no solo de vista.
8. **[MEDIO]** Confirmar con el usuario si `leulit.ctrl_combustible`/`leulit.ctrl_combustible_punto` deben llevar `company_id` (multicompañía).
9. **[MEDIO]** Confirmar si la dependencia `leulit_operaciones` en `__manifest__.py:11` es necesaria hoy o se puede retirar.
10. **[MEDIO]** Ampliar `constraint_from_to_punto_equals` (`models/leulit_ctrl_combustible.py:45-50`) para cubrir el caso "Otros" con texto libre idéntico.
11. **[MEDIO]** Añadir `@api.constrains` para `cantidad > 0` y para exigir `from_otros`/`to_otros` cuando el punto asociado tiene `flag_otro=True`.
12. **[BAJO]** Cambiar `_logger.error` por `_logger.info` en `models/leulit_ctrl_combustible_punto.py:112`.
13. **[BAJO]** Limpiar imports sin usar en ambos ficheros de `models/`.
14. **[BAJO]** Eliminar o dar uso real al campo muerto `cantidad_ctrl` (`models/leulit_ctrl_combustible.py:20-26,40`).
15. **[BAJO]** Revisar si `informado_por` debe seguir siendo `readonly=True` sin excepción para responsables.

## 5. Dudas / no verificable sin entorno

- **Política de borrado/edición de movimientos ajenos (#3.5).** No puedo decidir si
  cualquier usuario debe poder borrar/editar movimientos de combustible introducidos por
  otros, o si debe restringirse (por `ir.rule` de "propio registro" o recortando
  `perm_unlink`/`perm_write` a un rol responsable). Cambia el comportamiento actual para
  todos los usuarios — requiere confirmación explícita antes de tocar `security.xml`.
- **Multicompañía (#hallazgo medio 8).** No he encontrado en el módulo ninguna señal de
  que el combustible se gestione por compañía (no hay `company_id`, no hay dominios
  filtrando por `self.env.company`). No puedo confirmar si esto es un hueco real o si el
  negocio gestiona el combustible de forma unificada entre compañías — requiere respuesta
  del usuario.
- **Dependencia `leulit_operaciones` sin uso (#hallazgo medio 9).** Podría ser preparación
  para una integración futura con `leulit.vuelo` (consumo de combustible por vuelo) que
  aún no se ha implementado, en cuyo caso mantenerla es correcto. No hay forma de
  confirmarlo solo leyendo el código de este módulo.
- **Semántica de negocio de `cantidad_ctrl_totalizador_avgas/jeta`** (fórmula
  `totalizador_inicial + cantidad - last_totalizador`, líneas 71 y 77): la fórmula es
  internamente consistente y el único bug detectable por código es el campo de fecha
  equivocado (#3.2); no puedo confirmar sin un caso real de datos si el signo/orden de la
  fórmula representa "combustible restante" o "combustible consumido" tal como el negocio
  espera — lo dejo señalado pero no como bug.
- **Periodicidad del cron de aviso (#3.3).** Propongo `ir.cron` diario e inactivo por
  defecto; la frecuencia real y si debe activarse por defecto en producción es una
  decisión del usuario.
- Ninguno de estos hallazgos se ha podido confirmar ejecutando el módulo (no hay Odoo
  local en este entorno, según las instrucciones del proyecto); todas las afirmaciones se
  basan en lectura de código, `git log` del módulo y grep del resto del repo para
  contrastar dependencias/usos cruzados.
