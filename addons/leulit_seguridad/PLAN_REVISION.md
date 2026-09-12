# Revisión de código — `leulit_seguridad`

Revisión completa de modelos, vistas, seguridad, wizards, cron y reports. Alcance
estrictamente limitado a `addons/leulit_seguridad/`; cuando un hallazgo depende de
código de otro módulo (`leulit_esignature`, `leulit_parte_145`, `mgmtsystem_nonconformity`
OCA…) se señala el impacto pero **no se propone el fix en ese otro módulo**.

Toda afirmación de "esto falla" está basada en lectura de código (imports, `_inherit`,
`depends`, grep de todo el repo para confirmar dónde se define/usa cada símbolo), nunca
en ejecución real (no hay Odoo local disponible).

## 1. Resumen ejecutivo

- **Crítico: 3** — bypass de firma electrónica con OTP hardcodeado expuesto a todo
  usuario RBase; los dos reports QWeb del módulo están rotos cuando se imprimen por la
  vía estándar (solo funcionan si `leulit_esignature` construye el PDF a mano); el
  campo `melref` apunta a un modelo sin `ir.model.access` (confirmado).
- **Alto: 4** — dependencia no declarada (y potencialmente circular) con
  `leulit_esignature` para lógica de vuelo; filtro de anotaciones "activas" con un
  valor de estado que no existe (siempre vacío); dominio roto en "Procedimientos" de
  No Conformidad; `create()` de anomalía puede descartar silenciosamente el
  vuelo/helicóptero elegido por el usuario.
- **Medio: 6** — id hardcodeado sin comprobar existencia + scripts huérfanos
  alcanzables por RPC, patrón de cursor en hilo obsoleto/inconsistente, envío de email
  que traga excepciones sin loguear, emails hardcodeados duplicados, writes en bucle en
  vez de en lote, hilos sin `daemon=True` ni manejo de errores.
