# Revisión `leulit_esignature` — Odoo 17.0 Community

Revisión de código estático (sin entorno Odoo disponible). Todas las afirmaciones se basan en
lectura directa de fichero:línea, `__manifest__.py`, `__init__.py` y grep cruzado dentro de
`addons/leulit_esignature/` (y, sólo para confirmar dependencias declaradas en el manifest,
lectura puntual y de solo-lectura de `leulit_escuela/models/leulit_perfil_formacion_curso.py`).

## 1. Resumen ejecutivo

**24 hallazgos**: **3 críticos**, **9 altos**, **8 medios**, **4 bajos**. Los tres críticos
son facetas del mismo problema raíz: el mecanismo de firma electrónica con OTP está roto a
nivel de autenticación — `checksignatureRef()` compara dos valores que pone el propio
cliente (no un OTP recalculado en servidor), el hash `esignature`/`hashcode` se calcula con
MD5 sin ningún secreto pese a que el código sugiere que debería llevarlo, y existe un método
`hacksignature` invocable por RPC que permite generar un PDF "firmado" atribuido a cualquier
persona. El propio módulo demuestra el bypass: tres jobs en segundo plano
(`run_firmar_crs/boroscopia/formones`) llaman a `checksignatureRef` con `otp=notp='123456'`
fijo. Además hay dos bugs funcionales confirmados en producción actual (compute mal escrito
en `leulit.vuelo`, botón que llama a un método inexistente en `leulit.perfil_formacion_curso`).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `SignatureDoc.py:405-423` (`checksignatureRef`) | El "check" de OTP compara `datos['otp'] == datos['notp']`, ambos suministrados por el llamante vía contexto; nunca se recalcula el OTP real en servidor | Cualquier usuario con acceso de ejecución al modelo (prácticamente todos, ver `leulit.RBase` en `security.xml`) llama al método por RPC con `{'otp':'x','notp':'x','modelo':'leulit.anomalia','idmodelo':<id>}` y firma el registro sin conocer el OTP | Recalcular el OTP esperado en servidor (`self.env.user.get_otp()` o el del firmante real) dentro del propio método y comparar contra eso, nunca contra otro campo del mismo payload del cliente |
| Crítico | `ResUsers.py:45-50` (`hashEncodeWithSecret`) | MD5 sin sal ni secreto; el comentario `#h = hashlib.new(user['otp_secret'])` revela que se pretendía mezclar el secreto TOTP y no se hizo | `modelo`+`idmodelo` son públicos/adivinables y `otp` es literalmente `"N.A."` en varios flujos (`anomalia.py:72`, `vuelo.py:44/90/142`, maintenance_*); cualquiera puede recalcular offline un `esignature`/`hashcode` válido | Incluir `self.otp_secret` (o una clave de servidor) en el HMAC: `hmac.new(secret.encode(), tira.encode(), hashlib.sha256).hexdigest()` |
| Crítico | `SignatureDoc.py:426-448` (`hacksignature`) + UI oculta en `anomalia.xml:45-63`, `vuelo.xml:125-143` | Método RPC público que genera un PDF "firmado" atribuido a `idpersona` arbitraria sin ninguna validación de OTP ni de rol; su panel HTML (`#hackcontainer`, inputs `idpersona`/`iddocumento`) sigue presente y oculto en los formularios de anomalía y vuelo en producción | Cualquier usuario con acceso al modelo llama `hacksignature(idpersona=<id de otro>, iddocumento=<id>, estado=...)` por RPC y genera un documento firmado atribuido a esa persona sin su consentimiento; o alguien reactiva 3 líneas de JS comentadas para exponer el botón | Eliminar el método y el markup HTML de producción, o protegerlo con `@api.model` + control de grupo explícito y log de auditoría; nunca dejar herramientas de "hack"/impersonación en código desplegado |
| Alto | `vuelo.py:281-287` (`_esignature_docs`) | Dentro del `for item in self:` se asigna `self.esignature_docs = docs.ids` (todo el recordset) en vez de `item.esignature_docs` | Vista tree/kanban que muestra varios `leulit.vuelo` a la vez (Odoo agrupa records en un solo batch para el compute): todos los vuelos visibles terminan mostrando la lista de documentos firmados del **último** vuelo procesado en el batch, no la suya propia | Cambiar `self.esignature_docs = ...` por `item.esignature_docs = ...` (patrón ya correcto en `anomalia.py:180-182` y en los 3 ficheros `models/leulit_maintenance_*.py`) |
| Alto | `escuela/alumno_reports.xml:27-36` vs `escuela/perfil_formacion_curso_last_done.py:19` | El botón `firmar_informe_general_cursos_alu_ld` se añade a la vista de `leulit.perfil_formacion_curso`, pero el método sólo está definido en `leulit.perfil_formacion_curso_last_done` (modelo distinto, relacionado por `One2many`, sin `_inherits`) | Usuario pulsa "Firmar" en el formulario de perfil de formación → Odoo no encuentra el método en `leulit.perfil_formacion_curso` → error | Mover el botón a una vista de `leulit.perfil_formacion_curso_last_done`, o añadir en `leulit.perfil_formacion_curso` un método puente que delegue en el `last_done` activo |
| Alto | `EsignatureWizard.py:22-64` (`prepareSignature`) | `method` y `view_id` no están definidos (NameError garantizado); `context=None` por defecto pero se indexa sin comprobar `None`; `.encode('base64')` es sintaxis Python 2 inexistente en Python 3 | Si algo llega a invocar este método (hoy no hay llamadores en todo `addons/`) | Eliminar el método (y probablemente la clase entera, ver hallazgo bajo) o reescribirlo siguiendo el patrón ya correcto de `SignatureDoc.prepareSignature` |
| Alto | `models/website.py:44-54` (`portal_verify_csv`) + `views/webclient_templates.xml:145` | La ruta pública `/verifycsv` no filtra por `estado == 'completado'`; la plantilla hace `doc.fecha_valid.date()` sin comprobar que no sea `False` | Un usuario anónimo busca por un `esignature`/`hashcode` de un documento aún en estado `nuevo`/`validado` (sin `fecha_valid`) → `AttributeError: 'bool' object has no attribute 'date'` sin capturar → error 500 público, y de paso confirma la existencia de un documento en proceso de firma | Añadir `('estado','=','completado')` al domain, y usar `t-if="doc.fecha_valid"` antes de `.date()` |
| Alto | `security.xml:25-33` | `base.group_public` tiene `perm_read=1` sobre `leulit_signaturedoc` sin ningún `ir.rule` que acote filas | Combinado con los 2 hallazgos críticos de arriba, cualquier ruta pública que toque este modelo puede exponer más filas de las que el diseño de "verificación CSV" pretende | Revisar si el acceso público puede limitarse a través de la propia ruta (sin ACL a nivel de modelo) o añadir un `ir.rule` restrictivo (p.ej. sólo `estado='completado'`) para `base.group_public` |
| Alto | `models/leulit_maintenance_crs.py:151-174`, `..._boroscopia.py:151-171`, `..._form_one.py:151-171` (`run_firmar_*`) | Usan `with api.Environment.manage():` (API de entornos antigua; no puedo confirmar si sigue existiendo en Odoo 17 sin ejecutar código — ver sección de dudas) y `self.env.uid = user.id if user else 14`, con `14` como id de usuario hardcodeado | Si `api.Environment.manage` fue eliminado en Odoo 17, el hilo lanza excepción no capturada (se pierde silenciosamente, ver `threading.Thread` sin manejo de errores) en cada `firmar_crs/boroscopias/formones`; si no hay `certificador`/`mecanico`, el registro se firma como el usuario id=14 de esa base de datos, que puede no existir o ser otra persona en otro entorno | Sustituir por el patrón moderno de nuevo cursor (`Registry(self.env.cr.dbname).cursor()` + `api.Environment(new_cr, uid, context)`), envolver el hilo en try/except con log, y sustituir el `14` hardcodeado por un usuario de sistema configurable (parámetro de configuración o grupo dedicado) |
| Alto | `views.xml:65` (`<widget type="csv_code" style="button"/>`) + `menus.xml` | Sintaxis `<widget type="...">` es de Odoo ≤10 (Odoo 17 usa `<widget name="...">` apuntando a un widget registrado); el único fichero que registraría algo (`leulit_esignature.js`) está **enteramente comentado**, y `csv_code.js` sólo define una función global que nadie invoca ni registra | Al abrir el menú "Público > Verificar CSV / CID" la vista puede fallar al renderizar, o como mínimo el botón "Buscar" no hace nada porque el widget nunca se instancia | Reescribir la vista con un widget/OWL válido para Odoo 17, o sustituir por un controlador+plantilla portal (ya existe uno parecido en `models/website.py` / `webclient_templates.xml`) |
| Alto | `escuela/piloto.py:19-42` (`buildDocPerfilFormacionFirmado1Step`, `prepareSignature`, `generarPdfFirmado`) | `prepareSignature(self, descripcion, referencia)` se llama con 3 argumentos (`self.prepareSignature(descripcion, referencia, datos)`, línea 32) → `TypeError`; dentro, `context['modelo']` usa `context` no definido → `NameError`; `generarPdfFirmado` usa `cr`/`uid` no definidos → `NameError` | Nadie llama hoy a `buildDocPerfilFormacionFirmado1Step` en todo el árbol de `addons/` (verificado por grep) — código muerto pero 100% roto si se reactivara | Reescribir siguiendo el patrón correcto de `escuela/alumno.py` (usar `self.env['leulit_signaturedoc'].prepareSignature(...)` con los 5 argumentos que espera) o eliminar si ya no aplica |
| Alto | `escuela/alumno.py:73-82` (`generarPdfFirmado`) | `self.pool.get('res.users').browse(self.env.uid)` invoca `browse` sobre la clase de modelo del registry sin `env` vinculado (mezcla API antigua/nueva) | Si se llega a invocar `generarPdfFirmado` sobre `leulit.alumno` (no se ha localizado ningún llamador actual en `addons/`) | Sustituir por `self.env.user.name` |
| Medio | `ResUsers.py:35-38` (`get_otp`) | `totp.period = 20` tras crear `pyotp.TOTP(self.otp_secret, interval=60)`: `pyotp.TOTP` usa el atributo `interval`, no `period`; la asignación no tiene efecto real | El período efectivo del OTP sigue siendo 60s pese a la intención aparente de 20s (no puedo confirmarlo ejecutando pyotp; ver dudas) | Pasar `interval=20` al constructor o asignar `totp.interval = 20` |
| Medio | `models/website.py:2` | `from this import d` — importa el huevo de pascua `this` de Python (imprime el Zen of Python en el log al cargar el worker) y una variable `d` no usada en el fichero | Se ejecuta en cada arranque del proceso Odoo que importe este módulo | Eliminar la línea |
| Medio | `models/wizard_create_claim_from_vuelo.py` + `views/wizard_create_claim_from_vuelo.xml` | Modelo `TransientModel` y su vista completos, sin registrar: `models/__init__.py` no importa el fichero y `__manifest__.py` no incluye la vista en `data` | El wizard nunca se puede abrir; en su lugar `vuelo.py:445-446` (`firmar_doc_parte_vuelo`) lanza directamente un `UserError` cuando se excede el tiempo de actividad aérea, en vez de ofrecer crear la ocurrencia | Decidir con el usuario si se termina de cablear (import + entrada en `data`) o se elimina el código huérfano |
| Medio | `anomalia.py`, `models/leulit_maintenance_{crs,boroscopia,form_one}.py`, `models/leulit_anotacion_technical_log.py` | `buildFirmarDocsOdoo`/`generarPdfFirmado` casi idénticos en 5 ficheros (mismo esqueleto, sólo cambia el nombre de modelo/reporte); igual para los 3 `run_firmar_*` | Cualquier corrección de seguridad (p.ej. el bypass de OTP del hallazgo crítico) debe replicarse a mano en 5-8 sitios; alto riesgo de arreglar unos y olvidar otros | Extraer la lógica común a un mixin/`AbstractModel` (p.ej. `leulit.esignature.mixin`) parametrizado por modelo/reporte |
| Medio | Múltiples (`anomalia.py`, `vuelo.py`, `models/leulit_maintenance_*.py`) | Decenas de `_logger.error(...)` usadas para trazas normales de ejecución (no errores), p.ej. cada firma de anomalía/vuelo escribe varias líneas a nivel `ERROR` | Contaminan el log de producción a nivel ERROR, dificultando la monitorización real de errores (alertas basadas en nivel ERROR generarán ruido constante) | Bajar a `_logger.debug`/`_logger.info` o eliminar las trazas de depuración ya estabilizadas |
| Medio | `signaturedocquery.py:19-38` (`doquery`) | Firma de API antigua Odoo ≤8 (`cr, uid, ids, csvcode, context=None`) con `self.pool['leulit_signaturedoc'].search(cr, uid, ...)` | Sólo se invoca desde `csv_code.js` (código muerto, ver hallazgo "views.xml widget csv_code"); si ese widget se repara sin migrar también este método, la llamada fallará | Migrar a `def doquery(self, csvcode):` usando `self.env[...]` |
| Medio | `vuelo.py:290-302` (`check_item_signed`) | Firma de API antigua (`cr, uid, ids, checkval, context={}`) **con argumento mutable por defecto** `context={}` (antipatrón: el dict se comparte entre llamadas) | Sólo referenciado desde JS muerto (`leulit_esignature.js`, comentado) | Migrar a API moderna y sustituir `context={}` por `context=None` + `if context is None: context = {}` |
| Medio | `views/webclient_templates.xml:159` | Token `unique=` hardcodeado (`46f61b020d274f7a885810a4b0854e59be586c75`) en el enlace de descarga en vez de derivarse del adjunto | Copy-paste sin generalizar; no rompe la descarga (la URL ya varía por `id`) pero es ruido/deuda que puede confundir a quien lo lea | Generar el valor dinámicamente o eliminarlo si `/web/content` no lo necesita |
| Bajo | `binary.py` (fichero completo) | `import openerp.addons.web.http` — paquete `openerp` inexistente desde Odoo 10+; el fichero no se importa en `__init__.py` (línea comentada) | Ninguno actualmente (no se carga) | Eliminar el fichero, es deuda muerta |
| Bajo | `ResUsers.py` (bloques `'''...'''`), `SignatureDoc.py:65,142-147`, `res_users.xml:4-61,111-134` | Bloques extensos de código/XML comentado (plantillas de email, vista de wizard, lógica OTP antigua) | Reduce legibilidad y mantenibilidad | Eliminar o mover a un ticket/documentación si se quiere conservar el historial |
| Bajo | `EsignatureWizard.py` (clase completa) | Modelo `TransientModel` `leulit_esignaturewizard` declarado, con su único método roto (ver hallazgo alto), sin ninguna vista activa que lo use (la única referencia en `res_users.xml:111-134` está comentada) | — | Eliminar la clase completa si se confirma que `SignatureDoc.prepareSignature` es la que realmente se usa (así lo indica el grep de llamadores) |
| Bajo | `escuela/piloto.py:139-153` (`sendInstallMail`, `sendQRToRegisterMobile`, `initOTP`) | `raise UserError('Funcionalidad no migrada boton')` sin envolver el literal en `_()`, inconsistente con el resto del módulo que sí usa `_()` | Falta de traducción del mensaje en instalaciones multi-idioma | Envolver en `_('Funcionalidad no migrada')` |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] `checksignatureRef` no valida nada (`SignatureDoc.py:405-423`)

