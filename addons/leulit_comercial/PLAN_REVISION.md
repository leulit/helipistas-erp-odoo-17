# Revisión de código — `leulit_comercial` (Odoo 17.0 Community)

Revisión estática (sin entorno Odoo disponible). Módulo pequeño: 1 modelo
extendido (`account.move`), 3 vistas heredadas (`account.move`, `purchase.order`,
`sale.order`), 1 fichero de reports QWeb, 1 `menu.xml` vacío. No define modelos
nuevos, controladores, wizards, crons ni `security/`.

## 1. Resumen ejecutivo

**9 hallazgos**: 2 críticos, 3 altos, 3 medios, 3 bajos (los dos primeros
requieren tu decisión antes de tocar nada — ver §5). El módulo entero gira
en torno a un único fichero, `models/account_move.py` (28 líneas), que
concentra casi todo el riesgo: un `create()` que puede reventar con
`ValueError: Expected singleton` en facturación agrupada de varios pedidos, y
un método `save_from_app()` sin ningún control que permite reescribir
`state`/`partner_id`/`invoice_date` de **cualquier** factura por id.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/account_move.py:16-17` | `sale.origin` sobre recordset multi-registro lanza `ValueError: Expected singleton` | Facturar agrupado ≥2 pedidos de venta en una sola factura (flujo estándar de Odoo) | Usar `sale[:1].origin` o `sale.mapped('origin')` y decidir qué mostrar con varios pedidos |
| Crítico | `models/account_move.py:23-27` | `save_from_app()` escribe `state`/`partner_id`/`ref`/`invoice_date` de cualquier `account.move` por id, sin relación con `self`, sin pasar por `action_post`/`button_draft`, sin validar `datos` | Cualquier llamada `execute_kw`/JSON-RPC a este método por un usuario con permiso de escritura en `account.move` | Ver §3 — requiere decidir diseño, no solo "arreglar" (ver §5) |
| Alto | `models/account_move.py:14-18` | `create()` se ejecuta para **todo** `account.move` (facturas proveedor, asientos varios, pagos, POS...), no solo facturas de venta ligadas a pedidos; hace un `search()` extra en cada alta | Un usuario de Contabilidad sin acceso de lectura a `sale.order` crea una factura de proveedor → `search()` puede lanzar `AccessError` | Filtrar por `move_type in ('out_invoice','out_refund')` antes de buscar, o envolver en `sudo()` si la búsqueda es solo de lectura interna |
| Alto | `models/account_move.py:14-18` | Antipatrón N+1: una `search()` por cada factura creada, en vez de resolver por lotes | Importación/creación masiva de facturas | Sobrescribir con `@api.model_create_multi` y hacer un único `search()` para todos los `result.ids` |
| Alto | `models/account_move.py:16-17` | `result.origin = sale.origin` sobreescribe en silencio cualquier `origin` que ya viniera en `vals` (el campo es escribible desde `create`) | Un caller pasa `vals={'origin': 'X', ...}` en `create()` | Solo sobreescribir si `vals` no trae `origin`, o eliminar el campo custom (ver hallazgo medio de duplicidad con `invoice_origin`) |
| Medio | `views/account_move.xml:11-16` | El formulario muestra a la vez el campo nativo `invoice_origin` (desoculto) y el campo custom `origin` — mismo concepto, valores que pueden divergir | Factura con varios pedidos de origen: `invoice_origin` los agrega todos, `origin` solo el primero (y puede petar, ver crítico #1) | Decidir cuál de los dos es la fuente de verdad y quitar el otro de la vista |
| Medio | `models/account_move.py:24,26` | `_logger.error()` para trazas rutinarias de depuración, en cada llamada a `save_from_app` | Cualquier llamada al método en producción | Bajar a `_logger.debug()` o quitar; no loguear payloads con datos de cliente a nivel ERROR |
| Medio | `views/report_invoice_templates.xml:42-50` | `position="replace"` con contenido vacío sobre `<th>`/`<td>` de cantidad/precio/impuestos, sin ajustar anchos de columna del resto de la tabla heredada | Imprimir "Presupuesto / Pedido sin Detalle" — no se puede verificar el resultado visual sin renderizar | Verificar en entorno de pruebas que la tabla no queda descuadrada (ver §5) |
| Bajo | `models/account_move.py:4` | Imports sin usar: `RedirectWarning, UserError, ValidationError, AccessError` | — | Quitar los que no se usen |
| Bajo | `models/account_move.py:10` | `_name = "account.move"` junto a `_inherit = "account.move"` es redundante (no es el patrón dominante en el resto del repo para este caso) | — | Quitar `_name` si no aporta nada (o dejarlo si el equipo prefiere explicitarlo siempre; es solo estilo) |
| Bajo | `menu.xml` | Fichero íntegro comentado, sin contenido activo | — | Si no hay plan de reactivarlo, eliminarlo del manifest y del módulo |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] `create()` revienta con facturación agrupada de varios pedidos

`models/account_move.py:13-18`:

```python
@api.model
def create(self, vals):
    result = super(AccountMove, self).create(vals)
    sale = self.env['sale.order'].search([('invoice_ids','in',[result.id])])
    result.origin = sale.origin
    return result