- **Bajo: 3** — código muerto, typo CSS, CSS duplicado entre los dos reports.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/leulit_anomalia_scripts.py:17-41` + `security.xml:21-29` | `run_firmar_cerrar_anomalia` compara `otp == notp` con dos valores hardcodeados `'654321'`, y hace `self.env.uid = 14` como fallback; el modelo tiene CRUD completo para `leulit.RBase` (prácticamente todos los empleados) | Cualquier usuario autenticado con acceso ORM/RPC llama `env['leulit.anomalia_scripts'].firmar_cerrar_anomalia(id)` y obtiene una "firma" válida sin OTP real | Restringir el modelo a un grupo técnico/servidor, eliminar el script si es código muerto, o exigir el OTP real del firmante en vez de un par hardcodeado |
| Crítico | `report/ir_actions_report.xml:5-15,18-28` + `report/leulit_informe_anomalia.xml` + `report/leulit_informe_anotacion_technical_log.xml` | Las plantillas QWeb usan variables sueltas (`codigo`, `fecha`, `melref`…) sin `t-foreach="docs"`/`doc.campo`; el módulo no define ningún `_get_report_values` para suministrarlas | Un usuario pulsa "Imprimir" (botón estándar generado por `binding_type=report`) sobre una anomalía/anotación → PDF vacío o excepción, porque solo `leulit_esignature.generarPdfFirmado` construye ese diccionario a mano | Añadir un `AbstractModel` `report.leulit_seguridad.<...>` con `_get_report_values`, o reescribir la plantilla con `t-foreach="docs" t-as="o"` y `o.campo` |
| Crítico | `views/leulit_anomalia.xml:92` (campo `melref`) | `leulit.mel` (modelo de `leulit_parte_145`) no tiene ninguna fila en `ir.model.access` (confirmado por grep en `leulit_parte_145`) | Cualquier usuario abre una anomalía con categoría/MEL → `AccessError` al intentar leer/buscar `leulit.mel` | Fix real en `leulit_parte_145` (fuera de alcance); aquí solo se documenta que rompe `wizard_diferir`/`calc_fecha_limite` |
| Alto | `models/leulit_vuelo.py:18,25,37` | Llama a `haveNoGo` / `get_anomalias_unsigned_by_helicoptero`, definidos solo en `leulit_esignature`, que **no** está en `depends` del manifest — y que además ya depende de `leulit_seguridad`, por lo que añadir la dependencia inversa crearía un ciclo | Instalar/testear `leulit_seguridad` con únicamente sus dependencias declaradas rompe el onchange del parte de vuelo y `wizard_add_anomalia` con `AttributeError` | Requiere decisión de arquitectura (mover los métodos a `leulit_seguridad`) — ver "Dudas" |
| Alto | `models/leulit_vuelo.py:31,38` vs `models/leulit_anotacion_technical_log.py:108` | Filtra `leulit.anotacion_technical_log` por `estado='active'`, valor que no existe en la `Selection` (`edition`/`pending`/`closed`) | El bloque "Anotaciones Technical Log" del parte de vuelo (`views/leulit_vuelo.xml:11-19`) está siempre vacío, aunque existan anotaciones abiertas relevantes para el piloto | Cambiar el dominio al valor real (`estado != 'closed'` o `estado in ('edition','pending')`, a confirmar — ver "Dudas") |
| Alto | `views/mgmtsystem_nonconformity.xml:98` | `domain="[('parent_id','in',('Procedure','Environmental Aspect','Manuals'))]"` sobre `procedure_ids` (M2M a `document.page`) compara el Many2one `parent_id` (id numérico) con literales de texto | El desplegable "Procedimientos" del formulario de No Conformidad nunca encuentra opciones, o el `name_search` lanza error de cast de tipos en PostgreSQL | Cambiar a `('parent_id.name','in',(...))` o resolver los ids reales por xml-id |
| Alto | `models/leulit_anomalia.py:20-33` (`create`) | `vals.update({'helicoptero_id':..., 'vuelo_id':...})` se aplica siempre que `default_vuelo_id` esté en contexto, sin comprobar si `vals` ya trae otro valor (o vacío) puesto explícitamente por el usuario | Se crea una anomalía desde la pestaña del vuelo, el usuario cambia/vacía `vuelo_id` en el propio formulario antes de guardar → su elección se descarta silenciosamente | Usar `vals.setdefault(...)` en vez de `vals.update(...)`, o solo aplicar el default si la clave no está ya en `vals` |
| Medio | `models/mgmtsystem_nonconformity.py:245` | `origin = env['mgmtsystem.nonconformity.origin'].sudo().browse(24)` sin `.exists()` | En una BD donde no exista el id 24 (staging, otra instancia), el `write` posterior con `(4, origin.id)` intenta enlazar un FK inexistente | Buscar el origen por código/xml-id, no por id numérico; comprobar `.exists()` |
| Medio | `models/mgmtsystem_nonconformity.py:235-239` + `models/leulit_anomalia_scripts.py:17-21` | `set_default_origin_on_nonconformity` y `firmar_cerrar_anomalia` no se llaman desde ningún botón/cron/menú de todo el repo (grep completo) | Quedan como scripts huérfanos, solo alcanzables por RPC/consola — en el caso de `firmar_cerrar_anomalia` esto agrava el hallazgo crítico de arriba | Eliminarlos si ya no se usan, o documentarlos y restringir su acceso |
| Medio | `models/leulit_anomalia_scripts.py:24-25` | Usa `api.Environment.manage()` + `self.pool.cursor()`, patrón distinto del resto del repo (incluido este mismo módulo: `mgmtsystem_nonconformity.py:242-243`, y `leulit/models/res_partner.py`), que usan `registry(dbname).cursor()` + `api.Environment(cr, uid, context)` | No verificable sin ejecutar: si `Environment.manage()` ya no existe/es no-op en Odoo 17, el hilo fallaría en cuanto se invocara | Alinear con el patrón `registry(dbname).cursor()` ya usado en el propio módulo |
| Medio | `models/leulit_anomalia.py:98-101` + `models/leulit_anotacion_technical_log.py:59-62` | `wizard_send_email` atrapa cualquier excepción con `except Exception as e: pass`, sin loguear nada | Un fallo de envío (SMTP caído, plantilla rota…) al notificar un cambio de estado a CAMO/oficina técnica pasa completamente desapercibido | Loguear el error, como ya hace `_send_reminder_email` (`leulit_anotacion_technical_log.py:64-71`) |
| Medio | `models/leulit_anomalia.py:94` vs `views/leulit_anotacion_technical_log.xml:135` | Direcciones de correo hardcodeadas y duplicadas con mecanismos distintos: Python usa `context['mail_to']` en bucle, el template de anotación hardcodea `email_to` directo e ignora ese contexto | Cambiar el destinatario exige tocar dos sitios de forma distinta | Centralizar en un parámetro de configuración (`ir.config_parameter` o similar) |
| Medio | `models/leulit_wizard_asign_anomalia.py:22-24` + `models/leulit_wizard_asign_anotacion.py:22-24` | Bucle `for item in self.anomalia_ids: item.write(...)` — un `write()` por registro | Con muchas anomalías/anotaciones seleccionadas en el wizard, N updates en vez de 1 | `self.anomalia_ids.write({'maintenance_request_id': self.rel_maintenance_request.id})` |
| Medio | `models/leulit_anomalia_scripts.py:19-21` + `models/mgmtsystem_nonconformity.py:237-239` | `threading.Thread(...).start()` sin `daemon=True` ni `try/except` alrededor de la lógica del hilo | Un fallo dentro del hilo no queda registrado de forma consistente; el hilo no está marcado como daemon (a diferencia de `leulit/models/res_partner.py`) | Alinear con el patrón ya establecido en `res_partner.py` (`thread.daemon = True` + try/except con log) |
| Bajo | `models/mgmtsystem_verification_line.py:23` | `return False` muerto tras el `return {...}` en `action_get_attachment_view` | — | Eliminar la línea inalcanzable |
| Bajo | `report/leulit_informe_anomalia.xml:35` + `report/leulit_informe_anotacion_technical_log.xml:35` | `.campo1{font-weight: bold; font-size: 13px;º}` — carácter suelto `º` (typo de copiar/pegar), inocuo pero duplicado en ambos ficheros | — | Quitar el carácter |
| Bajo | `report/leulit_informe_anomalia.xml` y `report/leulit_informe_anotacion_technical_log.xml` | Bloque `<style>` casi idéntico (170+ líneas) duplicado entre los dos templates | Cualquier ajuste de estilo hay que replicarlo a mano en los dos ficheros | Factorizar en un `<template>` CSS común y `t-call`-earlo desde ambos |

## 3. Hallazgos críticos/altos — detalle

### 3.1 [CRÍTICO] Firma electrónica falsificable con OTP hardcodeado, expuesta a todo `RBase`

`models/leulit_anomalia_scripts.py`:

```python
def run_firmar_cerrar_anomalia(self,idanomalia):
    with api.Environment.manage():
        new_cr = self.pool.cursor()
        self = self.with_env(self.env(cr=new_cr))
        context = dict(self._context)
        anomalias = self.env['leulit.anomalia'].with_context(context).sudo().search([('id','=',idanomalia)])
        for anomalia in anomalias:
            args={'otp':'654321',
                  'notp':'654321',
                  'modelo':'leulit.anomalia',
                  'idmodelo':anomalia.id}
            context['args']=args
            self.env.uid = 14
            if anomalia.cerrado_por:
                user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',anomalia.cerrado_por.id)])
                self.env.uid = user.id
            self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()
            self.env.cr.commit()
