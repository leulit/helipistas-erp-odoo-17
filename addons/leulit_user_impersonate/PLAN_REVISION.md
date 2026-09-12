# Revisión de código — `leulit_user_impersonate`

Revisión estática (sin entorno Odoo disponible) de todo el addon: modelos, controlador HTTP,
seguridad, vistas XML y assets JS/SCSS. Alcance limitado a
`addons/leulit_user_impersonate/`; cualquier dependencia de otro módulo se señala pero no se
corrige aquí.

## 1. Resumen ejecutivo

**20 hallazgos**: **3 críticos**, **6 altos**, **7 medios**, **4 bajos**. Los críticos son de
seguridad/auditoría: la ruta HTTP que realmente concede la suplantación (`/web/impersonate/start`)
no genera ningún registro de auditoría (bypass total del log si se llama directamente), el propio
grupo que puede impersonar tiene permiso de `unlink`/`write` sobre `impersonate.log` (puede borrar
su propio rastro), y las comprobaciones "no admin / no a mí mismo" del controlador usan `==`
estricta, saltables con confusión de tipos. A nivel alto: el grupo "User Impersonation" concede
administrador total del sistema vía `implied_ids`, no hay expiración de sesión suplantada, y
"cerrar sesión" no restaura al usuario original pese a lo documentado.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `controllers/main.py:12-61` vs `models/res_users.py:39-73` | El controlador que realmente cambia `session.uid` no crea ningún `impersonate.log` — sólo lo crea el método de modelo `action_impersonate_user()`, que es un camino distinto | Un usuario del grupo `group_impersonate_user` llama directamente (curl/consola) a `POST /web/impersonate/start` con `{"user_id": N}` sin pasar por el botón de la UI | Crear el log dentro del propio controlador (única fuente de verdad), o hacer que el controlador exija y valide un token/; ver diff en §3.1 |
| Crítico | `security/ir.model.access.csv:2` | `group_impersonate_user` tiene `perm_write=1, perm_unlink=1` sobre `impersonate.log`: los usuarios auditados pueden editar/borrar su propio rastro | Un impersonador borra o trunca su fila en `impersonate.log` tras usarla | `perm_write=0, perm_unlink=0` para `group_impersonate_user`; escribir el `end_date` siempre vía `sudo()` desde el propio controlador |
| Crítico | `controllers/main.py:23,27` | `user_id == request.env.uid` y `user_id == 1` son comparaciones Python `==` estrictas; un `user_id` no-entero (ej. `"1"`) no es igual a `1` y evita ambos guardas | Llamada directa a `/web/impersonate/start` con `{"user_id": "1"}` (JSON string) para impersonar literalmente la cuenta `uid=1` | Forzar `user_id = int(user_id)` al principio del método (con `try/except → error controlado`) antes de cualquier comparación |
| Alto | `security/groups.xml:6-11` | `group_impersonate_user` usa `implied_ids: base.group_system`: dar este grupo, pensado para "sólo impersonar", concede además **todos** los permisos de Administrador de sistema | Se añade el grupo a un usuario de soporte/HR pensando que sólo podrá impersonar, y ese usuario obtiene acceso total a Ajustes/Técnico | Invertir la relación (que `base.group_system` implique `group_impersonate_user`, no al revés) o eliminar el `implied_ids` y comprobar sólo `group_impersonate_user` en el código — ver §3.2 |
| Alto | Todo el flujo (`controllers/main.py`, `models/impersonate_log.py`) | No existe expiración/timeout de la sesión suplantada; el propio README la lista como "Desarrollo Futuro" pendiente | Un admin impersona y olvida hacer "Stop"; la sesión sigue activa indefinidamente (días) sin cierre automático | Añadir `ir.cron` que cierre (`end_date`) e invalide sesiones de impersonación con más de N minutos, y comprobar la antigüedad en cada request vía `ir.http._authenticate` o similar |
| Alto | `README.md:79-82` vs ausencia de override de `/web/session/logout` | La documentación afirma que "cerrar sesión normalmente" devuelve al usuario original; el módulo no sobrescribe el logout estándar de Odoo, que simplemente destruye la sesión | El admin impersonando pulsa "Log out": queda deslogueado por completo (no vuelve a ser él mismo) y el log de `impersonate.log` queda con `end_date` vacío para siempre | Corregir la documentación, y/o interceptar el logout para cerrar el log (`end_date`) cuando había impersonación activa |
| Alto | `views/res_users_views.xml:151` + `models/res_users.py:39-73` | El listado para impersonar incluye usuarios archivados (`('active', 'in', [True, False])`) y ni el controlador ni `action_impersonate_user()` bloquean `active=False` | Se impersona a un ex-empleado con cuenta archivada | Añadir `if not self.active: raise UserError(...)` en `action_impersonate_user()` y replicar el check en el controlador |
| Alto | `models/res_users.py:39-73`, `security/groups.xml` | No hay jerarquía de "quién puede impersonar a quién": cualquier miembro de `group_impersonate_user` puede impersonar a cualquier otro usuario no-admin/no-él-mismo, incluidos otros administradores o gerentes con más privilegios que el impersonador | Un usuario de soporte con el grupo impersona a un gerente para ver/exportar datos a los que él mismo no tendría acceso directo | Añadir una comprobación de "no impersonar a un usuario con más grupos/privilegios que el actor" o, mínimo, no permitir impersonar a otros miembros de `group_system`/`group_impersonate_user` |
| Alto | `controllers/main.py:44,86` (pendiente de confirmar en entorno real — ver §5) | Mutar sólo `request.session.uid` sin recalcular `session.session_token` puede chocar con la verificación de seguridad de sesión de Odoo 17 (`Session.check_security`, ligada a uid+password), invalidando la sesión en el siguiente request en vez de "cambiar de usuario" | Tras `start_impersonation`, el `window.location.reload()` del JS dispara un nuevo request cuya validación de token no coincide con el nuevo `uid` | Verificar en entorno de pruebas; si se confirma, usar el mecanismo soportado por Odoo (`request.session.authenticate()`/regenerar `session_token` para el nuevo uid) en vez de tocar sólo `uid` |
| Medio | `controllers/main.py:12-61` vs `models/res_users.py:39-73` | Duplicación de reglas de negocio (self/admin) en dos sitios distintos con dos implementaciones distintas (una lanza `AccessError`/`UserError`, la otra devuelve `{'error': ...}`) — riesgo de que se corrija una y no la otra | Se añade una nueva restricción sólo en el método de modelo y se olvida replicarla en el controlador (o viceversa) | Centralizar la validación en un único método reutilizado por ambos (p. ej. un `@api.model` en `res.users` que el controlador también invoque) |
| Medio | `models/res_users.py:54-58` | `action_impersonate_user()` crea el log **antes** de que el controlador confirme el cambio real de sesión; si el cliente nunca ejecuta la `client action` devuelta (p. ej. llamada RPC externa vía `examples.py` §1), queda una fila `impersonate.log` con `end_date` vacío para siempre | Llamada a `action_impersonate_user()` vía XML-RPC/JSON-RPC externo sin pasar por el web client | Crear el log sólo cuando el controlador confirma el cambio de sesión (ver diff §3.1), no en el método de modelo |
| Medio | `controllers/main.py:75-83` | `stop_impersonation` cierra el log con `search(..., limit=1)`; si hay más de una fila abierta para el mismo par (doble clic, doble pestaña) sólo se cierra una, dejando huérfanas el resto | El usuario hace doble clic en "Impersonate" antes de que recargue la página, generando dos logs `end_date=False` para el mismo `(original,target)` | Buscar y cerrar **todas** las coincidentes (`.write({'end_date': ...})` sobre el recordset completo, no `limit=1`) |
| Medio | `models/user_menu_analysis.py:209-232` | `_compute_model_access` hace 4 llamadas `check_access_rights` con `with_user()` **por cada fila** (una por menú) sin agrupar ni cachear; con ~350 addons de terceros instalados puede haber cientos/miles de menús | Un usuario pulsa "Ver Menús" sobre un usuario en un entorno con muchos menús → cientos de consultas pequeñas a BD en una sola llamada | Agrupar por `model_name` único y calcular una vez por modelo (no por menú), cacheando en un `dict` local antes de asignar a cada registro |
| Medio | `views/impersonate_banner.xml` (menú `menu_impersonate_log`, `groups=` en `views/res_users_views.xml:111`) | El menú del log de auditoría sólo es visible para `group_impersonate_user` (los propios auditados); no hay separación de funciones auditor/actor en la navegación estándar | Un `group_system` que NO tiene `group_impersonate_user` (con `perm_read=1` vía CSV) no tiene ruta de menú normal para revisar el log de forma independiente | Añadir un menú adicional visible para `base.group_system` (sin el grupo de impersonar) apuntando a la misma acción, en modo sólo lectura |
| Medio | `README.md:5,51-56,157-165`, `QUICKSTART.md:5-9,251-261` | Documentación desincronizada: menciona dependencia de un módulo `access_roles` que no existe en este repo y que **no** está en `__manifest__.py` (`depends: ['base','web']`), un menú "Access Role → Impersonar" inexistente, y un script `install_impersonate.sh` que no está en el módulo; además recomienda `docker exec ... odoo -u` a mano, contradiciendo la convención del proyecto de usar siempre `./upd_module.sh` | Un desarrollador sigue el QUICKSTART literalmente y no encuentra ni el módulo `access_roles`, ni el menú, ni el script | Reescribir README/QUICKSTART acorde al código real; usar `./upd_module.sh leulit_user_impersonate dev --install` |
| Medio | `models/user_menu_analysis.py:227-232` | `except Exception as e:` genérico en `_compute_model_access` oculta cualquier error (incluidos bugs de programación) tras un simple `_logger.warning` | Un error de tipo/`AttributeError` real en el código queda silenciado como si fuera "sin acceso" | Acotar a excepciones esperables (p. ej. `KeyError` de modelo inexistente); dejar propagar el resto o loggear con `exc_info=True` |
| Bajo | `models/res_users.py:75-83` | `action_stop_impersonation()` es código muerto: ningún botón/vista lo invoca; el JS llama directamente al controlador `/web/impersonate/stop` | — (nunca se ejecuta en producción) | Eliminarlo o documentarlo explícitamente como API pública para integraciones futuras |
| Bajo | `examples.py` (fichero completo) | No se importa desde `__init__.py` (inerte), pero declara clases `_inherit = 'res.users'` dentro de funciones; si algún día se importa por error, registraría herencias duplicadas en el registro de Odoo | Un futuro desarrollador añade `from . import examples` sin darse cuenta de que contiene clases de ejemplo | Mover el fichero fuera del paquete Python (p. ej. a `docs/examples.py.txt`) o renombrarlo `.md`/`.py.example` |
| Bajo | (todo el módulo) | No existe carpeta `tests/`, incumpliendo el patrón del repo (`<module>/tests/` con `TransactionCase`) para un módulo de alto riesgo de seguridad | — | Añadir al menos tests de: bloqueo de self/admin, bypass por tipo, creación del log, permisos CSV |
| Bajo | `models/user_menu_analysis.py:236-238` | `generate_analysis` borra y regenera el análisis de un `user_id` sin aislar por quién lo ejecuta (`create_uid`); dos personas analizando el mismo usuario objetivo a la vez pueden pisarse los resultados | Dos administradores pulsan "Ver Menús" sobre el mismo usuario casi simultáneamente | Añadir dominio `('create_uid', '=', self.env.uid)` al `search()` de limpieza, o filtrar la vista por `create_uid = uid` |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Crítico] Bypass de auditoría vía el controlador HTTP

