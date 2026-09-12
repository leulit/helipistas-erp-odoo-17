# Revisión de código — `leulit_parte_privado`

Revisión estática (sin entorno Odoo disponible). Alcance: únicamente ficheros
bajo `addons/leulit_parte_privado/`. Todo lo que depende de código de otro
módulo (`leulit_operaciones`, `leulit_esignature`, `leulit`) se ha leído solo
para verificar el comportamiento real de lo que este módulo importa; no se ha
tocado ni se propone tocar nada fuera de `leulit_parte_privado`.

Fecha de revisión: 2026-09-10. Commit de referencia: working tree actual de
`main` (ver `git status` — el único fichero modificado en el repo,
`leulit_etiquetas.xml`, no pertenece a este módulo).

## 1. Resumen ejecutivo

8 hallazgos: **1 crítico**, **1 alto**, **3 medios**, **3 bajos**. El
crítico está en el propio manejador de errores de `finalizar()`
(`env.invalidate_all()` tras un `cr.rollback()` manual) y puede romper
justo la garantía que el módulo dice ofrecer ("si falla, el vuelo queda
cancelado y no bloquea el helicóptero/piloto"). El alto es de seguridad
(acceso de lectura sin restringir a todo `sale.order`). Ningún hallazgo
implica que el módulo toque el workflow de `leulit.vuelo` — se ha verificado
explícitamente que es 100% aditivo (ver §5).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `wizard/parte_privado_wizard.py:138` | `env.invalidate_all()` sin `flush=False` tras `cr.rollback()` | Cualquier `UserError` de la cadena B (o de cualquier eslabón tras el primer commit) | `self.env.invalidate_all(flush=False)` |
| Alto | `security/ir.model.access.csv:3` | Lectura sin dominio sobre todo `sale.order` | Usuario con solo `ROperaciones_parte_privado` lee cualquier presupuesto vía API/otras vistas | `ir.rule` que restrinja a `flag_flight_part=True` |
| Medio | `wizard/parte_privado_wizard.py:140` | Al cancelar, se pisa `comentarios` del operador con el mensaje de error | Fallo tardío con observaciones ya escritas en el wizard | Concatenar en vez de sobrescribir |
| Medio | `chains/vuelo_chain_privado.py:66-79` | Orden Descanso/Helicóptero invertido respecto a `initChainToCerrado` original | Vuelo con dos problemas simultáneos (helicóptero bloqueado + descanso incumplido) | Confirmar si es intencional; si no, reordenar |
| Medio | `tests/test_parte_privado.py:80-83` | `test_flujo_completo` se salta en silencio si faltan datos maestros | BD de pruebas sin piloto/presupuesto/helicóptero válidos | Usar fixtures/factories deterministas en vez de depender de datos incidentales |
| Bajo | `menu.xml:4-6` | Modificación de `groups_id` de un menú ajeno (`leulit.leulit_20200618_1104_menuitem`) no se revierte al desinstalar | Desinstalar `leulit_parte_privado` | Documentado como trade-off conocido; sin acción salvo que se quiera un script de desinstalación |
| Bajo | `wizard/parte_privado_wizard.py:16,19` | Dominios de `helicoptero_id`/`presupuesto_vuelo` no filtran estado operativo / compañía | Operador elige helicóptero en taller o presupuesto de otra compañía | Añadir filtros adicionales en el dominio (UX, no bloquea nada crítico) |
| Bajo | `wizard/parte_privado_wizard.py:42` | Selección arbitraria si el partner del piloto tiene &gt;1 usuario activo | Partner del piloto vinculado a dos `res.users` activos | Edge case raro; solo documentar o añadir `UserError` si hay más de uno |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] `env.invalidate_all()` tras `cr.rollback()` puede anular el propio rollback o enmascarar el error real

**Fichero:** `wizard/parte_privado_wizard.py:134-142`