```

`leulit_esignature.SignatureDoc.checksignatureRef()` (fuera de alcance, solo para
justificar el impacto) valida así:

```python
result = datos['otp'] ==  datos['notp']
```

Es decir, compara el OTP contra sí mismo: con `otp='654321'` y `notp='654321'` la
validación siempre pasa. Cualquier usuario con el grupo `leulit.RBase` (prácticamente
todos, ver `security.xml:21-29`) puede invocar
`env['leulit.anomalia_scripts'].firmar_cerrar_anomalia(id)` vía RPC/JSON-RPC y obtener
una firma "válida" con CRS de Part-145 sin ningún control real de identidad, además de
caer en `self.env.uid = 14` (usuario fijo, sin relación documentada con nada) si la
anomalía no tiene `cerrado_por`, o si `cerrado_por` no tiene usuario asociado (búsqueda
vacía → `user.id` es `False` → `self.env.uid = False`).

**Fix propuesto** (dentro de `leulit_seguridad`):
- Restringir `ir.model.access` de `leulit.anomalia_scripts` a un grupo técnico
  reducido (no `RBase`), o
- eliminar el método si es un script de un solo uso ya obsoleto (no tiene caller en
  todo el repo — ver hallazgo Medio más abajo), y
- si se mantiene, no usar un OTP hardcodeado igual a sí mismo ni un `uid` fijo sin
  fallback seguro.

### 3.2 [CRÍTICO] Los reports QWeb del módulo están rotos por el botón "Imprimir" estándar

`report/ir_actions_report.xml` registra ambos reports con `binding_model_id` +
`binding_type="report"`, lo que hace que Odoo añada automáticamente la opción
"Imprimir" en el formulario de `leulit.anomalia` / `leulit.anotacion_technical_log`.

Las plantillas (`report/leulit_informe_anomalia.xml`,
`report/leulit_informe_anotacion_technical_log.xml`) no hacen `t-foreach="docs"
t-as="doc"` en ningún momento; usan directamente nombres sueltos:

```xml
<span t-esc="codigo"/> ... <span t-esc="fecha"/> ... <span t-esc="melref"/> ...
<img t-att-src="'data:image/png;base64,%s' % logo_hlp" .../>
```

El módulo **no define ningún `_get_report_values`** (grep completo, sin resultados) que
inyecte esas variables. La única razón por la que hoy "funcionan" es que
`leulit_esignature` (fuera de alcance) las genera así, a mano, con `res_ids=[]`:

```python
data = {'codigo': item.codigo, 'fecha': item.fecha, ...}
pdf = self.env['ir.actions.report']._render_qweb_pdf(report, [], data=data)[0]
```

Cuando el botón "Imprimir" estándar se pulsa directamente sobre un registro, Odoo llama
a `_render_qweb_pdf(report, res_ids=[id])` **sin ese `data`**, así que ninguna de esas
variables sueltas existe en el contexto de render: el PDF sale vacío en esos campos, o
la generación falla.

**Fix propuesto** (dentro de `leulit_seguridad`): añadir un `AbstractModel`
`report.leulit_seguridad.leulit_2022201900_informe` (y el equivalente para el LOG) con
`_get_report_values(self, docids, data=None)` que construya el mismo diccionario que
hoy solo aporta `leulit_esignature`, o reescribir la plantilla para iterar sobre `docs`
y leer los campos con `o.campo`/`doc.campo` (opción más simple si solo se imprime un
registro cada vez).

### 3.3 [ALTO] Dependencia no declarada — y potencialmente circular — con `leulit_esignature`

`models/leulit_vuelo.py`:

```python
def isHelicopterBlocked(self, helicoptero_id, fechavuelo):
    return self.env["leulit.anomalia"].haveNoGo(helicoptero_id, fechavuelo)

