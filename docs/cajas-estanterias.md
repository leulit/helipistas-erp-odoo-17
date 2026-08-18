# Cajas y estanterías en el almacén (Odoo)

Estado: **implementado, sin desplegar ni probar**. Vive en `addons/leulit_almacen`.

Responde a «¿en qué estantería y en qué caja está esta pieza?» sin tocar el eje de ubicaciones,
que en este ERP significa el estado Part-145 del material y no dónde está algo físicamente.

El lado app (Flutter ICARUS) está sin implementar y se documenta aparte, en
`HELIPISTAS-APP-ALMACEN/almacen-app/com_leulit_icarus_app/docs/CAJAS-ESTANTERIAS.md`.

---

## 1. Decisiones de diseño (cerradas, no reabrir sin motivo)

**Caja → `stock.quant.package`** (modelo estándar de Odoo)

Ya estaba habilitado en producción (`group_stock_tracking_lot`, ~100 usuarios) y con **0
registros**: campo virgen. `package_id` y `result_package_id` ya existen en `stock.quant` y
`stock.move.line`, así que no hay migración de esquema.

**Estantería → `stock.location` con `usage='view'`**, bajo una raíz propia **por compañía**

Los almacenes de **Icarus** (`ICA`, compañía 2, 4.817 quants con stock) y de **Helipistas**
(`WH-HELIPISTAS`, compañía 1, 52 quants) están separados y sus estanterías no se mezclan. Por eso
hay dos raíces: `Estanterías Icarus` y `Estanterías Helipistas`, cada una con su `company_id`.
La separación la hace la regla multi-compañía de `stock.location`; además,
`stock_quant_package._check_estanteria_company` impide colocar una caja en la estantería de otra
compañía (un usuario con las dos compañías activas, o una llamada por XML-RPC desde la app, sí
podrían hacerlo sin ella).

Es *el* modelo estándar de Odoo para un sitio físico. Trae `barcode` y `company_id` de serie, y
jerarquía por si algún día hacen falta baldas. Cero modelos nuevos.

**Estado del material → se queda donde está**, en el árbol `ICA/Stock/...`

Ese árbol no es geografía: es el estado Part-145 (`Material Nuevo`, `Material Útil`, `Material
Pendiente Decisión`...). Unas 32 comparaciones literales de nombre, repartidas en 8 ficheros,
dependen de él. No se toca.

**Un lote va siempre en una sola caja — criterio de almacén, no negociable**

Un lote nunca se reparte entre dos cajas. Por tanto "esta pieza está en la caja X" tiene siempre
una respuesta única.

La caja se **guarda** en el quant (`package_id`), porque es el modelo estándar de Odoo y no hay
otro sitio donde ponerla sin inventar campos. Pero se **lee** desde la pieza: el calculado
`caja_estanteria` (`models/stock_lot.py`) la resuelve. Guardar y leer en sitios distintos no es
una contradicción: es la mecánica de Odoo por debajo de una regla de almacén más estricta.

Caso límite: un lote con existencias en dos ubicaciones a la vez (son estados Part-145 distintos,
no sitios distintos) tiene dos quants, y cada quant tiene su `package_id`. Por el criterio de
arriba, ambos deben apuntar a la **misma** caja. Medido en producción el 18-08-2026: eso afecta a
unos 50-70 lotes de ~4.800 con stock (**≈1,3 %**), no al 31 % que decía la versión anterior de
este documento — esa cifra no se reproduce con el dominio (cantidad > 0, ubicación interna).

**Código de caja: tecleado por el usuario, único global, con etiqueta QR propia**

Las cajas ya están rotuladas físicamente. La ficha se adapta al almacén, no al revés.

**Estantería obligatoria en la caja**

Una caja siempre está en algún sitio. Se impone en el formulario, no en el modelo (ver §2.1).

Modelos nuevos a crear: **ninguno**. Todo es Odoo estándar.

