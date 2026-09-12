# Revisión de código — `leulit_nda`

Revisión estática (sin entorno Odoo disponible) de todo el addon: modelos,
controladores, vistas XML, seguridad, datos, informe QWeb y JS embebido. No
hay wizards ni cron jobs en este módulo.

Dependencias declaradas en `__manifest__.py`: `leulit`, `mail`, `web`.

## 1. Resumen ejecutivo

16 hallazgos: **0 críticos, 5 altos, 5 medios, 6 bajos**. Los altos apuntan
todos al núcleo del módulo (garantizar que el usuario firmó *ese* NDA y que
nadie accede al backend sin firmarlo): el gate solo cubre el webclient
clásico (no XML-RPC/JSON dataset ni llamadas directas a métodos de
`res.users`), un fallo al generar/enviar el PDF deja `nda_firmado=True` en BD
aunque la UI diga que falló, y no hay vínculo entre la firma y la versión
concreta del acuerdo firmado. Ninguno requiere tocar otros módulos para
arreglarse.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Alto | `controllers/main.py` (todo el fichero, ámbito de `NdaHome`) | El bloqueo solo intercepta `Home.web_client` (`/web`); ningún otro punto de entrada al backend lo comprueba | Usuario con sesión válida (cookie) que aún no ha firmado llama directamente a `/web/dataset/call_kw/...`, `/xmlrpc/2/object`, `/longpolling`/`/bus/websocket`, o una app externa (móvil, integración) que no carga el webclient HTML — accede a datos y ejecuta acciones sin firmar el NDA | Documentar el límite explícitamente (ya se apunta en `ARCHITECTURE.md` para bloqueos parciales por pantalla, pero no para APIs); si se requiere bloqueo real de datos, añadir la comprobación en un `ir.http._dispatch()` propio en vez de solo en `Home.web_client` |
| Alto | `models/res_users.py:33`, `:56` | `action_nda_enviar_codigo` / `action_nda_verificar_codigo` no comprueban `self == self.env.user` | Un usuario interno autenticado llama a estos métodos vía `call_kw` genérico pasando el `id` de **otro** `res.users` (no el suyo) — el método usa `self.sudo()`, así que ejecuta igualmente: envía código al email del otro usuario repetidamente (spam) e invalida cualquier código que ese usuario tuviera pendiente de introducir (DoS contra su firma) | Añadir guarda al inicio de ambos métodos: `if self != self.env.user: raise AccessError(_("No autorizado"))` |
| Alto | `controllers/main.py:35-55` + `models/res_users.py:33`, `:56` | Las rutas JSON y las acciones no comprueban `_nda_debe_firmar()` / `not nda_firmado` antes de ejecutar | Un usuario que ya firmó (o una pestaña vieja de `/nda/acuerdo` que sigue abierta tras firmar) vuelve a pulsar "Firmar" → se genera un código nuevo y, al validarlo, se sobrescribe `nda_fecha_firma` con la fecha actual, perdiendo la fecha real de la firma original | Guardar `if not self._nda_debe_firmar(): raise UserError(_("Ya has firmado el acuerdo."))` al principio de `action_nda_enviar_codigo` y `action_nda_verificar_codigo` |
| Alto | `models/res_users.py:74-82` | `_nda_generar_y_enviar_pdf()` se llama **después** de `write({"nda_firmado": True, ...})`, sin try/except; si falla (wkhtmltopdf, `force_send=True` con SMTP caído, etc.) la excepción sube al controlador, que la traga y responde `ok:false`, pero el `write` ya se ejecutó en la misma transacción y se comitea igualmente | Servidor de correo caído o wkhtmltopdf no disponible en el momento de firmar: el usuario ve "No se ha podido verificar el código. Inténtalo de nuevo.", reintenta, pero `nda_firmado` ya es `True` en BD desde el primer intento — en su siguiente `/web` entra sin que se le vuelva a pedir, y puede que nunca reciba el PDF | Aislar el envío del PDF en su propio try/except (loguear y continuar) para que un fallo de notificación no quede oculto tras un mensaje que sugiere que la firma no se realizó — ver snippet en la sección 3 |
| Alto | `models/res_users.py` (campos `nda_*`) + `report/leulit_nda_report.xml:20` + `models/leulit_nda_acuerdo.py:14-16` | No existe ningún campo que registre **qué versión** de `leulit.nda.acuerdo` firmó el usuario; el PDF de confirmación usa `get_current()` en el momento de generarse, no la versión que el usuario realmente leyó en pantalla | Un admin edita el `contenido` del acuerdo activo (o publica una v2) mientras un usuario tiene el flujo OTP a medias (hasta 15 min de margen); el PDF que recibe documenta un texto distinto del que aceptó. Además, si se publica una v2, nadie que firmó la v1 vuelve a ser requerido a firmar — `nda_firmado` es un booleano global sin versión | Añadir `nda_acuerdo_id = fields.Many2one("leulit.nda.acuerdo", copy=False)` en `res.users`, fijarlo al momento de mostrar `/nda/acuerdo` (o al firmar) y usarlo en el informe en vez de `get_current()`; y decidir la política de re-firma al publicar una versión nueva (ver Dudas) |
| Medio | `models/res_users.py:40` | Código OTP generado con `random.randint`, un PRNG no criptográfico (CWE-338) | No es explotable de forma práctica hoy, pero es una mala práctica en un mecanismo de verificación de identidad | Sustituir por `secrets.randbelow(1000000)` (módulo `secrets`, ya en stdlib) |
| Medio | `controllers/main.py:35-44` + `models/res_users.py:39-43` | `/nda/enviar_codigo` no tiene ningún límite de frecuencia; cada llamada resetea `nda_codigo_intentos` a 0 | Un usuario (o alguien con su sesión) puede pedir códigos nuevos sin límite, lo que (a) permite reintentar 5 adivinanzas por cada código nuevo indefinidamente, amplificando el ataque de fuerza bruta descrito en el hallazgo de autorización, y (b) puede usarse para saturar la cola de correo | Añadir un cooldown mínimo entre envíos (p. ej. no permitir un nuevo código si el anterior no ha expirado, o un `ir.config_parameter` con intervalo mínimo) |
| Medio | `controllers/main.py:24-33` + `models/leulit_nda_acuerdo.py:14-16` | Si no hay ningún `leulit.nda.acuerdo` activo, `get_current()` devuelve un recordset vacío y `nda_acuerdo()` no lo comprueba | Un admin desactiva el único registro activo sin crear uno nuevo (o los desactiva todos por error): `/nda/acuerdo` se sirve igualmente, sin texto, y el botón "Firmar" sigue funcionando — el usuario puede "firmar" un acuerdo vacío | Comprobar `if not acuerdo:` en `nda_acuerdo()` y mostrar un error / impedir firmar en ese caso |
| Medio | `controllers/main.py:24` vs `__manifest__.py:9-13` | La ruta `/nda/acuerdo` usa `website=True`, pero el manifest no depende de `website` | Si en algún entorno el módulo `website` no está instalado, no está verificado que `web.frontend_layout` + `no_header`/`no_footer` se comporten igual (ver sección 5, no verificable sin ejecutar) | Quitar `website=True` si no aporta nada (parece innecesario para `web.frontend_layout`), o declarar la dependencia real si se necesita |
| Medio | (módulo completo) | No existe carpeta `tests/` — cero tests automatizados para un módulo que implementa un gate de seguridad | Cualquier regresión futura en `_nda_debe_firmar`, el conteo de intentos o la expiración del código pasaría desapercibida hasta producción | Añadir `TransactionCase` cubriendo: exención de superusuario/no-interno, `nda_firmado=True` exime, expiración de código, 5 intentos agotados, `leulit_nda.enforce=False` |
| Bajo | `models/res_users.py:30-31` | `_nda_debe_firmar()` hace `ir.config_parameter.sudo().get_param(...)` en cada carga de `/web`, sin caché | Coste extra menor por request; no es un problema real al volumen actual del ERP, pero es una query evitable | Cachear con `tools.ormcache` o leer el parámetro una vez por transacción |
| Bajo | `views/leulit_nda_acuerdo_views.xml:21-30` | La vista de lista no expone las versiones desactivadas (`active=False` se filtra por defecto) | Un admin que desactiva una versión antigua al publicar una nueva pierde la visión de histórico en la vista estándar | Añadir un filtro "Archivados" en la búsqueda, o `context="{'active_test': False}"` en la acción |
| Bajo | `data/mail_template_data.xml:9`, `:27` | `email_from` hardcodeado a `erp@helipistas.com` en ambas plantillas | Si cambia el dominio de envío o el SPF/DKIM configurado, hay que tocar código en vez de configuración | Dejar `email_from` vacío (usa el servidor saliente por defecto) o derivarlo de la configuración de la compañía |
| Bajo | `views/templates.xml:41-158` | El JS de la página vive inline en el `<script>` del QWeb en vez de en `static/src/js/` dentro del bundle de assets | Dificulta aplicar una CSP estricta (`script-src 'self'`) y rompe el patrón ya usado en el repo (p. ej. `widget_semaforo_field.js`) de mantener JS en ficheros de assets | Mover el script a `static/src/js/nda_acuerdo.js` e incluirlo en `web.assets_frontend` |
| Bajo | (módulo completo) | El kill-switch `leulit_nda.enforce` solo es accesible editando `ir.config_parameter` en modo Desarrollador | Un admin sin conocimientos técnicos no tiene forma sencilla de desactivar el bloqueo en caliente si el texto legal no está listo (como advierte `ARCHITECTURE.md`) | Exponer un checkbox en Ajustes o en el propio formulario de `leulit.nda.acuerdo` |
| Bajo | `models/res_users.py:39-43` | `nda_codigo` / `nda_codigo_expiracion` no se limpian si el código expira sin que el usuario lo use (quedan en BD hasta el siguiente intento) | Dato obsoleto pero inerte (ya no es válido por expiración); impacto mínimo | Limpiar estos campos también cuando `_nda_debe_firmar` detecta expiración, o dejarlo así si no se considera relevante |

