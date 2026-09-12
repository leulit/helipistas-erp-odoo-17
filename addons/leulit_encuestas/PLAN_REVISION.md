# Revisión de código — `addons/leulit_encuestas/`

Revisión estática (sin entorno Odoo disponible: no se ha ejecutado el módulo, solo lectura de código, `__manifest__.py`, XML y grep sobre el resto del repo). Alcance: únicamente ficheros dentro de `addons/leulit_encuestas/`.

## 1. Resumen ejecutivo

**14 hallazgos**: **1 crítico**, **4 altos**, **4 medios**, **5 bajos**. El crítico es un `__manifest__.py` que no declara dependencia de `leulit` pese a que `security/ir.model.access.csv` referencia el grupo `leulit.RBase` — riesgo real de fallo de instalación. Los altos son de mayor impacto funcional: un campo `company_id` `required` sin `default` en `survey.survey`, un `onchange` en el wizard de invitación que **sobrescribe destructivamente** `partner_ids` y `emails` (pérdida de destinatarios ya introducidos por el usuario), y un `@api.depends` incompleto que deja `computed_emails` con caché obsoleta. No hay controladores, crons ni reports en este módulo.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `__manifest__.py:9-11` | `depends` no incluye `"leulit"` pero `security/ir.model.access.csv` usa el external id `leulit.RBase` | Instalar `leulit_encuestas` en una BD donde `leulit` no está ya instalado/cargado (p.ej. `-i leulit_encuestas` en solitario) → `ir.model.access.csv` falla al resolver `leulit.RBase` y la instalación del módulo se cae | Añadir `"leulit"` a `depends` |
| Alto | `models/survey_survey.py:9` | `company_id` es `required=True` sin `default` | Alta de una encuesta nueva por cualquier vía que no rellene `company_id` explícitamente (formulario sin tocar el campo, `create()` programático de otro módulo) → `ValidationError` por campo requerido vacío; registros de encuestas ya existentes antes de instalar este módulo quedan con `company_id` NULL | Añadir `default=lambda self: self.env.company` + backfill de registros existentes |
| Alto | `models/survey_invite.py:16` | `_onchange_email_group_id` hace `rec.partner_ids = [(6, 0, partners.ids)]`, reemplazo total | Usuario añade manualmente destinatarios A y B en el wizard "Invitar", luego selecciona un `email_group_id` cuyo grupo solo tiene al partner C → A y B desaparecen sin aviso | Usar `[(4, p.id) for p in partners]` (añadir, no reemplazar) |
| Alto | `models/survey_invite.py:23` | `rec.emails = ', '.join(extras)` sobrescribe el campo libre `emails` | Usuario escribe a mano `foo@x.com` en el campo "Emails", luego selecciona un grupo con correos externos → `foo@x.com` se pierde, queda solo lo del grupo | Fusionar con el contenido previo de `rec.emails` en vez de sobrescribir |
| Alto | `models/leulit_email_group.py:16` | `@api.depends('partner_ids', 'external_emails')` no incluye `partner_ids.email` | Se crea el grupo con un partner sin editar nada más; después se edita el email de ese partner desde su ficha → `computed_emails` no se recalcula (Odoo no dispara el compute porque el campo dependiente `email` no está declarado) y queda con el correo antiguo/obsoleto | `@api.depends('partner_ids', 'partner_ids.email', 'external_emails')` |
| Medio | `security/ir.model.access.csv:2` + `views/survey_invite_inherit.xml:10` + `models/leulit_email_group.py:13` | No hay `ir.rule` de compañía sobre `leulit_encuestas.email.group`, ni dominio por compañía en el M2O `email_group_id` del wizard | Empresa 1 y empresa 2 conviven en la misma BD (patrón multi-company del proyecto); un usuario de la compañía 1 ve y puede usar/editar/borrar grupos de correo creados para la compañía 2 | Añadir `ir.rule` con dominio `['|', ('company_id','=',False), ('company_id','in', company_ids)]` y `domain` en la vista |
| Medio | `security/ir.model.access.csv:2` | El único grupo con acceso (CRUD completo, incl. `unlink`) es `leulit.RBase`, que según `leulit/groups.xml` es el grupo base implícito de prácticamente todo empleado | Cualquier empleado con acceso al ERP (no solo gestores de encuestas) puede ver, editar y **borrar** listas que contienen emails personales de partners y correos externos | Revisar si procede acotar a un grupo más específico (p.ej. grupo de encuestas o un grupo propio); es decisión de producto, no técnica — ver sección de dudas |
| Medio | `models/leulit_email_group.py:20-36` y `models/survey_invite.py:19-21` | Deduplicación de emails sensible a mayúsculas/espacios (`e not in seen`, `e not in partner_emails`) | Un partner tiene `Foo@Bar.com` y `external_emails` contiene `foo@bar.com` → ambas variantes se consideran distintas, el correo real recibe la invitación/notificación duplicada | Comparar por `email.strip().lower()` manteniendo el valor original para mostrar |
| Medio | `models/leulit_email_group.py:44-52` | Validación de "email externo" solo comprueba que exista `'@'` en la cadena | Se introduce `external_emails` = `"@@@"` o `"a@"` → pasa la validación, produce un correo inválido en `computed_emails` y en el `emails` del wizard | Validar con una regex mínima tipo `^[^@\s]+@[^@\s]+\.[^@\s]+$` |
| Bajo | `views/survey.xml:6` | Id de vista `leulit_20240625_1100_form` (timestamp, no descriptivo) | — | Renombrar a algo como `leulit_encuestas_survey_survey_view_form_company` |
| Bajo | `views/survey.xml:9` | `<field name="type">form</field>` explícito en un `ir.ui.view` | — | Quitar; `type` se infiere automáticamente de la raíz de `arch` en Odoo 17, es ruido/legacy |
| Bajo | `__manifest__.py:4` | `"description": "\n    "` vacía/placeholder | — | Rellenar con una descripción real del módulo |
| Bajo | `models/leulit_email_group.py:10,13` | `partner_ids` sin dominio (permite elegir partners sin email) y `company_id` sin `default` | — | `domain="[('email','!=', False)]"` opcional en la vista; `default=lambda self: self.env.company` |
| Bajo | `models/survey_invite.py:12-13` | Al vaciar `email_group_id` el onchange hace `continue` y no limpia lo que había puesto el grupo anterior | Usuario selecciona grupo A (añade sus partners/emails), luego borra la selección de `email_group_id` → los destinatarios del grupo A quedan en el wizard sin que el usuario lo pidiera explícitamente tras deseleccionar | Documentar el comportamiento como intencional o limpiar explícitamente lo añadido por el grupo anterior |