@api.depends('helicoptero_id','fechavuelo')
def _get_anomalias(self):
    for item in self:
        if item.helicoptero_id:
            item.diferido_ids = self.env['leulit.anomalia'].get_anomalias_unsigned_by_helicoptero(item.helicoptero_id.id)
```

`haveNoGo` y `get_anomalias_unsigned_by_helicoptero` solo existen en
`addons/leulit_esignature/anomalia.py` (`_inherit = 'leulit.anomalia'`). El
`__manifest__.py` de `leulit_seguridad` depende de `leulit, leulit_operaciones,
leulit_taller, mgmtsystem_audit, mgmtsystem_hazard_risk` — **no** de
`leulit_esignature`.

Además, `leulit_esignature/__manifest__.py` ya declara `"leulit_seguridad"` en sus
propios `depends`. Añadir `leulit_esignature` a los `depends` de `leulit_seguridad`
crearía un **ciclo de dependencias** que Odoo rechaza al construir el grafo de módulos.

Impacto real: si `leulit_seguridad` se instala/actualiza en un entorno donde
`leulit_esignature` no está instalado (p.ej. un test que solo instala las dependencias
declaradas), el onchange del parte de vuelo y `wizard_add_anomalia` rompen con
`AttributeError: 'leulit.anomalia' object has no attribute 'haveNoGo'`.

**No propongo el fix aquí** porque implica una decisión de arquitectura entre módulos
(mover los métodos a `leulit_seguridad`, o aceptar el acoplamiento implícito y
documentarlo) — ver sección de dudas.

### 3.4 [ALTO] `anotacion_ids` en el parte de vuelo siempre vacío

`models/leulit_vuelo.py:31,38`:

```python
item.anotacion_ids = self.env['leulit.anotacion_technical_log'].search(
    [('helicoptero_id','=',item.helicoptero_id.id),('estado','=','active')])
