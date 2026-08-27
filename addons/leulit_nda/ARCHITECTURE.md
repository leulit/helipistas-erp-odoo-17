# leulit_nda — Arquitectura

`leulit_nda` bloquea el acceso al backend de Odoo hasta que el usuario firma un
acuerdo de confidencialidad (NDA). Lo interesante de este módulo no es el NDA en
sí, sino el **mecanismo de interceptación**: da igual qué URL, menú, acción o
enlace directo abra el usuario — si tiene el NDA pendiente, siempre acaba en la
misma pantalla de firma. Ese mecanismo es genérico y reutilizable para cualquier
"debes hacer X antes de poder usar el ERP" (aceptar una política, rellenar un
dato obligatorio, ver un aviso legal, etc.). Este documento explica cómo está
construido para poder replicarlo.

## La idea clave: interceptar en el punto de entrada único, no en cada pantalla

Odoo (como cualquier SPA) tiene **un solo punto de entrada HTTP real** al
backend: la ruta `/web` servida por `Home.web_client()`
(`odoo/addons/web/controllers/home.py`). Todo lo demás — abrir un menú, pulsar
un breadcrumb, pegar la URL de un registro concreto, recargar la página — acaba
pasando por esa misma respuesta HTTP: es la que sirve el HTML/JS con el que
arranca el cliente web OWL. No existe una ruta por cada vista.

Por eso, en vez de intentar bloquear el acceso "por pantalla" (lo cual
obligaría a tocar decenas de vistas, o a montar un guard en JS por cada acción),
`leulit_nda` hereda ese único controlador y añade la comprobación ahí:

```python
# controllers/main.py
class NdaHome(Home):

    @http.route()
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action=s_action, **kw)
        if response.status_code == 200 and request.env.user._nda_debe_firmar():
            return request.redirect("/nda/acuerdo")
        return response
```

`@http.route()` sin argumentos, sobre un método que ya tiene `@http.route(...)`
en la clase padre, **hereda la ruta original** (`/web`, `/web/login` según
mapping de `Home`) y la vuelve a registrar apuntando a esta implementación. Es
el patrón estándar de Odoo para interceptar un controlador de un módulo base
sin tocar su código. Como `NdaHome` hereda de `Home`, sustituye al controlador
original para esa ruta.

Efecto práctico: **cualquier navegación que dispare `/web`** (login, refrescar,
abrir un enlace `/odoo/...`, pinchar un menú desde otra pestaña) pasa primero
por `super().web_client()` (que hace su trabajo normal) y luego por la
comprobación del NDA. Si el usuario no lo ha firmado, se le corta el paso con
un `redirect` a `/nda/acuerdo` **antes de que el cliente web llegue a pintar
nada**. Esto es lo que produce la sensación de "abras lo que abras, siempre
sale la misma pantalla": no es que cada pantalla compruebe el NDA, es que
ninguna pantalla llega a cargarse.

## La condición de bloqueo vive en el modelo, no en el controlador

```python
# models/res_users.py
def _nda_debe_firmar(self):
    """Indica si el usuario tiene bloqueado el acceso al backend hasta firmar el NDA."""
    self.ensure_one()
    if self.id == SUPERUSER_ID or not self._is_internal() or self.nda_firmado:
        return False
    icp = self.env["ir.config_parameter"].sudo()
    return icp.get_param("leulit_nda.enforce", "True") == "True"
```

El controlador solo pregunta `request.env.user._nda_debe_firmar()`; toda la
lógica de negocio (quién está exento, si ya firmó, si el bloqueo está activado
globalmente) vive en `res.users`. Esto es importante para reutilizar el patrón:
el "guard" HTTP debe ser tonto (una pregunta booleana), y la política debe
poder cambiar sin tocar el controlador. Puntos de exención ya contemplados:

- `SUPERUSER_ID` (usuario técnico `__system__`) nunca se bloquea — evita
  bloquear scripts/cron/migraciones que corren como superusuario.
- `_is_internal()` — solo aplica a usuarios internos (empleados), no a
  usuarios de portal/público.
- `nda_firmado` — una vez firmado, no se vuelve a preguntar.
- `ir.config_parameter` `leulit_nda.enforce` — kill-switch global para
  desactivar el bloqueo en caliente (útil mientras el texto legal definitivo
  no esté listo; ver el placeholder en
  [data/leulit_nda_acuerdo_data.xml](data/leulit_nda_acuerdo_data.xml)) sin
  desinstalar el módulo.

## La pantalla de firma es una página frontend, no una vista de backend

`/nda/acuerdo` es una ruta `type="http", auth="user", website=True` que
renderiza una plantilla QWeb "frontend" (`web.frontend_layout`, sin header ni
footer del sitio web), no una vista de formulario de Odoo. Esto es deliberado:

- El cliente web de backend (OWL) todavía no ha terminado de cargar cuando se
  hace el redirect — no hay `env` de JS, ni router, ni nada del framework de
  vistas disponible. Una página HTML "plana" servida por el controlador es lo
  único que puede pintarse en ese punto.