> **Verificado (fuente Odoo 17)** que una ubicación `usage='view'` no puede contener stock, así
> que nadie podrá mover material a una estantería por error:
> - `stock/models/stock_quant.py:638` — `@api.constrains('location_id') check_location_id` lanza
>   `ValidationError` si el quant cae en una ubicación `view`. Es constraint ORM: aplica también a
>   `sudo().create()`, XML-RPC y a los wizards custom de `leulit_almacen`.
> - `stock/models/stock_move_line.py:63,66` — `location_id` y `location_dest_id` llevan
>   `domain="[('usage','!=','view')]"`: las estanterías no salen en los desplegables.
> - `stock/models/stock_location.py:191` — tampoco se puede convertir a `view` una ubicación que
>   ya contiene productos.
>
> Matiz: la restricción está en el **quant**, no en el `stock.move`. Un movimiento hacia una vista
> se rechaza al validarse (cuando crea el quant), no al crearse.

### Lo que NO se hace

- La etiqueta impresa de la **pieza** no lleva la caja. Va pegada a la pieza, la caja cambia,
  y una etiqueta que miente es peor que una que calla. El QR va en la **caja**.
- La pantalla de certificado (`certificado_page`) **no** lleva campo caja. Decisión explícita:
  lo certificado desde el iPad entra sin caja y se ubica después.
- No se vacía la caja «a mano» al instalar / desinstalar / dar de baja. Es gratis: cuando la
  pieza sale de `Material Nuevo`, su quant allí queda a 0 y el `package_id` se va con él. Si
  salen 1 de 3 unidades, las 2 restantes siguen en su caja. Mecánica nativa, cero código.

---

---

## 2. Qué se ha implementado

Implementado dentro de `addons/leulit_almacen` (no es un módulo aparte: 7 de los ficheros ya
existían allí y varias vistas ya son herencias de las vistas core; un módulo nuevo tendría que
heredar de herencias sin ganar nada). Pendiente de desplegar y probar.

### 1 `estanteria_id` en la caja — `models/stock_quant_package.py` (nuevo)

```python
class StockQuantPackage(models.Model):
    _name = 'stock.quant.package'
    _inherit = 'stock.quant.package'

    _sql_constraints = [('leulit_name_uniq', 'unique(name)', '...')]

    estanteria_id = fields.Many2one('stock.location', string='Estantería',
                                    domain=lambda self: self._domain_estanteria())
```

**`required=True` va en la VISTA, no en el modelo.** A propósito: el botón nativo "Poner en
paquete" (`stock.picking.action_put_in_pack`) crea paquetes sin estantería y con `required` a
nivel de modelo reventaría. Con `required="1"` en el formulario, la regla se aplica donde las
personas crean cajas y el core sigue funcionando.

**Listar las estanterías para la app: `get_estanterias_app`.** La app no puede filtrar las
estanterías por nombre, y esto no es una preferencia de estilo sino una limitación de Odoo:

- `complete_name` de una ubicación `usage='view'` es **solo su propio nombre**, sin la ruta del
  padre. Lo hace `_compute_complete_name` del core (`if location.location_id and location.usage
  != 'view'`). En producción, `ICA` es hija de `Ubicaciones físicas` y su `complete_name` es
  `"ICA"`, no `"Ubicaciones físicas/ICA"`. Las estanterías son `view`, así que una estantería
  colgada de `Estanterías Icarus` tiene `complete_name = "E-01"` a secas: un dominio
  `[('complete_name','like','Estanterías/')]` **nunca** devuelve nada.
- Resolver los xmlid de las raíces desde la app tampoco vale: `ir.model.data` no tiene lectura
  para el usuario interno (regla `ir_model_data user`, `perm_read = false`); solo la tiene
  *Administration / Access Rights*.

Por eso la resolución vive en el servidor, que sí puede usar `env.ref`:

```python
def _domain_estanteria(self):
    raices = ...  # las dos raíces, resueltas por xmlid
    return [('usage', '=', 'view'), ('id', 'child_of', raices.ids), ('id', 'not in', raices.ids)]

@api.model
def get_estanterias_app(self):
    return self.env['stock.location'].search_read(self._domain_estanteria(), ['id', 'name'])
```

`_domain_estanteria` es **el mismo dominio que el campo `estanteria_id`**: un solo sitio decide
qué es una estantería válida, y lo usan igual el desplegable de Odoo y la app. Antes el campo
llevaba `domain="[('usage','=','view')]"`, que ofrecía también `ICA`, `WH-HELIPISTAS` y
`Partner Locations` — cualquier ubicación de tipo vista del sistema.