No aplica: el módulo no tiene controladores HTTP, `ir.cron`, wizards propios (solo extiende `survey.invite`, que es `TransientModel` de `survey`) ni reports — no hay hallazgos en esas categorías porque no existe código que revisar.

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [Crítico] Dependencia de `leulit` no declarada (`__manifest__.py`)

```python
# __manifest__.py:9-11
"depends": [
    "survey"
],
```

```csv
# security/ir.model.access.csv:2
access_leulit_encuestas_email_group,access_leulit_encuestas_email_group,model_leulit_encuestas_email_group,leulit.RBase,1,1,1,1
```

`leulit.RBase` es un external id definido en `addons/leulit/groups.xml`. Odoo solo garantiza que los datos de un módulo del que dependes están cargados antes que los tuyos; sin `"leulit"` en `depends`, no hay ninguna garantía de orden de carga respecto a `leulit`, y si `leulit` no está instalado en la base de datos en absoluto, la carga de `ir.model.access.csv` falla con un external id sin resolver y la instalación de `leulit_encuestas` se aborta. En este ERP concreto `leulit` está prácticamente siempre instalado (es el módulo fundacional), lo que hace que el bug pase desapercibido en el día a día, pero es exactamente el patrón que la documentación del proyecto identifica como obligatorio ("every leulit_* module depends on leulit") y aquí no se cumple.

**Fix propuesto:**

```diff
 "depends": [
+    "leulit",
     "survey"
 ],
```

### 3.2 [Alto] `company_id` requerido sin `default` en `survey.survey`

```python
# models/survey_survey.py:9
company_id = fields.Many2one(comodel_name="res.company", string="Compañía", required=True)
```

Al ser `required=True` sin `default`, cualquier alta de `survey.survey` que no rellene explícitamente `company_id` (por ejemplo, si en el futuro algún wizard/cron de otro módulo crea encuestas por código, o simplemente un usuario que abre el formulario y no toca ese campo) puede fallar por validación. Además, al añadir este campo a un modelo con registros existentes (encuestas creadas antes de instalar este módulo), esos registros quedarán con `company_id` vacío — Odoo no fuerza el `NOT NULL` a nivel de base de datos cuando no hay `default` y ya existen filas, pero cualquier futura escritura sobre esas encuestas desde el formulario estándar exigirá rellenar la compañía antes de poder guardar.