```python
except Exception as e:
    # ponytail: los handlers hacen cr.commit(), no hay rollback total sin editarlos (invariante spec §2).
    # Se vuelve al último commit y el vuelo queda cancelado para no bloquear helicóptero/piloto.
    self.env.cr.rollback()
    self.env.invalidate_all()
    if vuelo.exists() and vuelo.estado != 'cerrado':
        vuelo.sudo().write({'estado': 'cancelado', 'comentarios': 'Parte piloto privado fallido: %s' % e})
        self.env.cr.commit()
    raise
```

`odoo/api.py` (Odoo 17, verificado en el código fuente local en
`/Users/emiloalvarez/Work/PROYECTOS/ODOO-SOURCES/odoo-17.0/odoo/api.py:719-728`):

```python
def invalidate_all(self, flush=True):
    """ Invalidate the cache of all records.
    :param flush: whether pending updates should be flushed before invalidation.
        It is ``True`` by default, which ensures cache consistency.
        Do not use this parameter unless you know what you are doing.
    """
    if flush:
        self.flush_all()
    self.cache.invalidate()
```

`flush_all()` recalcula todos los campos computados pendientes de todo el
entorno (`_recompute_all()`) y escribe en BD todos los campos "sucios" en
caché de **todos** los modelos tocados en la transacción — usando el mismo
cursor que **acaba de ser revertido** en la línea anterior. Es decir: el
código hace `rollback()` y, en la siguiente línea, con los parámetros por
defecto, intenta volver a escribir en BD cualquier cambio que siguiera en
caché sin flushear en el momento de la excepción (campos relacionados/
computados de `vuelo`, del helicóptero, del presupuesto, etc., que no se
hubieran flusheado ya por un `search()` intermedio — el autoflush de Odoo
cubre parte pero no la totalidad de las escrituras pendientes).

Dos consecuencias posibles, ambas malas:

1. Si el flush tiene éxito, puede **reintroducir en BD parte de lo que el
   rollback pretendía deshacer**, contradiciendo la garantía documentada en
   el README ("Qué queda si falla" — "se vuelve al último commit").
2. Si el flush falla (por ejemplo porque algún dato en caché ya no es
   consistente con el estado post-rollback), la excepción nueva se propaga
   **antes** de llegar a `vuelo.sudo().write({'estado': 'cancelado', ...})`
   y antes del `raise` final — el usuario ve un error interno distinto del
   real, y **el vuelo puede quedar sin cancelar**, bloqueando el
   helicóptero/piloto: exactamente lo que este bloque de código existe para
   evitar.

**Fix propuesto:**

```python
self.env.cr.rollback()
self.env.invalidate_all(flush=False)
```

**Cómo verificarlo cuando haya entorno:** el propio test
`tests/test_parte_privado.py::test_flujo_completo` (paso 1, "fallo tardío")
ejercita exactamente esta rama. Tras el fix, ejecutar:

```bash
docker exec -ti helipistas_odoo_17 odoo -u leulit_parte_privado -d productiu --test-enable --test-tags=/leulit_parte_privado --stop-after-init
```

y confirmar que `test_flujo_completo` pasa sin depender de que
`test_flujo_completo` se salte por falta de datos maestros (ver hallazgo
medio §2, fila `tests/test_parte_privado.py:80-83`).

### 3.2 [ALTO] Acceso de lectura sin restricción a `sale.order`

**Fichero:** `security/ir.model.access.csv:3`

```csv
access_parte_privado_sale_order,sale.order lectura parte privado,sale.model_sale_order,leulit.ROperaciones_parte_privado,1,0,0,0
```

`ir.model.access.csv` concede permisos a nivel de **modelo completo**. El
dominio `[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)]`
que limita qué presupuestos aparecen en el desplegable del wizard
(`wizard/parte_privado_wizard.py:19`) es solo un filtro de UI/`name_search`;
no es una restricción de acceso. Cualquier usuario con únicamente el grupo
`ROperaciones_parte_privado` tiene, a nivel de ORM/API, `perm_read=1` sobre
**todos** los `sale.order` de la base de datos — incluyendo precios,
descuentos, cliente, márgenes — vía XML-RPC, debug mode, u otra vista que
liste `sale.order` sin dominio.