**Las raíces no se pueden borrar** — `models/stock_location.py`, override de `unlink()`.
`stock.location.location_id` es `ondelete='cascade'` (comprobado en producción, `ir.model.fields`):
borrar una raíz arrastraba en cascada todas las estanterías que cuelgan de ella, y cada caja se
quedaba sin posición. Un clic, sin aviso y sin vuelta atrás. El override lo corta con un mensaje,
salvo cuando el contexto trae `_force_unlink`, que es la marca que pone Odoo al desinstalar un
módulo — sin esa excepción, desinstalar `leulit_almacen` fallaría.

**Y una estantería en uso tampoco** — `estanteria_id` lleva `ondelete='restrict'`. Si tiene cajas
asignadas, Odoo se niega a borrarla. Es la red de seguridad de verdad: aunque alguien saltara el
override anterior, el `RESTRICT` de la FK aborta la transacción entera en la cascada.

Con las dos cosas, la rama "faltan las raíces" de `_domain_estanteria` deja de ser alcanzable en
operación normal. Se queda igualmente, devolviendo dominio vacío y un `warning` en el log en vez
de lanzar excepción: se evalúa al pintar el formulario de caja y una traza ahí dejaría la pantalla
inservible.

El `search_read` corre con los permisos de quien llama, así que la regla multi-compañía de
`stock.location` ya deja fuera las estanterías de la otra compañía — no hay que filtrar por
`company_id` a mano. Y las raíces se pueden renombrar sin romper la app.

### 2 Método para la app — `set_caja_app` en `models/stock_lot.py`

Mismo patrón que `create_adjustment_move_app`: los parámetros llegan por **contexto**
(`self._context.get('args', {})`), no por argumentos posicionales.

Parámetros: `lote_id`, `location_id`, `caja_id` (0/False para quitar la caja).

Comportamiento y errores que **la app tiene que manejar**:

- Falta `lote_id` o `location_id` → `UserError`:
  *"Faltan datos para asignar la caja (pieza y ubicación son obligatorios)."*
- La pieza no tiene existencias en esa ubicación → `UserError`:
  *"La pieza no tiene existencias en esa ubicación."*
- La pieza está repartida en **varias cajas** en esa ubicación → `UserError`:
  *"La pieza está repartida en varias cajas en esa ubicación (X, Y). Resuélvelo desde Odoo antes
  de asignarla por la app."*
- Todo correcto → escribe `package_id` en el quant y devuelve `true`.

Ese tercer caso existe porque un mismo lote en una misma ubicación tiene **un quant por caja**.
La app debe mostrar el mensaje tal cual, no tragárselo.

No genera ningún `stock.move`: la caja es posición física, no estado del material. Como
contrapartida, **el cambio de caja no queda en el histórico de movimientos**.

Detalle no evidente: escribe con `with_context(inventory_mode=False)` porque
`stock.quant._get_forbidden_fields_write()` incluye `package_id` y `write()` lanza `UserError`
si se escribe estando en modo inventario.

### 3 Resto de lo implementado en el ERP

- `data/leulit_estanterias.xml` — dos ubicaciones raíz, `Estanterías Icarus` (compañía 2) y
  `Estanterías Helipistas` (compañía 1), ambas `usage='view'` y `noupdate`. La compañía se
  referencia por id: Icarus no tiene xmlid en la base de datos.
- `models/stock_location.py` — override de `unlink()` que protege las dos raíces (ver arriba).
  Es el único contenido del fichero.
- `models/leulit_asignar_caja.py` + `views/leulit_asignar_caja.xml` — acción masiva
  "Asignar a caja" sobre selección múltiple en cualquier lista de existencias.
- `views/stock_quant_package.xml` — estantería en ficha/lista/búsqueda de cajas, agrupar por
  estantería, y dos acciones (Cajas, Estanterías).
- `views/stock_quant.xml` — columna Estantería y filtro **"Sin ubicar (sin caja)"**.
  La columna Caja, el filtro por caja y el agrupar por caja **ya venían del core** bajo
  `stock.group_tracking_lot`, que ya está activo.
- `views/stock_lot.xml` — campo "Caja / Estantería" en la ficha de pieza (calculado) y columna
  opcional en la lista.