**Fix propuesto:**

```diff
-company_id = fields.Many2one(comodel_name="res.company", string="Compañía", required=True)
+company_id = fields.Many2one(comodel_name="res.company", string="Compañía", required=True,
+                              default=lambda self: self.env.company)
```

Además hace falta un backfill de las encuestas ya existentes en la BD real (asignarles `company_id`); qué compañía corresponde a cada una es una decisión de negocio, no derivable del código — ver sección de dudas.

### 3.3 [Alto] `_onchange_email_group_id` sobrescribe `partner_ids` y `emails` en vez de fusionar

```python
# models/survey_invite.py:9-23
@api.onchange('email_group_id')
def _onchange_email_group_id(self):
    for rec in self:
        if not rec.email_group_id:
            continue
        partners = rec.email_group_id.partner_ids
        # set partner_ids to group partners
        rec.partner_ids = [(6, 0, partners.ids)]
        # compute external-only emails (exclude partner emails)
        external = rec.email_group_id.get_emails_list()
        partner_emails = [p.email for p in partners if p.email]
        extras = [e for e in external if e not in partner_emails]
        if extras:
            # populate the 'emails' free-text field with comma-separated emails
            rec.emails = ', '.join(extras)
```

`(6, 0, partners.ids)` es un reemplazo total del M2M `partner_ids`: cualquier destinatario que el usuario hubiera añadido a mano antes de elegir el grupo se pierde. Lo mismo con `rec.emails = ...`, que pisa el contenido previo del campo de texto libre. Escenario concreto: el usuario abre "Invitar", añade dos partners a mano, luego decide además añadir un grupo de correo → los dos partners añadidos a mano desaparecen del wizard sin ningún aviso, y si el usuario no se da cuenta, esos destinatarios simplemente no reciben la invitación.

**Fix propuesto:**

```diff
         partners = rec.email_group_id.partner_ids
-        # set partner_ids to group partners
-        rec.partner_ids = [(6, 0, partners.ids)]
+        # add the group's partners to whatever was already selected, don't wipe it
+        rec.partner_ids = [(4, p.id) for p in partners]
         # compute external-only emails (exclude partner emails)
         external = rec.email_group_id.get_emails_list()
         partner_emails = [p.email for p in partners if p.email]
         extras = [e for e in external if e not in partner_emails]
         if extras:
-            # populate the 'emails' free-text field with comma-separated emails
-            rec.emails = ', '.join(extras)
+            # merge with whatever the user already typed, don't overwrite it
+            existing = [e.strip() for e in (rec.emails or '').split(',') if e.strip()]
+            merged = existing + [e for e in extras if e not in existing]
+            rec.emails = ', '.join(merged)
```

### 3.4 [Alto] `computed_emails` con caché obsoleta: falta `partner_ids.email` en `@api.depends`

```python
# models/leulit_email_group.py:16-36
@api.depends('partner_ids', 'external_emails')
def _compute_computed_emails(self):
    for rec in self:
        emails = []
        for p in rec.partner_ids:
            if p.email:
                emails.append(p.email.strip())
        ...
```

`@api.depends('partner_ids', ...)` solo dispara el recompute cuando cambia la propia relación M2M (se añade/quita un partner del grupo), no cuando cambia un campo del partner referenciado (`email`). Escenario: se crea el grupo con un partner cuyo email es correcto; más tarde, desde la ficha del partner, se le corrige el email (typo, cambio de dominio corporativo, etc.) → `computed_emails` sigue mostrando (y usando, vía `get_emails_list()`, que alimenta el onchange del wizard de invitación) el email antiguo, hasta que algo vuelva a tocar `partner_ids` del grupo.

**Fix propuesto:**

```diff
-@api.depends('partner_ids', 'external_emails')
+@api.depends('partner_ids', 'partner_ids.email', 'external_emails')
 def _compute_computed_emails(self):
```

## 4. Plan de acción priorizado