```

`sale.order.invoice_ids` es un campo `Many2many` **calculado** (agrega las
facturas de todas las líneas de pedido), no una relación 1-a-1. Odoo permite
generar **una sola factura a partir de varios pedidos de venta** (facturación
agrupada por cliente/condiciones), un flujo estándar accesible desde la
acción "Crear factura" cuando hay varios pedidos seleccionados o cuando
comparten política de facturación/agrupación. En ese caso `sale` contiene
más de un registro.

Acceder a un campo escalar (`Char`) sobre un recordset con `len(self) > 1`
lanza `ValueError: Expected singleton: sale.order(12, 34)` en el ORM de
Odoo — no es un supuesto, es el comportamiento documentado de acceso a
campos no relacionales sobre multi-recordset. Esto revienta `create()`
**para la factura entera**, bloqueando la facturación agrupada de cualquier
cliente con esta configuración.

**Fix propuesto** (dentro del alcance del módulo):

```python
sale = self.env['sale.order'].search([('invoice_ids', 'in', [result.id])])
if sale:
    result.origin = sale[0].origin  # o ', '.join(sale.mapped('origin')) si se quiere agregado
```

Nota: qué mostrar cuando hay varios pedidos (¿el primero? ¿todos
concatenados, como ya hace `invoice_origin` nativo?) es una decisión de
negocio, no puramente técnica — la dejo en la sección 5.

### 3.2 [CRÍTICO] `save_from_app()` permite reescribir cualquier factura sin control

`models/account_move.py:23-27`:

```python
def save_from_app(self):
    _logger.error(self)
    datos = self._context.get('args',[])
    _logger.error(datos)
    self.search([('id','=',datos['factura_id'])]).write({'partner_id':datos['partner_id'],'state':datos['state'],'ref':datos['ref'],'invoice_date':datos['invoice_date']})
    return True
