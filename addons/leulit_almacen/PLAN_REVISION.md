# Revisión de código — `leulit_almacen`

Revisión estática (sin entorno Odoo disponible: sin `odoo-bin`, sin BBDD). Toda afirmación
está justificada leyendo el código del módulo y, cuando hace falta, el comportamiento estándar
documentado de la API de Odoo 17 — nunca ejecutada. Donde ese comportamiento estándar no se
puede dar por cerrado sin una instancia real, se marca explícitamente en la sección 5.

## 1. Resumen ejecutivo

- **Crítico: 2** — mutación de `env.companies` en un compute (`purchase_order_line.py`) y
  copia íntegra de `stock.move._action_assign` del core con logging a nivel ERROR
  (`stock_move.py`).
- **Alto: 8** — bug de `write()` con `vals` compartido entre registros (3 ficheros), compute
  incompleto en `stock_move_line`, `toggle_lock` sin control de acceso server-side, búsqueda de
  ubicación sin filtrar compañía que puede reventar, `sudo()` más amplio de lo necesario en
  `leulit_asignar_caja`, y posible fallo silencioso de numeración por secuencias mal
  compañía-scopeadas (ver Dudas).
- **Medio: 6** — magic numbers sin documentar, validación inconsistente de payloads de la app,
  antipatrón de rendimiento repetido en 7 métodos `_search_*`, mails de cron sin condición de
  contenido, `write()` de `stock.lot` roto en multi-registro.