- `views/stock_move_line.xml` — columnas Caja origen/destino en el histórico, y se **muestra**
  `result_package_id` en operaciones detalladas (estaba `column_invisible=1`). Eso es lo que
  permite ubicar la pieza al recepcionarla, sin código extra.
- `security.xml` — accesos para `RBase_almacen`. Ojo: este módulo **no** usa
  `security/ir.model.access.csv`; los permisos son registros `ir.model.access` dentro de
  `security.xml`.
- `menu.xml` — "Cajas" (`RBase_almacen`) y "Estanterías" (`RResponsable_almacen`).
- `report/leulit_etiquetas.xml` + `report/ir_actions_report.xml` — **etiqueta de caja**: campo
  `qr` calculado en `stock.quant.package` (`pyqrcode`, contenido `CAJA | {id} | {nombre}`),
  plantilla QWeb y acción de informe con `binding_model_id`, de modo que aparece en el menú
  **Imprimir** de la ficha y de la lista de cajas. Admite selección múltiple: una etiqueta por
  página. Mismo `paperformat_B8_landscape` que la etiqueta de pieza.

### 4 Búsqueda de cajas para el desplegable de la app

Ninguna preparación: la app hará `searchRead` sobre `stock.quant.package`. La lectura de ese
modelo ya la tiene cualquier usuario interno.

---

## 3. Contrato con la app ICARUS

La app llama a `stock.lot.set_caja_app` vía `OdooApi.callButton`, que envía los parámetros en
`context['args']`. El QR de las cajas usa el prefijo `CAJA|{package_id}|{name}` para que el
lector de la app lo distinga del QR de pieza, que tiene el formato `{id}|{codigo}`.

Los tres `UserError` de la tabla de arriba son parte del contrato: la app debe mostrarlos, no
tragárselos.

---

## 4. Verificación

Lado Odoo (contenedor de test, nunca producción):

```bash
docker exec -ti helipistas_odoo_17 odoo -u leulit_almacen -d <db_test> --stop-after-init
```

Comprobaciones mínimas:

- [x] ~~Confirmar que Odoo 17 impide usar una ubicación `usage='view'`~~ — **verificado en el
      fuente de Odoo 17**, ver §1 nota. No hace falta salvaguarda.
- [ ] `set_caja_app` escribe `package_id` en el quant correcto cuando el lote tiene stock en dos
      ubicaciones (≈1,3 % de los lotes con stock, unos 50-70: probar con uno de ellos).
- [ ] `set_caja_app` con una pieza sin stock en esa ubicación → `UserError`, no traza.
- [ ] Instalar una pieza que está en caja → el quant origen queda a 0 y el destino sin caja.
- [ ] Instalar 1 de 3 unidades → las 2 restantes conservan la caja.
- [ ] `name` de caja duplicado → lo rechaza la constraint.
- [ ] Caja sin estantería → lo rechaza el `required`.
- [ ] Imprimir → Etiqueta de caja sobre una caja: sale el código, la estantería y un QR legible.
- [ ] Lo mismo seleccionando varias cajas en la lista: una etiqueta por página.
- [ ] El QR impreso, leído con el móvil, contiene `CAJA | <id> | <nombre>`.


---

### Verificación estática ya hecha (sin instancia Odoo)

- Los 4 modelos compilan; los 26 XML del manifest parsean; 84 ids XML sin duplicados; refs y
  acciones de menú resueltos.
- Los xpath sobre vistas core se validaron contra el `arch_db` real de producción, no de memoria.
- Los campos `related` no almacenados son buscables en esta instancia (probado con
  `stock.quant.precio`).
- `stock.quant` y `stock.quant.package` tienen lectura para Usuario interno → la ficha de pieza
  no puede dar AccessError por el compute nuevo.
- Las ~32 comparaciones literales de nombres de ubicación siguen idénticas, fichero por fichero.
- Único cambio de comportamiento existente: `column_invisible` de `1` a `0` en
  `result_package_id` de operaciones detalladas. Todo lo demás es aditivo.

---

## 5. Inventario general: fecha y usuario de última revisión

Añadido en agosto de 2026. Responde a «mientras hago el inventario general, ¿qué piezas me faltan
por revisar?».

### 5.1 Decisiones (cerradas)

**El sello va en la pieza (`stock.lot`), no en el quant**