El único punto que crea el registro de auditoría es `action_impersonate_user()` (modelo), pero el
único punto que **realmente concede el acceso** (mutar `session.uid`) es el controlador, que no
loguea nada:

```python
# controllers/main.py:12-61 — concede el acceso real, SIN crear impersonate.log
@http.route('/web/impersonate/start', type='json', auth='user')
def start_impersonation(self, user_id):
    if not request.env.user.has_group('leulit_user_impersonate.group_impersonate_user'):
        raise AccessError('You are not allowed to impersonate users.')
    if user_id == request.env.uid:
        return {'error': 'Cannot impersonate yourself'}
    if user_id == 1:
        return {'error': 'Cannot impersonate administrator'}
    target_user = request.env['res.users'].sudo().browse(user_id)
    if not target_user.exists():
        return {'error': 'User not found'}
    original_uid = request.session.uid
    request.session['impersonate_original_uid'] = original_uid
    request.session['impersonate_target_uid'] = user_id
    request.session.uid = user_id          # <-- aquí se concede el acceso real
    ...
    return {'success': True, ...}
```

```python
# models/res_users.py:39-73 — crea el log, pero NO cambia la sesión
def action_impersonate_user(self):
    self.ensure_one()
    if not self.env.user.has_group('leulit_user_impersonate.group_impersonate_user'):
        raise AccessError(_('You are not allowed to impersonate users.'))
    ...
    self.env['impersonate.log'].create({...})   # <-- sólo aquí se loguea
    return {'type': 'ir.actions.client', 'tag': 'start_impersonation', ...}
```