```python
def checksignatureRef(self):
    result = False
    error = False
    errMsg = ""
    datos = self._context.get('args',[])
    codigo = datos['otp']
    result = datos['otp'] ==  datos['notp']
    valid = False
    if result:
        for item in self.env[datos['modelo']].search([('id','=',datos['idmodelo'])]):
            esignature = self.buildSignature(datos['modelo'], datos['idmodelo'], codigo)
            item.buildPdfSigned(datos, esignature)
        valid = True
    ...
```

`datos['otp']` y `datos['notp']` llegan **ambos** desde el contexto que pone quien invoca el
método (vía `with_context(context)` o el propio RPC `args`). No hay ninguna comparación contra
un OTP recalculado en servidor (`self.env.user.get_otp()` o el del firmante esperado). Además
`datos['modelo']` (el modelo a firmar) también es controlado por el llamante.

El propio módulo confirma que esto es explotable, no hipotético — mira `SignatureDoc.py:388-402`:

```python
def pruebas_checksignatureRef(self,id):
    ...
    args={'otp':'123456',
          'notp':'123456',
          'modelo':'leulit.vuelo',
          'idmodelo':vuelo.id}
    ...
    self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()
```

y los tres jobs en segundo plano `run_firmar_crs`/`run_firmar_boroscopias`/`run_firmar_formones`
(`models/leulit_maintenance_{crs,boroscopia,form_one}.py`) hacen exactamente lo mismo con
`otp=notp='123456'` fijo para "auto-firmar" en lote.