El README dice explícitamente que este grupo "no implica ningún otro rol de
operaciones" y que el usuario solo debería ver "el menú nuevo", lo que
sugiere que se pretendía un rol estrecho — este acceso de lectura amplio
contradice esa intención.

**Fix propuesto** (dentro de este módulo, sin tocar `sale.order` en otros
módulos):

```xml
<record id="parte_privado_sale_order_rule" model="ir.rule">
    <field name="name">Parte privado: solo presupuestos NCO de vuelo</field>
    <field name="model_id" ref="sale.model_sale_order"/>
    <field name="groups" eval="[(4, ref('leulit.ROperaciones_parte_privado'))]"/>
    <field name="domain_force">[('flag_flight_part','=',True)]</field>
</record>
```

**Duda para el usuario:** ¿se acepta restringir el acceso a solo los
presupuestos con `flag_flight_part=True` (coherente con el dominio ya usado
en el wizard), o se prefiere mantener lectura completa porque en la
práctica todo operador con este grupo ya tiene otro rol comercial? No se
puede decidir solo leyendo el código — ver §5.

## 4. Plan de acción (orden sugerido para una sesión posterior)

1. **[Crítico]** `wizard/parte_privado_wizard.py:138` — cambiar
   `self.env.invalidate_all()` por `self.env.invalidate_all(flush=False)`.
   Cambio de una línea, sin riesgo de romper nada más.
2. **[Alto]** `security/ir.model.access.csv` — añadir el `ir.rule` de §3.2
   sobre `sale.order` (pendiente de confirmar alcance del dominio con el
   usuario, ver duda en §5).
3. **[Medio]** `wizard/parte_privado_wizard.py:140` — no sobrescribir
   `comentarios`; concatenar el motivo del fallo al texto que ya hubiera
   escrito el operador, p. ej.:
   ```python
   nota_fallo = 'Parte piloto privado fallido: %s' % e
   comentarios = '\n'.join(filter(None, [vuelo.comentarios, nota_fallo]))
   vuelo.sudo().write({'estado': 'cancelado', 'comentarios': comentarios})
   ```
4. **[Medio]** `tests/test_parte_privado.py` — sustituir la dependencia de
   datos maestros incidentales en `test_flujo_completo` por fixtures
   creados en el propio test (helicóptero, presupuesto NCO, tipo de vuelo),
   para que el camino crítico (incluido el fix del punto 1) se ejecute
   siempre en CI en vez de saltarse en silencio.
5. **[Medio, pendiente de confirmación]** `chains/vuelo_chain_privado.py:66-79`
   — decidir si el orden Descanso→Helicóptero debe alinearse con
   `initChainToCerrado` (Helicóptero→Descanso) o si el orden actual es
   deliberado; ajustar solo si se confirma que no lo es.
6. **[Bajo]** `wizard/parte_privado_wizard.py:16,19` — opcional, añadir a
   los dominios del wizard filtros de estado operativo del helicóptero y de
   compañía del presupuesto, para adelantar el rechazo a la UI en vez de a
   mitad de cadena.