Cualquier usuario del grupo puede llamar `/web/impersonate/start` directamente (por ejemplo con
`curl`, o desde la consola del navegador con `fetch`), saltándose por completo el método de
modelo y, con él, el registro de auditoría — mientras conserva el acceso real como el usuario
objetivo.

**Fix propuesto** — mover la creación del log al propio controlador, que es el único lugar que
sabe si el cambio de sesión realmente ocurrió:

```python
# controllers/main.py — diff propuesto
@http.route('/web/impersonate/start', type='json', auth='user')
def start_impersonation(self, user_id):
    if not request.env.user.has_group('leulit_user_impersonate.group_impersonate_user'):
        raise AccessError('You are not allowed to impersonate users.')
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return {'error': 'Invalid user_id'}
    if user_id == request.env.uid:
        return {'error': 'Cannot impersonate yourself'}
    if user_id == 1:
        return {'error': 'Cannot impersonate administrator'}
    target_user = request.env['res.users'].sudo().browse(user_id)
    if not target_user.exists() or not target_user.active:
        return {'error': 'User not found'}

    original_uid = request.session.uid
    request.session['impersonate_original_uid'] = original_uid
    request.session['impersonate_target_uid'] = user_id
    request.session.uid = user_id

+   request.env['impersonate.log'].sudo().create({
+       'original_user_id': original_uid,
+       'impersonated_user_id': user_id,
+       'start_date': fields.Datetime.now(),
+   })
    ...
```