1. **[Crítico]** Añadir `"leulit"` a `depends` en `__manifest__.py` — sin esto el módulo puede no instalar en una BD limpia.
2. **[Alto]** Añadir `default=lambda self: self.env.company` a `company_id` en `models/survey_survey.py:9`, y acordar con el usuario cómo hacer el backfill de encuestas existentes sin `company_id`.
3. **[Alto]** Cambiar `models/survey_invite.py:16` de `(6, 0, ...)` a `(4, id)` por partner, para no perder destinatarios ya seleccionados.
4. **[Alto]** Cambiar `models/survey_invite.py:23` para fusionar `rec.emails` en vez de sobrescribirlo.
5. **[Alto]** Añadir `'partner_ids.email'` al `@api.depends` de `_compute_computed_emails` en `models/leulit_email_group.py:16`.
6. **[Medio]** Añadir `ir.rule` de compañía sobre `leulit_encuestas.email.group` y `domain` por compañía en el campo `email_group_id` de `views/survey_invite_inherit.xml:10` (requiere decisión de negocio, ver dudas).
7. **[Medio]** Revisar si `leulit.RBase` es el grupo correcto para CRUD completo (incl. `unlink`) sobre `security/ir.model.access.csv:2`, o si procede un grupo más acotado (decisión de producto, ver dudas).
8. **[Medio]** Normalizar email (`strip().lower()`) en la deduplicación de `models/leulit_email_group.py:20-36` y en el filtro de `models/survey_invite.py:19-21`, para evitar invitaciones duplicadas por diferencias de mayúsculas/espacios.
9. **[Medio]** Reforzar `_check_external_emails_format` (`models/leulit_email_group.py:44-52`) con una regex mínima en vez de solo comprobar `'@' in email`.
10. **[Bajo]** Renombrar el id de vista `leulit_20240625_1100_form` (`views/survey.xml:6`) a algo descriptivo.
11. **[Bajo]** Quitar el `<field name="type">form</field>` redundante en `views/survey.xml:9`.
12. **[Bajo]** Rellenar `"description"` en `__manifest__.py:4`.
13. **[Bajo]** `default=lambda self: self.env.company` en `company_id` de `leulit_encuestas.email.group` (`models/leulit_email_group.py:13`) y opcionalmente dominio `email != False` en `partner_ids` (línea 10).
14. **[Bajo]** Decidir y documentar si al vaciar `email_group_id` en el wizard (`models/survey_invite.py:12-13`) se deben limpiar `partner_ids`/`emails` que había añadido el grupo anterior, o dejar el comportamiento actual documentado como intencional.

## 5. Dudas / no verificable sin entorno

- **Instalación real del módulo tras añadir `"leulit"` a `depends`**: no se puede confirmar sin ejecutar `./upd_module.sh leulit_encuestas dev --install` (o `-u` si ya está instalado) en el entorno Docker del usuario, con inspección de logs para ERROR/CRITICAL.
- **Campos `access_mode`, `active` y `answer_count` del modelo `survey.survey` referenciados en `views/survey.xml` y `partner_ids` en `survey.invite`**: el módulo base `survey` es código core de Odoo y no está vendorizado en este repo (`addons/third-party-addons/` no lo incluye), por lo que no he podido grepear su definición exacta. Por conocimiento general de Odoo 17 estos campos existen en el modelo estándar, pero esa suposición **no está verificada leyendo el código del repo** — conviene confirmarlo actualizando el módulo en el entorno de pruebas y comprobando que las vistas cargan sin error de xpath/campo inexistente.
- **Backfill de `company_id` en encuestas ya existentes** (hallazgo 3.2): qué compañía (1 = Helipistas, 2 = Icarus, u otra) corresponde a cada encuesta histórica es una decisión de datos/negocio que no puedo derivar del código; no la he asumido ni resuelto.
- **Alcance del grupo `leulit.RBase` para gestionar `leulit_encuestas.email.group`** (hallazgo M2, plan punto 7): si el acceso amplio a "todo empleado" es intencional (p.ej. porque cualquiera puede necesitar montar una lista de correo puntual) o si debería acotarse a un grupo de encuestas — es una decisión de producto/seguridad que dejo documentada como pregunta, no la resuelvo unilateralmente.
- **Necesidad real de `ir.rule` multi-company sobre `email.group`** (hallazgo M1): depende de si en la práctica ambas compañías (1 y 2) comparten el módulo de encuestas activamente o si en la práctica solo una compañía lo usa hoy, lo cual no es verificable leyendo solo este addon.