**Fix propuesto** (idea, a validar con el usuario porque toca el contrato usado por varios
módulos dependientes):

```python
def checksignatureRef(self):
    datos = self._context.get('args', {})
    firmante = self.env['res.users'].browse(datos.get('user_id') or self.env.uid)
    otp_esperado = firmante.get_otp()
    result = datos.get('otp') == otp_esperado
    ...
```

### 3.2 [CRÍTICO] Hash de firma sin secreto (`ResUsers.py:45-50`)

```python
def hashEncodeWithSecret(self, tira):
    import hashlib
    #h = hashlib.new(user['otp_secret'])
    h = hashlib.md5()
    h.update(tira.encode('utf-8'))
    return h.hexdigest()
```

El comentario muerto demuestra la intención original de mezclar `otp_secret` en el hash; la
implementación real es MD5 puro sobre una cadena JSON con `modelo`, `idmodelo` y `otp` — todos
predecibles o, en varios flujos (`otp: "N.A."`), constantes. Cualquiera que conozca el modelo y
el id de un registro puede recalcular offline un `esignature`/`hashcode` "válido".

**Fix propuesto:**

```python
def hashEncodeWithSecret(self, tira):
    import hmac, hashlib
    secret = (self.otp_secret or '').encode('utf-8')
    return hmac.new(secret, tira.encode('utf-8'), hashlib.sha256).hexdigest()
```