Regla de almacén: un lote se guarda entero en una caja, nunca repartido. Con eso, «esta pieza está
revisada» tiene una respuesta única y no hace falta bajar al quant. Medido además en producción
(18-08-2026):

- 4.857 quants con stock en ubicación interna frente a ~4.871 lotes con stock ⇒ **≈1,0 quants por
  lote**.
- Hay quants duplicados en la *misma* ubicación (lote 6818, `MS35769-31`: 1 ud. + 6 ud., ambos en
  `Material Nuevo`), porque Odoo los parte por `in_date`. Marcar por quant obligaría a tachar dos
  filas para un solo montón físico.
- Un quant a 0 lo acaba borrando el cron de limpieza de Odoo, y con él se iría el sello.

> El «31 %» de la primera versión de §1 quedó corregido: la medición de hoy da ≈1,0 quants por
> lote y ≈1,3 % de lotes en más de una ubicación. Y por criterio de almacén, un lote va siempre en
> una sola caja.

**Sin modelo de campaña de inventario**

«Pendiente» se resuelve filtrando por fecha en el buscador: el martes se empieza, el viernes se
filtra `Último inventario ≥ martes` (hecho) y `< martes o vacío` (pendiente). Nada que declarar,
nada que mantener, y admite varios recuentos al año.

**Sin tabla de histórico**

`stock.lot` ya hereda `mail.thread`. Los dos campos llevan `tracking=True`, así que el chatter de
la pieza guarda el histórico de inventarios anteriores: quién, cuándo y valor anterior.

**`update_stock` no se toca**

El booleano «Actualizado» preexistente es un flag muerto de la migración de 2023: 1.527 a `True`,
de los cuales 1.522 creados en el lote de migración de enero de 2023, último marcado en mayo de
2023, y ningún código lo lee ni lo escribe. Se deja como está — decisión explícita, no se borra
nada.

### 5.2 Qué se ha implementado

`models/stock_lot.py`:

```python
fecha_inventario   = fields.Date(string="Último inventario", tracking=True)
usuario_inventario = fields.Many2one(comodel_name="res.users", string="Inventariado por", tracking=True)

def marcar_inventariado(self):
    return self.write({
        'fecha_inventario': fields.Date.context_today(self),
        'usuario_inventario': self.env.uid,
    })
```

`views/stock_lot.xml`:

- Formulario (`leulit_20221121_1017_form`): los dos campos, justo bajo `update_stock`.
- Lista (`leulit_20221121_1017_tree`): `fecha_inventario` visible, `usuario_inventario` como
  columna opcional.
- Buscador (`leulit_20260818_1200_search`, nuevo, hereda `stock.search_product_lot_filter`):
  ambos campos buscables, filtros **Con stock** y **Sin inventariar**, y agrupar por usuario o
  por fecha.

### 5.3 Contrato con la app ICARUS

Método: `stock.lot.marcar_inventariado`, vía `OdooApi.callButton` sobre los ids de las piezas.
**No lleva parámetros**: la fecha la pone el servidor y el usuario es el de la sesión que llama.
Admite varias piezas en una sola llamada.

Para listar las piezas de una caja, `searchRead` sobre `stock.lot` con `fecha_inventario` y
`usuario_inventario`. Filtrar por caja **no** se hace con `caja_estanteria` (es `compute` con
`store=False`: sirve para mostrar, no para buscar); el dominio correcto, que sí va por SQL, es
sobre la relación:

```python
[('quant_ids.package_id', '=', caja_id), ('quant_ids.quantity', '>', 0)]
```

Y para no arrastrar las ~4.000 fichas de piezas ya instaladas o consumidas (8.963 lotes en total,
~4.871 con stock), filtrar siempre por existencias:

```python
[('quant_ids.quantity', '>', 0), ('quant_ids.location_id.usage', '=', 'internal')]
```

⚠️ **No usar `product_qty` en dominios.** Es `store=False` y su `_search_product_qty` recorre en
Python todos los lotes: la consulta se arrastra.

### 5.4 Verificación pendiente

Sin instancia Odoo local. En el entorno de pruebas:

```bash
docker exec -ti helipistas_odoo_17 odoo -u leulit_almacen -d <db> --stop-after-init
```

Después comprobar:

1. Los dos campos salen en la ficha de la pieza y en la lista de lotes.
2. Los filtros **Con stock** y **Sin inventariar** aparecen en el buscador de Lotes/Nº de serie.
3. `marcar_inventariado` sella fecha y usuario, y el cambio queda anotado en el chatter.
4. Que un lote con existencias en dos ubicaciones tenga la misma caja en ambas.

---

## 6. Puesta en marcha

Orden a seguir. Cada bloque supone que el anterior salió bien.

### 6.1 Actualizar el módulo

En el servidor, dentro del checkout del repo:

```bash
cd /efs/HELIPISTAS-ODOO-17/odoo/addons/helipistas-erp-odoo-17
git pull
./upd_module.sh leulit_almacen prod
```

El script actualiza, avisa si el log trae `ERROR`/`CRITICAL` y reinicia el contenedor. No hace
`pg_dump`: el respaldo es la copia diaria del EFS. Este cambio añade dos columnas y una clave
foránea, nada que reescriba datos existentes, así que no hace falta `--backup`.
Ver `docs/produccion.md`.

### 6.2 Verificar que el `-u` pasó de verdad

Ningún fichero lo dice: el estado está en la base de datos.

```bash
# las columnas nuevas existen
docker exec -i helipistas_postgres psql -U odoo -d productiu -c \
  "SELECT column_name FROM information_schema.columns
    WHERE table_name IN ('stock_lot','stock_quant_package')
      AND column_name IN ('fecha_inventario','usuario_inventario','estanteria_id');"

# las dos raíces se crearon, una por compañía
docker exec -i helipistas_postgres psql -U odoo -d productiu -c \
  "SELECT d.name, l.id, l.company_id, l.usage
     FROM ir_model_data d JOIN stock_location l ON l.id = d.res_id
    WHERE d.module = 'leulit_almacen' AND d.name LIKE 'location_estanterias%';"
```

Tres columnas y dos filas (compañías 2 y 1, `usage = view`). Cero filas = el código está en
disco pero el módulo no se actualizó.

### 6.3 Configurar antes de tocar nada

1. **Crear las estanterías.** Menú *Almacén → Estanterías* (grupo `RResponsable_almacen`).
   El módulo crea las dos raíces **vacías**: hasta que no haya estanterías colgando de ellas,
   el desplegable de caja sale vacío en Odoo y en la app.
   Cada estantería debe llevar **Ubicación padre** = la raíz de su compañía. Sin padre no
   aparece en ningún sitio.
2. **Revisar los grupos.** Quien inventaría necesita `RBase_almacen`; quien mantiene el
   catálogo de estanterías, `RResponsable_almacen`.
3. **Cajas.** Se pueden crear desde Odoo o sobre la marcha desde la app. Si se rotulan antes,
   imprimir las etiquetas: seleccionar en la lista → *Imprimir → Etiqueta de caja*.

### 6.4 Prueba funcional en Odoo, antes de soltar la app

- Formulario de caja: el desplegable de estantería trae **solo** estanterías. Si aparecen
  `ICA`, `WH-HELIPISTAS` o `Partner Locations`, el dominio no se aplicó.
- Crear una caja sin estantería → lo rechaza. Con un código ya existente → lo rechaza.
- Seleccionar varias líneas en *Existencias* → *Asignar a caja*. Comprobar que **no** aparece
  ningún movimiento nuevo en el histórico de la pieza.
- Columna **Estantería** en existencias y filtro **Sin ubicar (sin caja)**.
- Ficha de pieza: campo *Caja / Estantería* relleno, y *Último inventario* / *Inventariado por*.
- Buscador de Lotes: filtros **Con stock** y **Sin inventariar**, y agrupar por *Inventariado por*.
- Con un usuario de Icarus, comprobar que **no** ve las estanterías de Helipistas.
- Borrar una raíz de estanterías → debe negarse con mensaje, no borrar nada.

### 6.5 Requisito de la app — bloqueante

La app **no funciona** hasta que el frontend cambie `findEstanterias` a
`stock.quant.package.get_estanterias_app`. El filtro por nombre que lleva ahora
(`complete_name like 'Estanterías/'`) no puede devolver nada: ver §1.

Después, el ciclo mínimo desde el iPad: escanear QR de caja → escanear pieza → *Revisado* →
comprobar en Odoo que la pieza quedó en esa caja y con fecha y usuario de inventario.