Y en `models/res_users.py`, `action_impersonate_user()` deja de crear el log (sólo valida y
devuelve la client action), evitando la duplicación de responsabilidades del hallazgo medio §2.

### 3.2 [Crítico] Log de auditoría no es a prueba de manipulaciones

```csv
# security/ir.model.access.csv:2
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_impersonate_log_user,impersonate.log.user,model_impersonate_log,group_impersonate_user,1,1,1,1
```

`group_impersonate_user` (el grupo que **produce** las entradas del log al impersonar) tiene
también `perm_write=1` y `perm_unlink=1` sobre ese mismo modelo. Cualquiera de esos usuarios puede
editar o borrar sus propias filas desde la UI estándar (la vista tree/form tiene
`create="false" edit="false" delete="false"` pero eso sólo oculta botones en esa vista concreta —
no es una restricción de acceso; el modelo sigue siendo editable/borrable vía otras vistas,
`ir.model.access` genérico en modo desarrollador, o RPC directo).

**Fix propuesto**:

```diff
-access_impersonate_log_user,impersonate.log.user,model_impersonate_log,group_impersonate_user,1,1,1,1
+access_impersonate_log_user,impersonate.log.user,model_impersonate_log,group_impersonate_user,1,0,0,0
```

Y hacer que el `write` del `end_date` en `stop_impersonation` (controllers/main.py:83) se haga
siempre vía `sudo()` (ya lo hace: `log.write(...)` sobre un recordset obtenido con
`.sudo().search(...)`), de modo que ningún usuario normal necesite `perm_write` directo.

### 3.3 [Crítico] Bypass de "no admin / no a mí mismo" por confusión de tipos

```python
# controllers/main.py:23,27
if user_id == request.env.uid:
    return {'error': 'Cannot impersonate yourself'}
if user_id == 1:
    return {'error': 'Cannot impersonate administrator'}
```

`type='json'` acepta cualquier payload JSON válido para `user_id`; la comprobación es una
igualdad estricta de Python. `"1" == 1` es `False`, igual que `"1" == 5` (uid del actor). Un
usuario del grupo que invoque el endpoint directamente con `{"user_id": "1"}` evita ambos guardas
(el guardado desde la UI oficial siempre envía un entero JS, por lo que el flujo normal no lo
dispara — el riesgo es una llamada deliberada fuera de la UI).

**Fix propuesto**: casear a `int` al principio del método y devolver error controlado si falla
(ver diff completo en §3.1).

## 4. Plan de acción priorizado

1. **[Crítico]** Mover la creación de `impersonate.log` al controlador `start_impersonation` (única
   fuente de verdad) y eliminarla de `action_impersonate_user()` — `controllers/main.py`,
   `models/res_users.py`.
2. **[Crítico]** Quitar `perm_write`/`perm_unlink` a `group_impersonate_user` sobre
   `impersonate.log` — `security/ir.model.access.csv`.
3. **[Crítico]** Castear `user_id` a `int` con manejo de error antes de cualquier comparación en
   los tres métodos del controlador — `controllers/main.py`.
4. **[Alto]** Revisar el diseño de `implied_ids` en `group_impersonate_user` (o documentarlo muy
   explícitamente si es intencional) — `security/groups.xml`.
5. **[Alto]** Bloquear impersonar usuarios `active=False`, tanto en el controlador como en
   `action_impersonate_user()` — `controllers/main.py`, `models/res_users.py`,
   `views/res_users_views.xml`.
6. **[Alto]** Añadir expiración/timeout de la sesión suplantada (cron + comprobación por request) —
   `models/impersonate_log.py`, `controllers/main.py`.