- **Bajo: 4** — código muerto, comentario obsoleto, uso no idiomático de `search` en vez de
  `browse`, estilo.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/purchase_order_line.py:17` | `self.env.companies = ...` dentro de un compute | Abrir cualquier pedido de compra o su lista de líneas (dispara `_get_cantidades`) | Quitar la línea; usar `with_company()`/`with_context(allowed_company_ids=...)` si hace falta cambiar de compañía |
| Crítico | `models/stock_move.py:32-171` | `_action_assign` es una copia completa del core con `_logger.info`→`_logger.error` | Cualquier reserva de stock (instalar, recibir, transferir) | Eliminar el override; si se necesita el log, hookear con `super()._action_assign()` + log puntual |
| Alto | `models/stock_move.py:20-26`, `models/stock_move_line.py:22-28`, `models/stock_picking.py:19-27` | `write()` reescribe `vals['date'/'date_done']` dentro de un `for` sobre `self` y llama a `super().write(vals)` una sola vez | Escribir `date`/`date_done` sobre 2+ registros con `picking_id.scheduled_date` distinto en la misma llamada | Aplicar el `write` por registro (o agrupar por valor) en vez de mutar `vals` compartido |
| Alto | `models/stock_move_line.py:88-93` | `_get_tipo_instalacion` no inicializa `is_instalacion=False`, asigna a un campo inexistente `location_des`, y no tiene `@api.depends` | Leer/filtrar `is_instalacion` de una `stock.move.line` cuyo destino no es Equipamiento/Salida Almacén | Inicializar `item.is_instalacion = False` antes del `if`; quitar `item.location_des = False`; añadir `@api.depends('location_dest_id')` |
| Alto | `models/purchase_order.py:9-11` | `toggle_lock()` sin control de acceso; solo el botón está `groups=` en la vista | Llamar a `toggle_lock` por RPC/devtools sin pertenecer a `RResponsable_almacen` | Añadir `if not self.env.user.has_group('leulit_almacen.RResponsable_almacen'): raise UserError(...)` dentro del método |
| Alto | `models/stock_picking.py:51` | `location_destino = search([('name','=','Material Nuevo')])` sin `company_id` ni `limit=1` | Existe más de una ubicación llamada "Material Nuevo" (una por compañía) | Filtrar por `company_id` y añadir `limit=1`, igual que `location_origen` en la línea anterior |
| Alto | `models/leulit_asignar_caja.py:35,41` | `.sudo()` sobre `stock.quant.write()` bastante más amplio de lo que exige el bloqueo de `inventory_mode` | Usuario con `RBase_almacen` pero sin `stock.group_stock_user` usa "Asignar a caja" | Confirmar si `sudo()` es necesario solo para el campo, o retirar y comprobar si `with_context(inventory_mode=False)` basta sin sudo |
| Alto (a confirmar) | `views/stock_install.xml:181-189`, `stock_move_certificate.xml:73-81`, `stock_move_scrap.xml` (secuencias) vs `models/*.py` `with_company(2)` | `ir.sequence` con `company_id=1` pero `next_by_code()` se llama siempre `with_company(2)` | Validar/crear un Install/Uninstall/Certificado/Scrap en el entorno de test | Igualar `company_id` de la secuencia a la compañía con la que se resuelve (2), o quitar `company_id` de la secuencia (secuencia global) |
| Medio | `models/leulit_calibracion.py:44-56` | `write()` usa `self.herramienta` sin `ensure_one()`; `create()` indexa `vals['herramienta']` sin comprobar que exista | `write` sobre varias `leulit.calibracion` a la vez (RPC/script); `create` con `fecha_calibracion` pero sin `herramienta` en el mismo `vals` | `ensure_one()` en `write`; usar `vals.get('herramienta')` con guarda en `create` |
| Medio | `models/stock_lot.py:543` | `if item.currency_id.id == 2: precio_unitario = item.precio * 0.9` | Cualquier pieza con esa moneda | Sustituir el id mágico por una referencia/constante documentada, y documentar de dónde sale el 0.9 |
| Medio | `models/stock_lot.py:641` | `if datos['location_id'] != 18:` id de ubicación hardcodeado sin comentario | Entorno donde el id 18 no es esa ubicación (otra BBDD/instalación) | Resolver por xmlid o nombre+compañía, no por id numérico suelto |
| Medio | `models/stock_lot.py:19-26` | `write()`: `self.env['ir.attachment'].search([('rel_production_lot','=', self.id)])` rompe en multi-registro (`self.id` sobre recordset >1) | Editar `rel_docs` sobre varias piezas a la vez | Iterar `for lot in self:` y buscar por `lot.id` |
| Medio | `models/stock_lot.py:626-657`, `stock_move_certificate.py:178-193`, `stock_uninstall.py:202-220` | Acceso directo a `datos['clave']` sin `.get()`/validación (contraste con `set_caja_app`/`set_estanteria_app`, que sí validan) | La app omite una clave del payload | Validar claves obligatorias y lanzar `UserError` explícito, como ya hace `set_caja_app` |
| Medio | `models/stock_lot.py`, `stock_quant.py`, `product_product.py`, `stock_move_line.py` (7 métodos `_search_*`) | `for item in self.search([]): ...` — full scan + cómputo en Python en cada búsqueda/filtro | Filtrar/ordenar por cualquiera de esos campos con miles de lotes/quants | Reescribir como dominio SQL o campo `store=True` con `@api.depends`, igual que se hizo con `caja_id` |
| Medio | `data/stock_production_lot_notify_expiration_date.xml`, `data/stock_warehouse_orderpoint_notify_stock_minimo.xml` | El cron manda el correo aunque no haya nada que reportar (`force_send=True` incondicional) | Cron activado con `email_values` vacío | Solo llamar a `send_mail` si `email_values` no está vacío |
| Bajo | `models/leulit_calibracion.py:53` | `self.env['stock.lot'].search([('id','=',vals['herramienta'])])` en vez de `.browse(...)` | — | Usar `browse` |
| Bajo | `models/stock_move_line.py:91` | `item.location_des = False` — campo inexistente, no hace nada | — | Eliminar la línea |
| Bajo | `models/ir_attachment.py:8` | Comentario `#TODO BeyondCompare from openerp.addons...` obsoleto | — | Eliminar |
| Bajo | Todo el módulo | Estilo muy heterogéneo (una línea de 400+ caracteres, mezclas de comillas) | — | No formatear automáticamente (ver CLAUDE.md del usuario); limpiar solo si se toca esa línea por otro motivo |

## 3. Hallazgos críticos/altos, uno a uno

### 3.1 `purchase_order_line.py:17` — mutación de `env.companies` en un compute

```python
@api.depends('product_id','product_qty')
def _get_cantidades(self):
    self.env.companies = self.env['res.company'].search([('name','in',['Icarus Manteniment S.L.','Helipistas S.L.'])])
    for item in self:
        ...
```

`env.company` / `env.companies` son propiedades de solo lectura en la API estándar de Odoo 17
(`odoo/api.py`, clase `Environment`): no tienen setter. Asignarles un valor debería lanzar
`AttributeError: can't set attribute`. Esto se ejecuta cada vez que se lee `en_stock`,
`en_prevision` o `en_borrador` — es decir, cada vez que se abre un pedido de compra o su línea
(campos no `store`, se recalculan al leer). Si el `AttributeError` es real, **toda vista de
línea de pedido de compra que muestre estos campos está rota**.

Incluso si en algún build de Odoo `Environment` aceptara la asignación (no debería, y no hay
`@companies.setter` documentado en 17.0), los `Environment` son instancias compartidas/cacheadas
por `(cr, uid, context, su)`: mutar `companies` en una de ellas dentro de un compute cambiaría el
contexto multi-compañía para **cualquier otro código que reutilice ese mismo `Environment`**
dentro de la misma request/transacción, no solo para este método. Es peligroso lo consiguiera o
no.

El mismo patrón aparece también 4 veces en `leulit_taller/models/maintenance_request.py` — fuera
de alcance de este módulo, pero es el mismo bug y convendría revisarlo junto con este hallazgo
(ver §5).

**Fix propuesto:**

```python
@api.depends('product_id','product_qty')
def _get_cantidades(self):
    companies = self.env['res.company'].search([('name','in',['Icarus Manteniment S.L.','Helipistas S.L.'])])
    for item in self:
        quant_ids = self.env['stock.quant'].with_context(allowed_company_ids=companies.ids).search([...])
        ...
```

o, si el propósito real es solo buscar `stock.quant`/`stock.picking`/`purchase.order` sin
restricción de compañía activa, usar `.sudo()` puntual o un dominio explícito con
`('company_id', 'in', companies.ids)` en cada búsqueda, en vez de tocar el entorno global.

### 3.2 `stock_move.py:32-171` — `_action_assign` duplica el core

El método completo (140 líneas) reproduce la implementación de `stock.move._action_assign` de
Odoo 17 (mismo flujo: `moves_to_redirect`, `_get_available_move_lines`,
`_update_reserved_quantity`, `_apply_putaway_strategy`...), cambiando únicamente los `_logger.info(...)`
originales por `_logger.error(...)`:

```python
if move._should_bypass_reservation():
    _logger.error('Bypassing reservation for move %s', move.display_name)
    ...
    _logger.error('Reserving move %s', move.display_name)
```

No hay ninguna lógica propia de `leulit_almacen` añadida dentro del método — no toca `caja_id`,
`estanteria_id` ni nada del dominio del módulo. Dos problemas:

1. **Mantenibilidad/riesgo**: cualquier fix o cambio de comportamiento que Odoo publique en
   `_action_assign` (es una de las zonas más sensibles del core: reservas, FEFO/FIFO, packs)
   queda silenciosamente bloqueado por este override. Un futuro upgrade de Odoo no lo notará; el
   módulo seguirá ejecutando la versión congelada de hace 2+ años.
2. **Ruido operativo**: cada reserva de stock normal (instalar una pieza, recibir un pedido,
   transferir) escribe en el log a nivel `ERROR`. En un sistema con alertas basadas en nivel de
   log, esto genera falsos positivos constantes y entierra errores reales entre miles de
   "errores" que no lo son.

**Fix propuesto:** eliminar el override entero y dejar que se use `stock.move._action_assign`
del core sin tocar. Si el propósito original era añadir logging de diagnóstico, hacerlo con un
`_logger.debug`/`_logger.info` alrededor de una llamada a `super()._action_assign(...)`, no
reimplementando el método.

## 4. Plan de acción priorizado

1. **[Crítico]** Confirmar en entorno de test si `self.env.companies = ...` lanza `AttributeError`
   abriendo cualquier pedido de compra; si es así, aplicar el fix de §3.1 en
   `models/purchase_order_line.py:17`. Revisar también los 4 usos idénticos en
   `leulit_taller/models/maintenance_request.py` (fuera de este módulo, coordinar aparte).
2. **[Crítico]** Eliminar el override de `_action_assign` en `models/stock_move.py:32-171`.
3. **[Alto]** Unificar el fix del bug de `write()`/`vals` compartido en `models/stock_move.py:20-26`,
   `models/stock_move_line.py:22-28` y `models/stock_picking.py:19-27`.
4. **[Alto]** Verificar en test si las 4 secuencias (`stock.install`, `stock.uninstall`,
   `stock.move.certificate`, `stock.scrap`) generan de verdad `INS/00001`, `DES/00001`,
   `CERT/00001`, `SCRAP/00001` o caen en `_('New')`. Si fallan, igualar `company_id` de la
   secuencia a la compañía usada en `next_by_code` (o quitarle `company_id`).
5. **[Alto]** Añadir control de acceso server-side a `purchase_order.py::toggle_lock`.
6. **[Alto]** Arreglar `stock_picking.py:51` (`create_moves_to_icarus`): filtrar
   `location_destino` por `company_id` y `limit=1`.
7. **[Alto]** Corregir el compute `_get_tipo_instalacion` en `stock_move_line.py:88-93`.
8. **[Alto]** Revisar con el usuario si `RBase_almacen` puede darse sin `stock.group_stock_user`
   en producción; si es plausible, acotar el `sudo()` de `leulit_asignar_caja.py:35,41`.
9. **[Medio]** Saneado de `leulit_calibracion.py` (`ensure_one`, `vals.get`).
10. **[Medio]** Documentar o corregir los magic numbers de `stock_lot.py:543` (moneda id 2, factor
    0.9) y `stock_lot.py:641` (ubicación id 18) — requiere respuesta de negocio, ver §5.
11. **[Medio]** Validar payloads (`datos.get(...)`) en `create_moves_app`, `create_adjustment_move_app`,
    `stock_move_certificate.action_validate_app`, `stock_uninstall.action_validate_app`.
12. **[Medio]** Sustituir los 7 `_search_*` de escaneo completo por dominios SQL o campos
    `store=True`, priorizando `stock_lot._search_product_qty`/`_search_total_qty` y
    `stock_quant._search_total_qty` (los más usados en listas de existencias).
13. **[Medio]** Condicionar el envío de los dos correos de cron a que `email_values` no esté vacío.
14. **[Bajo]** Limpieza menor: `leulit_calibracion.py:53` (`browse`), `stock_move_line.py:91`
    (borrar `item.location_des = False`), `ir_attachment.py:8` (comentario obsoleto).

## 5. Dudas / no verificable sin entorno

Todo lo siguiente necesita una instancia Odoo real (o al menos una consola `odoo shell`) para
cerrarse con certeza; se documenta aquí en vez de asumirse, tal como se pidió.

1. **`env.companies = ...` (§3.1).** Estoy razonablemente seguro (por la API pública de
   `odoo/api.py` en 17.0) de que `company`/`companies` son propiedades sin setter y que la
   asignación lanza `AttributeError`. No puedo ejecutarlo para confirmarlo. Si por lo que sea
   *no* lanza excepción, el hallazgo sigue siendo válido pero cambia de "probablemente rompe la
   vista" a "corrompe silenciosamente el contexto multi-compañía compartido durante el resto de
   la transacción" — en cualquier caso hay que quitarlo.
2. **Numeración de secuencias (`company_id=1` vs `with_company(2)`).** No tengo certeza total de
   si `ir.sequence.next_by_code()` en 17.0 filtra la búsqueda de la secuencia por
   `company_id in (compañía activa, False)` o solo por `code`. Si filtra por compañía (mi lectura
   más probable de la API estándar), Instalación/Desinstalación/Certificado/Scrap llevan **dos
   años generando referencias `Nuevo`/`New` en vez de `INS/00001` etc.** Comprobación de 30
   segundos en test: crear una Instalación y mirar el campo `Reference`. Si ya muestra
   `INS/xxxxx`, este hallazgo se descarta entero.
3. **Compute con rama sin asignar (`stock_move_line._get_tipo_instalacion`, §2).** No tengo
   certeza de si Odoo 17 lanza una excepción en tiempo de ejecución cuando un método `compute`
   deja el campo sin asignar para algún registro del batch, o si simplemente lo deja en `False`
   silenciosamente. En cualquiera de los dos casos el comportamiento es incorrecto (falta la
   rama `else`), pero la gravedad real depende de esto.
4. **Magic numbers de negocio** (`stock_lot.py:543` moneda id `2` + factor `0.9`; `stock_lot.py:641`
   ubicación id `18`): no puedo saber si son reglas de negocio intencionadas (p. ej. una moneda
   USD con un descuento de conversión fijo del 10%, o una ubicación "Scrap" concreta) o
   copy-paste con un id de una BBDD de desarrollo que no es el de producción. Necesito que el
   usuario confirme el significado antes de tocarlos.
5. **Alcance real del grupo `RBase_almacen`** (§2, hallazgo del `sudo()` en
   `leulit_asignar_caja.py`): la severidad de ese hallazgo depende de si en producción existen (o
   podrían existir) usuarios con `RBase_almacen` pero sin `stock.group_stock_user`. El propio
   `docs/cajas-estanterias.md` (§6.3) dice que son grupos independientes que hay que dar juntos,
   lo que sugiere que sí es una combinación posible, pero no puedo confirmar la configuración real
   de grupos en producción.
6. **Unicidad del nombre "Material Nuevo" entre compañías** (`stock_picking.py:51`): asumo que
   existe una ubicación "Material Nuevo" en más de una compañía porque el árbol ICA/Stock es
   propio de cada almacén y el resto del módulo sí filtra por `company_id` en casos análogos: no
   puedo confirmar sin consultar la tabla `stock_location` real si hoy hay una o dos.