```

`leulit.anotacion_technical_log.estado` (`models/leulit_anotacion_technical_log.py:108`)
solo admite `edition`/`pending`/`closed`. `'active'` no es un valor posible, así que el
`search` siempre devuelve un recordset vacío. El bloque correspondiente en
`views/leulit_vuelo.xml:11-19` (`invisible="not anotacion_ids"`) nunca se muestra en el
parte de vuelo, ocultando permanentemente anotaciones de technical log abiertas
relevantes para el piloto antes de volar.

**Fix propuesto**: cambiar el dominio al estado real que se quiera mostrar — a
confirmar con negocio (ver "Dudas"), probablemente `('estado','!=','closed')` o
`('estado','in',['edition','pending'])`.

## 4. Plan de acción (orden de ejecución sugerido)

1. **[Crítico]** Restringir o eliminar el acceso RPC a
   `leulit.anomalia_scripts.firmar_cerrar_anomalia` — `security.xml`,
   `models/leulit_anomalia_scripts.py`.
2. **[Crítico]** Añadir `_get_report_values` (o reescribir las plantillas) para que el
   botón "Imprimir" estándar funcione sin depender de `leulit_esignature` —
   `report/leulit_informe_anomalia.xml`, `report/leulit_informe_anotacion_technical_log.xml`.
3. **[Alto]** Resolver la dependencia con `leulit_esignature` para `haveNoGo` /
   `get_anomalias_unsigned_by_helicoptero` — `models/leulit_vuelo.py` (requiere decisión
   de arquitectura, ver Dudas).
4. **[Alto]** Corregir el filtro `estado='active'` de `anotacion_ids` —
   `models/leulit_vuelo.py:31,38` (requiere confirmar el estado correcto, ver Dudas).
5. **[Alto]** Corregir el dominio `parent_id` → `parent_id.name` en
   `views/mgmtsystem_nonconformity.xml:98`.
6. **[Alto]** Cambiar `vals.update(...)` por `vals.setdefault(...)` en
   `models/leulit_anomalia.py:20-33` (`create`).
7. **[Medio]** `mgmtsystem_nonconformity.py:245` — sustituir `browse(24)` por búsqueda
   por xml-id/código con comprobación de existencia.
8. **[Medio]** Decidir si `set_default_origin_on_nonconformity` y
   `firmar_cerrar_anomalia`/`run_firmar_cerrar_anomalia` se eliminan (sin caller en todo
   el repo) o se documentan/restringen.
9. **[Medio]** Alinear `leulit_anomalia_scripts.py` con el patrón
   `registry(dbname).cursor()` ya usado en `mgmtsystem_nonconformity.py` y en
   `leulit/models/res_partner.py`.
10. **[Medio]** Loguear las excepciones en `wizard_send_email` (`leulit_anomalia.py`,
    `leulit_anotacion_technical_log.py`) en vez de `except ... pass`.
11. **[Medio]** Centralizar los emails hardcodeados (`leulit_anomalia.py:94`,
    `leulit_anotacion_technical_log.xml:135`) en un parámetro de configuración.
12. **[Medio]** Sustituir los bucles `for item in ...: item.write(...)` por un único
    `write()` en lote en `leulit_wizard_asign_anomalia.py` y
    `leulit_wizard_asign_anotacion.py`.
13. **[Medio]** Añadir `daemon=True` y try/except con log a los hilos de
    `leulit_anomalia_scripts.py` y `mgmtsystem_nonconformity.py`, siguiendo el patrón de
    `res_partner.py`.
14. **[Bajo]** Limpiar `return False` muerto en
    `mgmtsystem_verification_line.py:23`.
15. **[Bajo]** Quitar el typo `º` y factorizar el CSS duplicado entre los dos reports.

## 5. Dudas / no verificable sin entorno

- **Dependencia circular con `leulit_esignature`** (hallazgo 3.3): no puedo decidir por
  mi cuenta si la solución correcta es mover `haveNoGo` /
  `get_anomalias_unsigned_by_helicoptero` (y el equivalente de anotaciones,
  `get_anotaciones_unsigned_by_helicoptero`) a `leulit_seguridad`, o si el equipo acepta
  que `leulit_seguridad` nunca se instala/testea en producción sin
  `leulit_esignature` y prefiere solo documentarlo. Necesito tu decisión antes de tocar
  nada aquí.
- **Valor correcto para el filtro de "anotaciones activas"** (hallazgo 3.4): infiero por
  el resto del código (`estado in ('pending')` se usa en
  `views/leulit_wizard_asign_anotacion.xml:13` como "anotación abierta pendiente de
  asignar") que el filtro debería excluir `closed`, pero no sé si el diseño original
  quería excluir también `edition` (anotaciones aún en borrador) del bloque del parte de
  vuelo. Lo dejo para confirmar contigo en vez de asumir el comportamiento de negocio.
- **Botones `wizard_cerrar`/`wizard_diferir`/`wizard_pending` sin restricción de grupo
  ni firma** (`views/leulit_anomalia.xml:31-33`): cualquier usuario `RBase` puede cerrar
  o diferir una anomalía directamente desde el formulario, sin pasar por el flujo de
  firma electrónica (`firmar_cerrar_anomalia`). No sé si esto es un "camino rápido"
  interno intencional frente al cierre firmado formal, o si debería exigir el mismo
  control. No lo trato como bug porque no puedo distinguir regla de negocio de descuido
  solo leyendo el código.
- **`api.Environment.manage()` en Odoo 17** (hallazgo medio 9): no tengo acceso al
  código fuente de Odoo 17 en este entorno para confirmar si el método sigue existiendo,
  es un no-op deprecado, o ya fue eliminado. Recomiendo probar
  `run_firmar_cerrar_anomalia` en el entorno Docker de pruebas antes de tocarlo.
- **Reports rotos vía "Imprimir" estándar** (hallazgo 3.2): no puedo confirmar sin
  ejecutar si Odoo 17 lanza una excepción dura (nombre no definido) o renderiza vacío en
  silencio para los `t-esc` de variables inexistentes en el contexto QWeb — en ambos
  casos el resultado es un PDF inútil, pero el síntoma exacto (error visible vs. PDF en
  blanco) solo se puede confirmar en el entorno Docker de pruebas.