7. **[Alto]** Decidir y documentar correctamente el comportamiento de "cerrar sesión" durante una
   impersonación (¿cierra el log?, ¿restaura al original?) — `README.md`, `controllers/main.py`.
8. **[Alto]** Añadir alguna restricción de "a quién se puede impersonar" (jerarquía/roles), no sólo
   uid=1 y self — `models/res_users.py`, `security/groups.xml`.
9. **[Alto]** Verificar en entorno real si mutar sólo `session.uid` invalida la sesión por el
   `session_token` de Odoo 17 — ver §5.
10. **[Medio]** Centralizar la validación de negocio (self/admin/activo) en un único método
    compartido entre controlador y modelo — `models/res_users.py`, `controllers/main.py`.
11. **[Medio]** Cerrar **todas** las filas abiertas coincidentes en `stop_impersonation`, no sólo
    una (`limit=1` → sin límite) — `controllers/main.py`.
12. **[Medio]** Agrupar por modelo único en `_compute_model_access` en vez de recalcular por cada
    menú — `models/user_menu_analysis.py`.
13. **[Medio]** Añadir un menú de sólo-lectura del log visible para `base.group_system` sin
    depender de `group_impersonate_user` — `views/res_users_views.xml` (o
    `security/*`).
14. **[Medio]** Reescribir `README.md`/`QUICKSTART.md` para reflejar el manifest real (sin
    `access_roles`, sin script inexistente, usando `./upd_module.sh`).
15. **[Medio]** Acotar el `except Exception` de `_compute_model_access` —
    `models/user_menu_analysis.py`.
16. **[Bajo]** Eliminar `action_stop_impersonation()` (código muerto) o documentarlo como API
    pública — `models/res_users.py`.
17. **[Bajo]** Sacar `examples.py` del paquete Python del addon (mover a docs) —
    `examples.py`.
18. **[Bajo]** Añadir `tests/` con al menos los casos de seguridad descritos arriba.
19. **[Bajo]** Aislar `generate_analysis` por `create_uid` para evitar pisarse entre analistas
    concurrentes — `models/user_menu_analysis.py`.

## 5. Dudas / no verificable sin entorno

- **Invalidación de sesión por `session_token`** (hallazgo Alto §2, fila 9): en Odoo 17,
  `Session.check_security()` recalcula un token ligado al `uid` (y a datos del usuario, como el
  hash de contraseña) en cada request y lo compara contra el token almacenado en la sesión. El
  código de este módulo cambia `request.session.uid` **sin** tocar `session.session_token`. Por
  el diseño documentado de Odoo (no verificable leyendo sólo este addon, ya que esa lógica vive en
  el núcleo `odoo/http.py`, no vendorizado en este repo), es plausible que el *siguiente* request
  (el propio `window.location.reload()` que dispara el JS tras "start") falle la verificación de
  seguridad de sesión y cierre la sesión en vez de "cambiar de usuario" — lo que convertiría el
  bug crítico de auditoría (§3.1) en menos explotable en la práctica, pero también significaría
  que la funcionalidad tal como está escrita podría no funcionar de forma fiable. **Requiere
  probarse en el entorno Docker real** (`./upd_module.sh leulit_user_impersonate dev --install`,
  luego reproducir el flujo de impersonar y comprobar si la sesión sobrevive al reload).
- **Comportamiento de CSRF/CORS sobre los endpoints `type='json'`**: no se ha podido verificar
  empíricamente si un tercero podría disparar estas llamadas JSON-RPC de forma cross-site; el
  análisis estático sugiere que el `Content-Type: application/json` requerido dificulta un CSRF
  clásico vía formulario HTML, pero esto depende de configuración de CORS del despliegue real, no
  del código del módulo.
- **`browse(user_id)` con un `user_id` no entero**: no se ha podido confirmar en qué versión exacta
  de Odoo 17 (parche) `res.users.sudo().browse(user_id)` levanta excepción vs. comportamiento
  silencioso cuando `user_id` es una cadena; el hallazgo crítico §3.3 se apoya únicamente en la
  semántica de `==` de Python, que sí es verificable sin ejecutar nada.
- **Impacto real de impersonar `uid=1` vía el bypass de tipos**: dado que `group_impersonate_user`
  ya implica `base.group_system`, el actor ya tiene permisos de administrador equivalentes; el
  valor añadido del bypass es sobre todo "aparecer como Administrator" en trazas de otros módulos
  (auditoría cruzada, `mail.message` `create_uid`, etc.), no una escalada de privilegios nueva en
  sentido estricto. Confirmar con el usuario si ese matiz cambia la prioridad relativa frente a los
  otros críticos.