7. **[Bajo]** Documentar (por ejemplo en el propio README, sección "Qué
   queda si falla") que desinstalar el módulo no revierte el `groups_id`
   añadido a `leulit.leulit_20200618_1104_menuitem` en `menu.xml:4-6`; solo
   si en algún momento se decide desinstalar el módulo en producción.

## 5. Dudas / no verificable sin entorno

- **Alcance del `ir.rule` sobre `sale.order` (hallazgo §3.2):** ¿se
  restringe a `flag_flight_part=True`, a algo más amplio, o se deja como
  está porque en la práctica los usuarios de este grupo siempre tienen
  también un rol comercial? Es una decisión de negocio, no técnica.
- **Orden de handlers en `chain_to_cerrado()` (`chains/vuelo_chain_privado.py:66-79`):**
  Descanso corre antes que Helicóptero, al revés que en
  `leulit_operaciones/models/leulit_vuelo.py::initChainToCerrado()`
  (Helicóptero antes que Descanso). Funcionalmente no cambia qué se valida
  — solo qué mensaje de error ve el usuario primero si hay dos problemas a
  la vez. No hay comentario en el código que indique si el cambio de orden
  es deliberado (a diferencia de las otras omisiones/diferencias, que sí
  están comentadas explícitamente con "ponytail:"). Requiere confirmación.
- **Diseño de impersonación vía OTP (no es un hallazgo nuevo, es una nota
  de contexto):** cualquier usuario con el grupo `ROperaciones_parte_privado`
  puede firmar un vuelo completo en nombre de **cualquier** piloto marcado
  como `privado`, usando el OTP real del piloto obtenido
  programáticamente (`user.get_otp()`, sin que el piloto lo introduzca).
  Esto es exactamente la funcionalidad pedida y está documentado con
  detalle en el README (secciones "Flujo de `finalizar()`" y "Cliente móvil"),
  así que no se reporta como vulnerabilidad — se deja constancia aquí solo
  para que quede explícito que el riesgo residual (un operador con este
  grupo puede fabricar/firmar partes de cualquier piloto privado, sin
  gesto de consentimiento del piloto en cada vuelo) es un riesgo aceptado
  por diseño y no un descuido de este módulo.
- **Ejecución real del test tras el fix del punto crítico:** no se ha
  podido ejecutar `test_flujo_completo` (no hay Odoo local). La predicción
  de que el bug de `invalidate_all()` afecta a ese test es una deducción de
  lectura de código (comportamiento documentado de `odoo/api.py` en el
  fuente de Odoo 17 instalado localmente), no una confirmación en runtime.
  Ejecutar en el Docker de pruebas del usuario tras aplicar el fix, como se
  indica en §3.1.

## Categorías sin hallazgos / no aplicables

- **Reports/QWeb:** el módulo no define ningún `report/` propio (reutiliza
  el informe PTV/POV existente de `leulit_operaciones` vía la maquinaria de
  firma, sin tocarlo). Nada que revisar aquí.
- **Controladores HTTP / cron jobs:** el módulo no define ninguno. El
  README menciona una futura app móvil que atacaría el mismo wizard por
  JSON-RPC, pero eso vive fuera de este módulo (no hay controlador en este
  addon todavía).
- **Rendimiento:** sin hallazgos propios de este módulo. `finalizar()`
  opera sobre un único vuelo por ejecución (no hay bucles sobre
  recordsets grandes, no hay `search()` sin `limit` en código propio del
  módulo); el coste real de las cadenas vive en los handlers importados de
  `leulit_operaciones`, fuera de alcance de esta revisión.
- **Workflow de `leulit.vuelo` (restricción de diseño no negociable):**
  verificado explícitamente — este módulo no hereda `leulit.vuelo` para
  sobrescribir sus métodos de transición de estado, no importa ni modifica
  `initChainToPostvuelo`/`initChainToCerrado`/`wkf_act_postvuelo`/
  `wkf_act_cerrado` de `leulit_operaciones`, y construye sus propias cadenas
  (`chain_to_postvuelo`/`chain_to_cerrado` en `chains/vuelo_chain_privado.py`)
  encadenando instancias de los mismos handlers **importados**, más un
  handler propio (`DatosGeneralesPrivadoHandler`) que replica — sin
  modificar el original — el subconjunto de comprobaciones aplicable a un
  vuelo NCO transcrito. El único campo añadido a `leulit.vuelo`
  (`models/leulit_vuelo.py`) es un `Many2one` nuevo
  (`privado_introducido_por`), puramente aditivo. Cumple la restricción.