(Requiere decidir con el usuario qué pasa con los `esignature`/`hashcode` ya emitidos, dado que
cambia el algoritmo — no es un cambio compatible hacia atrás sin migración.)

### 3.3 [CRÍTICO] `hacksignature` — impersonación de firmante (`SignatureDoc.py:426-448`)

```python
def hacksignature(self, idpersona, iddocumento, estado):
    ...
    for item in self.browse(int(iddocumento)):
        result = self.env[item.modelo].hackGenerarPdfFirmado(int(item.idmodelo), item.fecha_valid, idpersona, estado, None)
        ...
```

Método público (no empieza por `_`, por tanto invocable por RPC por cualquier usuario con
acceso de ejecución al modelo `leulit_signaturedoc`, que `security.xml` concede ampliamente a
`leulit.RBase`). Permite generar un PDF "firmado" atribuyéndolo a `idpersona`, sin validar que
quien llama sea esa persona ni que tenga OTP alguno. Su interfaz de usuario sigue presente
(oculta con `display:none`) en producción:

```xml
<!-- anomalia.xml:45-63, vuelo.xml:125-143 -->
<div id="hackcontainer" style="display:none">
    ...
    <td>Id persona:</td><td><input type="text" id="idpersona"/></td>
    <td>Id documento:</td><td><input type="text" id="iddocumento"/></td>
    ...
</div>
```