## 3. Hallazgos altos desarrollados

### 3.1 Bloqueo solo cubre `/web` — otros puntos de entrada no pasan por el gate

`controllers/main.py` solo sobrescribe `Home.web_client` (que sirve `/web` y,
según el mapping de rutas del `Home` base, variantes como `/web/login`) y
registra tres rutas propias (`/nda/acuerdo`, `/nda/enviar_codigo`,
`/nda/verificar_codigo`). Ningún otro controlador se toca. Eso significa que
cualquier cliente que hable directamente el protocolo JSON-RPC/XML-RPC de
Odoo contra otros endpoints (`/web/dataset/call_kw/<model>/<method>`,
`/xmlrpc/2/object`, `/xmlrpc/2/common`, `/longpolling` / `/bus/websocket`,
cualquier controlador de otro módulo con `auth="user"`) nunca ejecuta
`_nda_debe_firmar()`, porque ninguno de ellos pasa por `web_client`.

```python
# controllers/main.py — único punto interceptado
class NdaHome(Home):
    @http.route()
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action=s_action, **kw)
        if response.status_code == 200 and request.env.user._nda_debe_firmar():
            return request.redirect("/nda/acuerdo")
        return response
```

Con una sesión de navegador válida (cookie), basta con abrir la consola del
navegador (o usar Postman/curl reutilizando la cookie) y llamar a
`/web/dataset/call_kw` para leer o escribir datos sin haber firmado nunca el
NDA. `ARCHITECTURE.md` (última sección) ya avisa de que el patrón "no sirve
para... bloqueos parciales por registro o por acción", pero esa nota habla de
pantallas dentro del propio webclient, no de que el resto de la API HTTP de
Odoo quede completamente fuera del alcance del bloqueo — vale la pena
dejarlo explícito porque el `summary`/`description` del manifest ("Bloquea
el acceso al backend...") se puede leer como una garantía más fuerte de lo
que realmente ofrece el código.

**No es arreglable dentro de este módulo sin rediseño** (habría que
interceptar en `ir.http._dispatch()`, que afecta a todas las rutas del
sistema, y decidir qué rutas quedan exentas — login, assets, `/nda/*`,
etc.). Lo dejo señalado, no lo implemento, tal como piden las restricciones
de esta revisión.

### 3.2 Sin comprobación de propiedad en `action_nda_enviar_codigo` / `action_nda_verificar_codigo`

```python
# models/res_users.py
def action_nda_enviar_codigo(self):
    """Genera un código de 6 cifras y lo envía por email al usuario."""
    self.ensure_one()
    if not self.email:
        raise UserError(...)
    self.sudo().write({...})
    ...
```

Ninguno de los dos métodos comprueba que `self` sea el usuario que está
ejecutando la llamada. El controlador siempre los invoca sobre
`request.env.user` (correcto), pero al ser métodos públicos de `res.users`
son igualmente invocables vía `call_kw` genérico contra **cualquier** id de
`res.users`, y como internamente usan `.sudo()`, la falta de permisos de
escritura sobre `res.users` no los detiene.

**Fix propuesto:**

```python
def action_nda_enviar_codigo(self):
    self.ensure_one()
    if self != self.env.user:
        raise AccessError(_("No tienes permiso para esta acción."))
    ...

def action_nda_verificar_codigo(self, codigo):
    self.ensure_one()
    if self != self.env.user:
        raise AccessError(_("No tienes permiso para esta acción."))
    ...
```

(recuerda añadir `AccessError` al import de `odoo.exceptions`).

### 3.3 Re-firma posible tras `nda_firmado=True` — pisa `nda_fecha_firma`

Ni la ruta `/nda/enviar_codigo` ni `/nda/verificar_codigo` ni las acciones
que invocan comprueban `_nda_debe_firmar()` (esa comprobación solo se hace
en `nda_acuerdo()`, la página GET). Una pestaña de `/nda/acuerdo` que quedó
abierta después de firmar (o un usuario que vuelve atrás con el navegador)
puede seguir pulsando "Firmar" y completar el flujo de nuevo:

```python
def action_nda_verificar_codigo(self, codigo):
    self.ensure_one()
    user = self.sudo()
    ...
    user.write({
        "nda_firmado": True,
        "nda_fecha_firma": fields.Datetime.now(),   # <- sobrescribe la fecha real de firma
        ...
    })
    user._nda_generar_y_enviar_pdf()                # <- vuelve a generar y enviar el PDF
```

Para un documento cuyo propósito es dejar constancia legal de "cuándo" se
firmó, perder la fecha original de firma es un problema de integridad del
registro de auditoría.

**Fix propuesto:** añadir la guarda al principio de ambos métodos de acción
(mismo sitio que el fix 3.2):

```python
if not self._nda_debe_firmar():
    raise UserError(_("Ya has firmado el acuerdo de confidencialidad."))
```

### 3.4 Fallo al generar/enviar el PDF deja `nda_firmado=True` con respuesta de error al usuario

```python
def action_nda_verificar_codigo(self, codigo):
    ...
    user.write({
        "nda_firmado": True,
        "nda_fecha_firma": fields.Datetime.now(),
        "nda_codigo": False,
        "nda_codigo_expiracion": False,
        "nda_codigo_intentos": 0,
    })
    user._nda_generar_y_enviar_pdf()   # sin try/except
```

```python
# controllers/main.py
@http.route("/nda/verificar_codigo", type="json", auth="user")
def nda_verificar_codigo(self, codigo=None, **kw):
    try:
        request.env.user.action_nda_verificar_codigo(codigo)
        return {"ok": True}
    except UserError as e:
        return {"ok": False, "error": str(e)}
    except Exception:
        _logger.exception("Error verificando el código NDA")
        return {"ok": False, "error": "No se ha podido verificar el código. Inténtalo de nuevo."}
```

`_nda_generar_y_enviar_pdf()` hace `_render_qweb_pdf` (requiere wkhtmltopdf)
y `send_mail(..., force_send=True)` (SMTP síncrono, dentro de la misma
petición HTTP). Si cualquiera de los dos falla, la excepción no está
capturada dentro de `action_nda_verificar_codigo`, así que sube hasta el
`except Exception` genérico del controlador, que la registra en el log y
responde `{"ok": False, ...}` — pero el `write()` anterior ya ejecutó dentro
de la misma transacción, y como el controlador no relanza la excepción (la
captura y devuelve un dict normal), Odoo comitea la petición igualmente. El
usuario ve un mensaje de fallo y probablemente reintenta, pero
`nda_firmado` ya quedó en `True` desde el primer intento: en su siguiente
carga de `/web` entrará sin que se le vuelva a pedir firmar, sin que quede
claro (ni para él ni para un administrador) si realmente recibió el PDF.

**Fix propuesto:** separar la notificación de la firma en sí, para que un
fallo de correo/informe no contradiga el estado real guardado en BD:

```python
def action_nda_verificar_codigo(self, codigo):
    ...
    user.write({
        "nda_firmado": True,
        "nda_fecha_firma": fields.Datetime.now(),
        "nda_codigo": False,
        "nda_codigo_expiracion": False,
        "nda_codigo_intentos": 0,
    })
    try:
        user._nda_generar_y_enviar_pdf()
    except Exception:
        _logger.exception(
            "NDA firmado por %s pero falló la generación/envío del PDF", user.login
        )
        # no relanzar: la firma es válida aunque falle la notificación
    _logger.info("NDA firmado por el usuario %s", user.login)
```

(Import de `logging`/`_logger` ya existe en el fichero.)

### 3.5 Sin vínculo entre la firma y la versión concreta del acuerdo firmado

`res.users` guarda `nda_firmado` (booleano) y `nda_fecha_firma`, pero nunca
qué `leulit.nda.acuerdo` fue el que el usuario leyó y aceptó. El PDF de
confirmación se genera consultando la versión **actual** en el momento de
firmar:

```xml
<!-- report/leulit_nda_report.xml -->
<div t-out="env['leulit.nda.acuerdo'].sudo().get_current().contenido"/>
```

Esto tiene dos consecuencias:

- Si el texto activo cambia entre que el usuario abre `/nda/acuerdo` (donde
  se le muestra `acuerdo = get_current()`) y completa el flujo OTP (hasta
  15 minutos de margen, tiempo de vida del código), el PDF que recibe puede
  no coincidir con lo que realmente leyó en pantalla.
- El campo `version` en `leulit.nda.acuerdo` deja claro que se prevén
  revisiones del texto legal, pero no existe ningún mecanismo que fuerce a
  re-firmar cuando se publica una versión nueva: `nda_firmado` es un
  booleano global, no ligado a una versión, así que quien firmó la v1 queda
  exento para siempre aunque se publique una v2 con cambios sustanciales.

**Fix propuesto** (cambio de modelo, fuera del alcance de "solo revisar" —
lo dejo como propuesta, no lo aplico):

```python
# models/res_users.py
nda_acuerdo_id = fields.Many2one(
    "leulit.nda.acuerdo", string="Versión del NDA firmada", copy=False
)
```

Fijarlo en el mismo `write()` de `action_nda_verificar_codigo` (usando el
`acuerdo` que se le mostró, no un `get_current()` recalculado), y usar
`user.nda_acuerdo_id` en vez de `get_current()` dentro del informe. La
política de si se debe forzar re-firma al publicar una versión nueva
(comparando `nda_acuerdo_id` contra `get_current()` en `_nda_debe_firmar`)
queda como pregunta abierta — ver sección 5.

## 4. Plan de acción priorizado

1. **[Alto]** `models/res_users.py` — añadir guarda `if self != self.env.user` en `action_nda_enviar_codigo` y `action_nda_verificar_codigo` (3.2).
2. **[Alto]** `models/res_users.py` — añadir guarda `if not self._nda_debe_firmar(): raise UserError(...)` en ambas acciones, para impedir re-firma (3.3).
3. **[Alto]** `models/res_users.py` — envolver `_nda_generar_y_enviar_pdf()` en try/except dentro de `action_nda_verificar_codigo` para no perder la firma ni mentir en la respuesta al usuario (3.4).
4. **[Alto]** `models/res_users.py` + `report/leulit_nda_report.xml` — añadir `nda_acuerdo_id` y usarlo en el informe en vez de `get_current()`; decidir con el usuario la política de re-firma en nueva versión (3.5, requiere la decisión de la sección 5).
5. **[Alto]** Decidir y documentar (o implementar) si se necesita bloquear también accesos vía RPC/XML-RPC directos, no solo `/web` (3.1) — decisión de producto/arquitectura, no solo de código.
6. **[Medio]** `models/res_users.py:40` — sustituir `random.randint` por `secrets.randbelow`.
7. **[Medio]** `controllers/main.py` / `models/res_users.py` — añadir cooldown mínimo entre envíos de código en `/nda/enviar_codigo`.
8. **[Medio]** `controllers/main.py:24-33` — comprobar `if not acuerdo:` antes de renderizar/permitir firmar.
9. **[Medio]** `controllers/main.py:24` — decidir si `website=True` es necesario; si no, quitarlo (o declarar la dependencia real).
10. **[Medio]** Añadir `tests/` con `TransactionCase` cubriendo los casos descritos en la tabla.
11. **[Bajo]** Resto de mejoras de mantenibilidad (cache de `ir.config_parameter`, filtro de archivados, `email_from`, mover el JS a assets, UI para el kill-switch, limpieza de código expirado) — sin urgencia, agrupables en el mismo commit de limpieza.

## 5. Dudas / no verificable sin entorno

- **¿`Home.web_client` en esta instalación concreta de Odoo 17 mapea también la(s) ruta(s) `/odoo` (y `/odoo/<path:subpath>`)?** Odoo 17 introdujo `/odoo` como nuevo prefijo de URL del backend. Si en `addons/web/controllers/home.py` de la versión instalada `web_client` registra únicamente `/web` (y no `/odoo`) en un método distinto, el bloqueo se saltaría con solo navegar a `/odoo` en vez de `/web` — esto **elevaría el hallazgo 3.1 de Alto a Crítico**. No he podido confirmarlo porque no hay fuente de Odoo core vendida en el repo ni entorno para ejecutar. Verificación sugerida: con un usuario de prueba sin firmar, una vez redirigido a `/nda/acuerdo`, teclear manualmente `https://<host>/odoo` en la misma pestaña y comprobar si también redirige o si carga el backend directamente.
- **¿`website=True` en `/nda/acuerdo` (controllers/main.py:24) funciona igual con y sin el módulo `website` instalado?** El manifest no declara esa dependencia; no he podido confirmar en código si `web.frontend_layout` con `no_header`/`no_footer` depende de que `website` esté instalado en este servidor concreto. Verificación sugerida: comprobar en el entorno de pruebas si `website` está instalado (`Ajustes > Apps`) y, si no lo está, cargar `/nda/acuerdo` para confirmar que no aparece cabecera/pie del sitio ni ningún error.
- **Política de re-firma ante una nueva versión del acuerdo** (relacionado con 3.5): ¿se debe forzar a todos los usuarios a volver a firmar cuando se publica una versión nueva de `leulit.nda.acuerdo`, o el diseño actual (firmar una vez, para siempre) es intencional y el campo `version` es solo informativo/histórico? Es una decisión de producto, no la cierro por mi cuenta.
- **¿El texto del NDA debe ser el mismo para todas las compañías?** `leulit.nda.acuerdo` no tiene `company_id`; dado que el ERP es multi-compañía (Helipistas / Icarus, según `CLAUDE.md`), no puedo determinar solo leyendo el código si eso es una omisión o una decisión deliberada (acuerdo único para todo el grupo).
- **Comportamiento de `force_send=True` bajo carga / SMTP lento**: no puedo medir el impacto real en la petición HTTP (bloqueo percibido) sin un entorno para probarlo; lo señalo como contribuyente al hallazgo 3.4 pero no como hallazgo de rendimiento cuantificado.