```

Problemas concretos, todos verificables leyendo solo este código:

1. **Bypass del workflow contable**: escribe `state` directamente con
   `write()`, en vez de pasar por `action_post()` / `button_draft()` /
   `button_cancel()`. Odoo genera número de secuencia, valida líneas,
   comprueba fecha de bloqueo contable (`lock_date`), etc. en esos métodos,
   no en un `write()` plano. Un `write({'state': 'posted'})` directo puede
   dejar el asiento contable en un estado inconsistente (sin secuencia
   asignada, sin las comprobaciones habituales). No puedo confirmar desde
   este módulo si el `write()` nativo de `account.move` (definido en el
   módulo `account`, fuera de alcance) bloquea esto — lo tengo como
   pregunta abierta en §5, no como hecho cerrado.
2. **Sin relación con `self`**: el método ignora completamente el
   recordset sobre el que se llama y busca en **toda la tabla**
   `account.move` por `datos['factura_id']`. Cualquier caller con permiso
   de escritura sobre `account.move` (perfil estándar de Facturación/Ventas)
   puede modificar una factura arbitraria, de cualquier compañía, sin que
   el nombre del método deje claro ese alcance.
3. **Bug de tipo**: `datos = self._context.get('args', [])` usa `[]` como
   valor por defecto, pero dos líneas después se indexa como diccionario
   (`datos['factura_id']`). Si el contexto no trae `'args'`, esto lanza
   `TypeError: list indices must be integers or slices, not str` en vez de
   un error controlado. El valor por defecto debería ser `{}`.
4. **Sin manejo de "no encontrado"**: si `factura_id` no existe, `search()`
   devuelve recordset vacío y `write()` sobre vacío no hace nada ni avisa —
   el método devuelve `True` como si hubiera guardado, ocultando el fallo
   al caller (la app cliente cree que guardó y no fue así).
5. **`_logger.error()` para logging rutinario** (línea 24 y 26): loguea el
   recordset completo y el payload crudo (puede incluir datos de cliente)
   a nivel `ERROR` en cada llamada, no solo en fallos.

No encontré ningún caller de `save_from_app` en este repositorio (ni
controlador HTTP, ni cron, ni otro modelo lo invoca) — el nombre sugiere que
lo llama una app externa (móvil/JSON-RPC) que no está en este checkout. Esto
no reduce el riesgo: cualquier método público de un modelo Odoo es invocable
vía `execute_kw`/JSON-RPC por un usuario autenticado con permisos sobre el
modelo, tenga o no callers internos en este repo.

**No propongo un fix cerrado aquí** porque depende de decisiones de
producto (¿se sigue usando esta integración? ¿qué debe poder hacer la app
externa exactamente?) — ver §5.

## 4. Plan de acción (orden sugerido para una sesión posterior)

1. **[CRÍTICO]** Resolver `create()` con `sale` multi-registro —
   `models/account_move.py:16-17`. Bloqueante: rompe la facturación
   agrupada en producción hoy mismo si se da el caso. Requiere antes
   decidir qué mostrar con varios pedidos (§5, pregunta A).
2. **[CRÍTICO]** Decidir el destino de `save_from_app()` —
   `models/account_move.py:23-27`. Requiere tu respuesta a §5 pregunta B
   antes de tocar una línea (endurecer con validaciones/`sudo` acotado, o
   eliminar si es integración muerta).
3. **[ALTO]** Acotar `create()` a `move_type` de factura de venta y
   convertirlo a `@api.model_create_multi` con una única búsqueda por lote
   — `models/account_move.py:14-18`.
4. **[ALTO]** No sobreescribir `origin` si ya viene en `vals` —
   `models/account_move.py:16-17` (mismo bloque que el punto 1, resolver
   junto).
5. **[MEDIO]** Decidir si `origin` (custom) y `invoice_origin` (nativo)
   deben coexistir en el formulario de factura — `views/account_move.xml:11-16`.
6. **[MEDIO]** Bajar `_logger.error` a `_logger.debug` (o quitar) en
   `save_from_app` — depende de la decisión del punto 2.
7. **[MEDIO]** Verificar en entorno de pruebas que el informe
   "Presupuesto / Pedido sin Detalle" no queda con columnas descuadradas —
   `views/report_invoice_templates.xml:42-50`.
8. **[BAJO]** Limpieza: imports sin usar (línea 4), `_name` redundante
   (línea 10), `menu.xml` comentado por completo.

## 5. Dudas / no verificable sin entorno — para repasar contigo

Estas son decisiones de negocio o comportamientos que no puedo cerrar solo
leyendo código; las dejo explícitas en vez de asumir (según se pidió en el
encargo). Te propongo repasarlas una a una, por ejemplo con `grill-me`,
antes de que alguien las implemente:

- **A. `create()` con varios pedidos de origen** (hallazgo crítico 3.1):
  cuando una factura agrupa varios pedidos de venta, ¿qué debe mostrar el
  campo `origin`? ¿el primero, todos concatenados (como ya hace
  `invoice_origin` nativo), o dejarlo vacío en ese caso? Esto también
  resuelve el hallazgo medio de duplicidad con `invoice_origin`.
- **B. `save_from_app()`** (hallazgo crítico 3.2): ¿sigue en uso por alguna
  app externa (¿la app Flutter de parte de vuelo, u otra)? Si sigue en uso:
  ¿qué payload/contrato exacto espera el cliente, y qué controles de
  autenticación/autorización tiene esa app aparte del usuario Odoo con el
  que hace `execute_kw`? Si no está en uso: propongo eliminarlo en vez de
  parchearlo. No puedo decidir esto solo con el código de este módulo.
- **C. Bloqueo de `write()` sobre `state`**: no puedo confirmar sin
  ejecutar Odoo si el `write()` nativo de `account.move` (módulo `account`,
  fuera del alcance de este addon) ya impide o restringe escribir `state`
  directamente fuera de los métodos de transición de estado, o si lo deja
  pasar sin más. Afecta a la severidad real del hallazgo 3.2 — lo trato
  como agravante potencial, no como hecho confirmado.
- **D. Compatibilidad de `create(self, vals)` con creación por lotes**: no
  he podido verificar contra el runtime real de Odoo 17 si una llamada
  interna con `create([{...}, {...}])` (lista) sobre un modelo cuyo
  override usa `@api.model` (no `@api.model_create_multi`) falla, se
  serializa registro a registro por un shim de compatibilidad del ORM, o se
  comporta de otro modo. Lo señalo como antipatrón documentado en
  `.github/copilot-instructions.md` (línea 364) independientemente de esto,
  pero la severidad exacta de un eventual fallo por creación en lote
  necesitaría confirmarse en el entorno Docker de pruebas.