El JS que la activaría (`Ctrl+Enter` → `hack_signature.startHack()`) está hoy comentado en
`leulit_esignature.js`, pero (a) reactivarlo es trivial (descomentar el bloque), y (b) el
método sigue siendo invocable directamente por RPC sin pasar por ninguna UI.

**Fix propuesto:** eliminar `hacksignature`/`hackGenerarPdfFirmado` y el markup HTML asociado
de las vistas de producción. Si existe un caso de uso legítimo de "firma administrativa"
(soporte, regularización de datos históricos), implementarlo como acción explícita restringida
a un grupo de administración, con registro de auditoría (`mail.thread`/log dedicado), nunca
como atajo de teclado oculto.

### 3.4 [ALTO] Compute roto en `leulit.vuelo._esignature_docs` (`vuelo.py:281-287`)

```python
def _esignature_docs(self):
    for item in self:
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.vuelo'),('idmodelo','=',item.id)])
        if len(docs) > 0:
            self.esignature_docs = docs.ids   # <-- debería ser item.esignature_docs
        else:
            self.esignature_docs = None       # <-- debería ser item.esignature_docs
```

Cuando Odoo llama a un método `compute` sobre varios registros a la vez (comportamiento normal
en listas/tree views), `self` contiene todos los `leulit.vuelo` visibles. Asignar
`self.esignature_docs = ...` dentro del bucle aplica ese valor a **todo el recordset** en cada
iteración; al terminar el bucle, todos los vuelos muestran los documentos firmados del último
vuelo procesado, no los suyos. El patrón correcto ya existe en el propio módulo, p.ej.
`anomalia.py:176-182`:

```python
def _esignature_docs(self):
    for item in self:
        docs = self.env['leulit_signaturedoc'].search([...])
        item.esignature_docs = docs.ids if docs else None
```

**Fix propuesto:**

```python
def _esignature_docs(self):
    for item in self:
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.vuelo'),('idmodelo','=',item.id)])
        item.esignature_docs = docs.ids if docs else None
```

### 3.5 [ALTO] Botón "Firmar" apunta a un método que no existe en el modelo (`escuela/alumno_reports.xml:27-36`)

```xml
<record model="ir.ui.view" id="hlp_202011101800_view">
    <field name="model">leulit.perfil_formacion_curso</field>
    <field name="inherit_id" ref="leulit_escuela.leulit_20201106_1607_form" />
    <field name="arch" type="xml">
        <button name="informe_general_cursos_alu_ld" position="before">
            <button name="firmar_informe_general_cursos_alu_ld" type="object" class="oe_highlight" string="Firmar"/>
        </button>
    </field>
</record>
```

El método sólo está definido aquí:

```python
# escuela/perfil_formacion_curso_last_done.py
class leulit_perfil_formacion_curso_last_done(models.Model):
    _inherit = "leulit.perfil_formacion_curso_last_done"

    def firmar_informe_general_cursos_alu_ld(self):
        ...
```

`leulit.perfil_formacion_curso` (definido en `leulit_escuela/models/leulit_perfil_formacion_curso.py`,
fuera de alcance de este módulo pero confirmado por lectura de solo verificación) no define ni
hereda ese método — sólo tiene relaciones `One2many` (`last_done_history`, `last_done`) hacia
`leulit.perfil_formacion_curso_last_done`, sin `_inherits` que delegue llamadas de método.
Pulsar el botón fallará con un error de método/campo no encontrado.

**Fix propuesto (a validar con el usuario, toca cuál es el flujo correcto):** mover el botón a
una vista del modelo `leulit.perfil_formacion_curso_last_done` (p.ej. dentro del `tree`/`form`
embebido en `last_done`), o añadir en `leulit.perfil_formacion_curso` un método puente:

```python
def firmar_informe_general_cursos_alu_ld(self):
    for item in self:
        item.last_done.firmar_informe_general_cursos_alu_ld()
```

## 4. Plan de acción priorizado

1. **[Crítico]** Corregir `checksignatureRef` para comparar contra un OTP recalculado en
   servidor, no contra otro campo del mismo payload del cliente — `SignatureDoc.py:405-423`.
   Auditar y actualizar en el mismo cambio los usos internos que hoy dependen del bypass
   (`pruebas_checksignatureRef`, `run_firmar_crs/boroscopias/formones`).
2. **[Crítico]** Incluir un secreto real en `hashEncodeWithSecret` (HMAC) — `ResUsers.py:45-50`.
   Decidir con el usuario la estrategia de migración de `esignature`/`hashcode` ya emitidos.
3. **[Crítico]** Eliminar `hacksignature`/`hackGenerarPdfFirmado` y el markup `#hackcontainer`
   de `anomalia.xml` y `vuelo.xml`, o sustituirlos por un flujo administrativo auditado y
   restringido por grupo — `SignatureDoc.py:426-448`.
4. **[Alto]** Arreglar el compute `_esignature_docs` de `leulit.vuelo` (`self.` → `item.`) —
   `vuelo.py:281-287`. Cambio de una línea, impacto directo en lo que ve el usuario.
5. **[Alto]** Decidir y corregir el botón `firmar_informe_general_cursos_alu_ld` —
   `escuela/alumno_reports.xml:27-36`.
6. **[Alto]** Revisar la ruta pública `/verifycsv`: filtrar por `estado='completado'` y
   blindar `fecha_valid.date()` contra `False` — `models/website.py:44-54`,
   `views/webclient_templates.xml:145`.
7. **[Alto]** Verificar en un entorno de pruebas real si `views.xml:65`
   (`<widget type="csv_code">`) rompe la carga de la vista o de la instalación del módulo; si
   es así, corregirlo o sustituir la funcionalidad por el portal ya existente.