- El propio texto del acuerdo (`leulit.nda.acuerdo.contenido`, un campo
  `Html`) es editable por un admin desde
  `Helipistas > Acuerdo NDA` sin tocar código ni traducciones.
- El único endpoint dentro de esa ruta (`self._nda_debe_firmar()`) vuelve a
  comprobarse en `nda_acuerdo()`: si alguien llega a `/nda/acuerdo` sin
  tenerlo pendiente (por ejemplo, ya lo firmó en otra pestaña), se le reenvía
  a `/web` en vez de mostrarle la pantalla de firma otra vez.

## El flujo de firma (OTP por email + PDF)

La firma en sí reutiliza el patrón de "código de un solo uso" ya usado en
`leulit_esignature` (ver `CLAUDE.md` del repo), pero implementado de forma
independiente y más simple (sin `pyotp`, con un código numérico aleatorio
guardado en el propio `res.users`):

1. El usuario pulsa **Firmar** → JS hace `POST /nda/enviar_codigo` (JSON-RPC).
2. `action_nda_enviar_codigo()` genera un código de 6 cifras, lo guarda en
   `nda_codigo` / `nda_codigo_expiracion` (TTL 15 min) y lo envía por email
   con la plantilla `mail_template_nda_codigo`.
3. El usuario introduce el código → `POST /nda/verificar_codigo`.
4. `action_nda_verificar_codigo()` valida código + expiración + nº de
   intentos (máx. 5, `nda_codigo_intentos`), y si es correcto marca
   `nda_firmado = True`, `nda_fecha_firma = now()`.
5. `_nda_generar_y_enviar_pdf()` renderiza el informe QWeb
   (`report/leulit_nda_report.xml`) a PDF, lo adjunta como `ir.attachment`
   (con `res_model`/`res_id` explícitos, como exige la convención del repo) y
   lo envía por email con `mail_template_nda_firmado`.
6. El JS del frontend redirige a `/web` — esta vez `_nda_debe_firmar()` da
   `False` y `NdaHome.web_client()` deja pasar la respuesta normal.

Todas las rutas JSON (`/nda/enviar_codigo`, `/nda/verificar_codigo`) son
`auth="user"`, así que ya identifican al usuario logueado; no hace falta
pasarle el `user_id` desde el JS ni exponer nada por parámetro.

## Cómo reutilizar este patrón para otra cosa

El mecanismo de interceptación (`NdaHome` + `_nda_debe_firmar()`) es agnóstico
del contenido — el "qué hay que hacer antes de entrar" es intercambiable. Para
un caso nuevo (p. ej. forzar la lectura de un aviso, la aceptación de una
política de datos, o completar un dato obligatorio del perfil):

1. **No dupliques el controlador `Home`.** Si ya existe una herencia de
   `Home.web_client()` en el repo (esta, `NdaHome`), añade la condición nueva
   ahí como un `or` adicional, con su propio redirect si aplica. Si se crean
   varios módulos independientes que heredan `web_client()` cada uno por su
   lado, MRO decide el orden — mejor centralizar todas las comprobaciones de
   "gate de entrada" en un único sitio si se prevé más de una.
2. Añade un método `_debe_<cosa>()` en `res.users` con la misma forma que
   `_nda_debe_firmar()`: `ensure_one()`, exención de `SUPERUSER_ID` y de
   usuarios no internos, y lectura de un `ir.config_parameter` como
   kill-switch.
3. Crea una página frontend propia (`type="http", auth="user", website=True`,
   plantilla con `web.frontend_layout`) con su propio redirect de vuelta a
   `/web` si la condición ya no aplica (evita bucles y pantallas fantasma si
   el usuario llega por bookmark).
4. Si necesitas una acción del lado servidor disparada desde esa página, usa
   rutas `type="json", auth="user"` que llamen a métodos de modelo — no
   dupliques lógica de negocio en el controlador.

Este patrón **no sirve** para casos donde el usuario deba poder acceder a
*algunas* pantallas sí y a otras no (aquí es todo-o-nada: bloquea el `/web`
completo). Para bloqueos parciales por registro o por acción, el mecanismo
correcto en Odoo es `security/ir.model.access.csv` + reglas de registro
(`ir.rule`), no este controlador.

## Archivos relevantes

- [controllers/main.py](controllers/main.py) — el gate (`NdaHome`) y las 3
  rutas de la página de firma.
- [models/res_users.py](models/res_users.py) — campos `nda_*`, condición de
  bloqueo (`_nda_debe_firmar`) y flujo OTP + PDF.
- [models/leulit_nda_acuerdo.py](models/leulit_nda_acuerdo.py) — texto
  versionado del acuerdo, editable desde el backend.
- [views/templates.xml](views/templates.xml) — plantilla QWeb frontend +
  JS inline de la pantalla de firma (sin dependencias de OWL).
- [data/mail_template_data.xml](data/mail_template_data.xml) — plantillas de
  email del código OTP y de la confirmación con el PDF adjunto.
- [report/leulit_nda_report.xml](report/leulit_nda_report.xml) — informe QWeb
  del PDF firmado.