8. **[Alto]** Sustituir `api.Environment.manage()` por el patrón moderno de nuevo cursor y
   quitar el `uid=14` hardcodeado en `run_firmar_crs/boroscopias/formones` (3 ficheros).
9. **[Alto]** Decidir si `EsignatureWizard.py`, `escuela/piloto.py` (métodos rotos) y
   `escuela/alumno.py:generarPdfFirmado` se arreglan o se eliminan (código muerto hoy, pero
   engañoso para quien lo lea o intente reutilizarlo).
10. **[Medio]** Extraer a un mixin común la lógica duplicada de `buildFirmarDocsOdoo`/
    `generarPdfFirmado`/`run_firmar_*` repetida en 5-8 sitios, para que el fix del punto 1 no
    tenga que replicarse a mano.
11. **[Medio]** Limpiar imports/código muerto evidente: `from this import d`
    (`models/website.py:2`), `binary.py` completo, bloques comentados extensos.
12. **[Medio]** Revisar nivel de log (`_logger.error` → `debug`/`info`) en las rutas de firma
    para no contaminar las alertas de producción.
13. **[Bajo]** Limpieza general: eliminar `EsignatureWizard` si se confirma que no se usa,
    envolver mensajes de usuario pendientes en `_()`, quitar el token `unique=` hardcodeado de
    `webclient_templates.xml:159`.

## 5. Dudas / no verificable sin entorno

- **`api.Environment.manage()`** (`models/leulit_maintenance_{crs,boroscopia,form_one}.py`,
  método `run_firmar_*`): no tengo forma de confirmar sin ejecutar código si este classmethod
  sigue existiendo en el `odoo/api.py` de esta instalación de Odoo 17 (no encontré el código
  fuente de Odoo en el repo para comprobarlo). Si fue retirado, cada hilo lanzado por
  `firmar_crs`/`firmar_boroscopias`/`firmar_formones` fallaría con `AttributeError` de forma
  silenciosa (no hay `try/except` alrededor del `Thread.run`). Verificar ejecutando uno de
  estos flujos en el entorno de pruebas Docker (`./upd_module.sh leulit_esignature dev`) y
  revisando el log del contenedor.
- **`<widget type="csv_code" style="button"/>`** (`views.xml:65`): no puedo confirmar sin
  cargar la vista en un Odoo 17 real si el parser de arch la rechaza (rompiendo la carga del
  módulo) o simplemente la ignora en silencio (dejando el botón "Buscar" inerte). Se debe
  probar `./upd_module.sh leulit_esignature dev` y observar si hay error o sólo un botón que
  no responde.
- **`pyotp.TOTP.period` vs `.interval`** (`ResUsers.py:37`): mi lectura del comportamiento de
  `pyotp` es a partir de conocimiento general de la librería, no de su código fuente instalado
  en este proyecto (no está vendorizado en el repo). Si la versión de `pyotp` instalada en el
  contenedor expone `period` como alias de `interval`, este hallazgo no aplica — confirmar con
  `docker exec -ti helipistas_odoo_17 python3 -c "import pyotp; print(pyotp.__version__)"` y
  revisando su código fuente instalado.
- **Alcance real de `base.group_public` sobre `leulit_signaturedoc`** (`security.xml:25-33`):
  no puedo confirmar sin un servidor real si el endpoint `/web/dataset/call_kw` es alcanzable
  por un visitante anónimo del portal en esta versión/configuración concreta de Odoo 17 (nginx,
  `list_users`, etc. de `dockerserver/`), lo que cambia el nivel de explotabilidad práctica del
  hallazgo. La exposición vía el controlador `/verifycsv` (que sí es `auth="public"` explícito)
  no depende de esta duda y es explotable con certeza.
- **Llamadores reales de `generarPdfFirmado`/`prepareSignature`/`doquery`/`check_item_signed`
  con firma de API antigua**: confirmé por grep que no hay llamadores en `addons/`, pero no he
  revisado los ~350 módulos de `addons/third-party-addons/` ni módulos fuera de este repo (p.ej.
  la app Flutter, si en algún momento llamara a estos métodos por XML-RPC/JSON-RPC directo). Si
  el usuario sabe de integraciones externas que invoquen estos métodos por nombre, avisar antes
  de tocarlos.
