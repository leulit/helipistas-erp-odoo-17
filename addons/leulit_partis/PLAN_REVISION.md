# Revisión técnica — `leulit_partis`

**Qué es este módulo** (según `__manifest__.py`/`README.rst`, no es autoexplicativo por el nombre):
Sistema de Gestión de Seguridad de la Información (SGSI) para cumplimiento **EASA PART-IS / AESA**,
construido extendiendo dos veces el modelo OCA `mgmtsystem.hazard` (una vez como "Activo de
información", otra como "Análisis de riesgo MAGERIT"), con catálogos de amenazas/vulnerabilidades/
controles, workflow de aprobación de planes de tratamiento, dashboard de KPIs, wizards de análisis
masivo/exportación, notificaciones por cron y auditoría vía OCA `auditlog`.

**Dependencias reales** (`__manifest__.py`): `leulit`, `mgmtsystem`, `mgmtsystem_hazard`,
`mgmtsystem_hazard_risk`, `mgmtsystem_manual`, `document_page`, `hr`, `auditlog`. Todas presentes
en `addons/third-party-addons/`.

Revisión hecha 100% por lectura de código (imports, `_inherit`, campos declarados en las
dependencias OCA vendorizadas, manifest). Sin entorno Odoo/Postgres disponible — nada se ha
ejecutado.

## 1. Resumen ejecutivo

**22 hallazgos**: **6 críticos**, **6 altos**, **6 medios**, **4 bajos**.

Los críticos son de una naturaleza muy concreta y grave: el wizard de exportación CSV, el informe
PDF de plan de tratamiento, el sistema de notificaciones por cron y el wizard de análisis masivo
de riesgos **no funcionan en absoluto** — referencian un modelo (`mgmtsystem.risk`) y campos
(`residual_level`, `asset_code`, `strategy`, `existing_control_ids`, etc.) que no existen en
ninguna parte del código real del módulo ni de sus dependencias; el campo real usa otro nombre
(`pilar_residual_level`, `magerit_asset_score`, `pilar_treatment_strategy`...). Además, los botones
de aprobación/rechazo de riesgos lanzan `models.ValidationError`/`models.AccessError`, que no
existen en `odoo.models` (deberían venir de `odoo.exceptions`), por lo que fallan con
`AttributeError` en vez de mostrar el mensaje de validación. Los tests del módulo tampoco pueden
ejecutarse: faltan campos obligatorios heredados de la base OCA. A nivel de seguridad, el grupo
`leulit.RBase` (prácticamente todo empleado de la empresa, según las convenciones del proyecto)
tiene CRUD completo sobre catálogos SGSI, inventario de equipos IT y configuración de
notificaciones, anulando la separación usuario/manager que el propio módulo define.

## 2. Tabla de hallazgos

| Sev. | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `models/mgmtsystem_risk.py:293,297,307,321,337` | `models.ValidationError`/`models.AccessError` no existen en `odoo.models` | Cualquier usuario pulsa "Solicitar Aprobación" sin estrategia definida, o "Aprobar"/"Rechazar" sin ser manager | Importar `from odoo.exceptions import ValidationError, AccessError` y usarlas |
| Crítico | `models/mgmtsystem_notification_cron.py:56,85` | `self.env['mgmtsystem.risk']` — ese modelo no existe (el real es `mgmtsystem.hazard`) | Se ejecuta el cron diario/semanal (activo por defecto, `data/cron_jobs.xml`) | Usar `self.env['mgmtsystem.hazard']` y los nombres de campo reales |
| Crítico | `models/mgmtsystem_notification_cron.py:86,128,162` | Campo `residual_level` no existe (el real es `pilar_residual_level`, Selection de texto, no entero 4/5) | Igual que arriba, una vez corregido el modelo | Usar `pilar_residual_level in ['high','critical']` |
| Crítico | `models/mgmtsystem_risk_export_wizard.py:67,119-155` | Modelo `mgmtsystem.risk` inexistente + ~14 campos inexistentes (`asset_code`, `asset_type`, `asset_location`, `asset_value_c/i/d`, `asset_score`, `vulnerability_ids`, `threat_probability`, `potential_impact`, `inherent_level`, `existing_control_ids`, `strategy`, `proposed_control_ids`, `approver_id`, `target_date`) | Usuario pulsa "Exportar a CSV" (acción `action_mgmtsystem_risk_export_wizard`) | Reescribir contra el modelo/campos reales (`mgmtsystem.hazard`, `magerit_*`, `pilar_*`) |
| Crítico | `report/risk_treatment_plan_template.xml:63,110-194` + `report/risk_treatment_plan_report.xml:10` | Mismo problema que el wizard de exportación: `o.env['mgmtsystem.risk']`, `o.asset_code`, `risk.strategy=='mitigate'`, etc. | Se imprime "Plan de Tratamiento de Riesgos" (si se llamara a la acción — no hay botón que la invoque) | Reescribir la plantilla QWeb contra `mgmtsystem.hazard`/campos `magerit_*`/`pilar_*` |
| Crítico | `models/mgmtsystem_risk_bulk_wizard.py:95-111` | `action_create_risks` crea `mgmtsystem.hazard` sin `risk_type_id`, campo `required=True` sin default (definido en la dependencia `mgmtsystem_hazard_risk`) | Cualquier uso del wizard "Análisis Masivo de Riesgos" | Añadir `risk_type_id` a `vals` (con selección en el wizard o valor por defecto) |
| Crítico | `tests/test_risk_computations.py:34-41,64-86` | `.create()` sobre `mgmtsystem.hazard` sin los campos `required=True` heredados de OCA (`type_id`, `hazard_id`, `origin_id`, `department_id`, `responsible_user_id`, `analysis_date`, `risk_type_id`) | Se ejecuta la suite de tests | Añadir esos campos obligatorios al `setUp`/`create()` de cada test |
| Alto | `security/ir_model_access.xml:23-31,53-61,83-91`, `security/ir_model_access_new.xml` (todas las filas `*_rbase`) | `leulit.RBase` (todo empleado, ver convención del proyecto) tiene `perm_write/create/unlink=1` en catálogos SGSI, dashboard, informes de auditoría, wizards, `mgmtsystem.notification.cron` e inventario de equipos IT | Cualquier empleado con acceso básico al ERP edita/borra el catálogo de controles, cambia destinatarios de alertas o borra un informe de auditoría | Quitar las filas `*_rbase` con CRUD completo o limitarlas a `perm_read` |
| Alto | `models/mgmtsystem_asset.py` + `models/mgmtsystem_risk.py` (diseño completo) + todas las vistas/wizards con dominio `magerit_threat_id` | Activo vs. Riesgo se distinguen solo por si `magerit_threat_id` (opcional) está relleno — no hay campo/modelo dedicado | Alguien crea un "activo" y por error rellena una amenaza, o viceversa | Documentar como decisión de diseño asumida, o (cambio mayor, fuera de alcance sin confirmar con el usuario) introducir un campo discriminador explícito |
| Alto | `data/notification_templates.xml:7,18-19,31,75,86,99` | `${object.risk_count}`/`${object.risk_list}` en la plantilla de email — `object` es el registro `mgmtsystem.notification.cron`, que no tiene esos campos; el contexto pasado via `with_context(ctx)` no se expone como `object.*` en el motor Jinja de `mail.template` | Aun arreglando el bug del cron, el envío de email fallaría/renderizaría vacío | Pasar `risk_count`/`risk_list` como campos reales del wizard/registro, o renderizar el HTML en Python y usar `mail_values={'body_html': ...}` en `send_mail` |
| Alto | `views/mgmtsystem_asset_views.xml`, `views/mgmtsystem_risk_export_wizard_views.xml`, `report/*.xml` | Las acciones de exportar a CSV y de informe PDF no están enlazadas a ningún botón/menú real (`grep` no encuentra referencias en ninguna vista), contradiciendo `PROGRESS.md` ("Botón Exportar a CSV en vista de activos", "Botón PDF en header") | Un usuario nunca puede llegar a estas funciones desde la UI normal | Añadir los botones documentados, o eliminar/marcar como no terminadas estas features |
| Alto | `views/mgmtsystem_risk_base_views.xml:39` | Filtro "Mitigar" usa `('pilar_treatment_strategy', '=', 'mitigate')`, valor que no existe en la selección real (`reduce/avoid/accept/transfer`) | Usuario pulsa el filtro "Mitigar" en la búsqueda de riesgos | Cambiar a `'reduce'` |
| Medio | `data/notification_templates.xml:56,128` | El CTA de los emails enlaza a `leulit_partis.action_mgmtsystem_risk`/`menu_mgmtsystem_risk`, xmlids inexistentes en el módulo | Usuario clica el botón "Ver Riesgos" del email | Apuntar a `leulit_partis.action_mgmtsystem_risk_analysis` / `menu_leulit_partis_risk_analysis` |
| Medio | `models/mgmtsystem_dashboard.py:92-148` | 3 métodos compute no almacenados hacen `search([])` sobre **toda** la tabla `mgmtsystem.hazard` (sin `company_id`, sin límite) y filtran en Python; se recalculan en cada acceso al dashboard | Empresa con muchos activos/riesgos; cada apertura del Kanban/form dispara 3 búsquedas completas | Usar `search_count`/`read_group` con dominios, o cachear/almacenar los KPIs |
| Medio | `data/auditlog_rules.xml:8` | `log_read=True` sobre `mgmtsystem.hazard`, modelo compartido por activos Y riesgos, leído constantemente (listas, kanban, KPIs del dashboard) | Uso normal del módulo (abrir listas/dashboard) | Desactivar `log_read` o acotarlo a un subconjunto de campos/records realmente sensibles |
| Medio | `views/mgmtsystem_risk_export_wizard_views.xml:9,20,32,36` | Atributo `states="draft"/"done"` en `<group>`/`<button>` — sintaxis obsoleta, ya migrada en el resto del repo (ver comentario en `stock_quant_history`) a `invisible=` | Se abre el wizard de exportación (si además se arregla el bug crítico) | Sustituir por `invisible="state != 'draft'"` / `invisible="state != 'done'"` |
| Medio | `views/mgmtsystem_dashboard_views.xml:158-161,193-200` + falta de datos iniciales | Acción del dashboard es `kanban,form` pero no se crea ningún registro `mgmtsystem.dashboard` en `data/`; el ACL de usuario normal tiene `perm_create=0` | Usuario SGSI normal (no manager) entra al menú "Panel de Control" por primera vez | Crear un registro inicial en `data/` (`noupdate="1"`), o dar `perm_create=1` a `mgmtsystem_user` |
| Medio | `models/mgmtsystem_document.py:41-56` | `linked_asset_ids` y `linked_risk_ids` apuntan al mismo comodelo `mgmtsystem.hazard` sin dominio que distinga activo/riesgo | Usuario añade un "riesgo" en el campo de "activos relacionados" (o viceversa) | Añadir `domain="[('magerit_threat_id','=',False)]"` / `!=` respectivamente |
| Medio | `models/res_config_settings.py` (todo el fichero) | Umbrales MAGERIT/PILAR guardados como `ir.config_parameter` global, sin distinción por `company_id`, en un ERP multi-compañía (ver `CLAUDE.md` del proyecto) | Empresa 1 y empresa 2 (Icarus/Helipistas) comparten los mismos umbrales de criticidad | Confirmar con el usuario si es el comportamiento deseado; si no, mover a un modelo con `company_id` |
| Bajo | `models/mgmtsystem_dashboard.py:182-204` vs. `views/mgmtsystem_dashboard_views.xml` | `"view_mode": "tree,form"` hardcodeado en Python duplica lo que ya definen las acciones XML | — | Delegar a las acciones XML existentes (`action_mgmtsystem_hazard_asset`/`_risk`) en vez de construir el dict a mano |
| Bajo | `PROGRESS.md` (todo el fichero) | Marca como "✅ Completo"/"✅ Instalación en producción" funcionalidades que están rotas o inalcanzables (export CSV, informe PDF, notificaciones) | Un mantenedor futuro confía en el changelog | Corregir el changelog tras aplicar los fixes |
| Bajo | `views/mgmtsystem_risk_base_views.xml:105` (action) | `context: {'search_default_is_risk': 1}` no corresponde a ningún filtro `is_risk` en la vista search | Se abre "Análisis de Riesgos" | Quitar la clave o añadir el filtro `is_risk` correspondiente |
| Bajo | `models/mgmtsystem_notification_cron.py:140-147,172-179` | Envío de email uno a uno por destinatario, síncrono (`force_send=True`) dentro de un bucle Python | Grupo destinatario con muchos usuarios | Usar `email_to` con lista separada por comas en un único `send_mail`, o encolar sin `force_send` |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 (Crítico) Excepciones inexistentes en el workflow de aprobación

`models/mgmtsystem_risk.py` importa solo `from odoo import api, fields, models, _` — nunca
`odoo.exceptions` — pero lanza:

```python
# líneas 293, 297, 337
raise models.ValidationError(_("Debe definir una estrategia..."))
# líneas 307, 321
raise models.AccessError(_("Solo los responsables SGSI pueden..."))
```

`odoo.models` no define `ValidationError` ni `AccessError` (viven en `odoo.exceptions`). Cualquier
llamada a estos métodos que entre en la rama del `raise` no muestra el mensaje de validación: falla
con `AttributeError: module 'odoo.models' has no attribute 'ValidationError'`. Esto no es un caso
límite: `action_submit_for_approval` es el botón "Solicitar Aprobación", visible para cualquier
usuario SGSI, y la validación salta en el camino normal (crear un riesgo sin estrategia todavía y
pedir aprobación).

**Fix:**
```python
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
...
raise ValidationError(_("Debe definir una estrategia de tratamiento antes de solicitar aprobación."))
...
raise AccessError(_("Solo los responsables SGSI pueden aprobar planes de tratamiento."))
```

### 3.2 (Crítico) Cron de notificaciones: modelo y campo inexistentes

`models/mgmtsystem_notification_cron.py`:

```python
# línea 56-59
pending_risks = self.env['mgmtsystem.risk'].search([
    ('treatment_plan_state', '=', 'pending'),
    ('create_date', '<=', threshold_date)
])
...
# línea 85-88
critical_risks = self.env['mgmtsystem.risk'].search([
    ('residual_level', 'in', [4, 5]),
    ('treatment_plan_state', 'in', ['draft', 'rejected']),
])
```

Comprobado por grep en todo el repo (`leulit_partis` + `third-party-addons`): no existe ningún
modelo `mgmtsystem.risk`, ni de este módulo ni de sus dependencias OCA. El modelo real de riesgo es
`mgmtsystem.hazard` (extendido dos veces, ver `mgmtsystem_asset.py`/`mgmtsystem_risk.py`). Tampoco
existe el campo `residual_level` en ningún modelo del módulo — el campo real es
`pilar_residual_level`, un `Selection` con valores de texto (`negligible/low/medium/high/critical`),
no un entero comparable con `[4, 5]`.

Esto no es código muerto: `data/cron_jobs.xml` registra ambos cron **activos por defecto**
(`active eval="True"`) con periodicidad diaria y semanal. Tras instalar/actualizar el módulo, cada
ejecución programada lanzará una excepción (`KeyError: 'mgmtsystem.risk'`) registrada en los logs
del servidor, de forma indefinida.

**Fix (bloqueante — depende de confirmar semántica con el usuario, ver sección 5):**
```python
pending_risks = self.env['mgmtsystem.hazard'].search([
    ('magerit_threat_id', '!=', False),
    ('treatment_plan_state', '=', 'pending'),
    ('create_date', '<=', threshold_date),
])
...
critical_risks = self.env['mgmtsystem.hazard'].search([
    ('magerit_threat_id', '!=', False),
    ('pilar_residual_level', 'in', ['high', 'critical']),
    ('treatment_plan_state', 'in', ['draft', 'rejected']),
])
```
También hay que corregir `risk.hazard_id.name` en `_send_pending_approval_email`/
`_send_critical_risks_email` (líneas 126,159): `hazard_id` en `mgmtsystem.hazard` es el campo
**obligatorio** heredado de OCA que apunta al catálogo `mgmtsystem.hazard.hazard` ("Peligro" en el
sentido original del módulo de seguridad laboral) — no tiene relación con el "activo PART-IS" que
la plantilla pretende mostrar. El campo correcto es `risk.magerit_asset_id.name`.

### 3.3 (Crítico) Wizard de exportación CSV completamente desconectado del modelo real

`models/mgmtsystem_risk_export_wizard.py` fue escrito contra un esquema de datos que no es el que
existe en este módulo (parece copiado de un diseño anterior con `mgmtsystem.risk` como modelo
independiente). Ejemplos concretos verificados contra `mgmtsystem_asset.py`/`mgmtsystem_risk.py`:

| Campo referenciado en el wizard | Existe? | Campo real |
|---|---|---|
| `hazard.asset_code` / `asset_type` / `asset_location` | No | (no existen estos conceptos en el módulo) |
| `hazard.asset_value_c/i/d` | No | `magerit_confidentiality/integrity/availability` |
| `hazard.asset_score` | No | `magerit_asset_score` |
| `self.env['mgmtsystem.risk']` | No | `mgmtsystem.hazard` (mismo registro que `hazard`) |
| `risk.vulnerability_ids` | No | `magerit_vulnerability_id` (Many2one, no m2m) |
| `risk.threat_probability` / `potential_impact` | No | `magerit_probability` / `magerit_impact` |
| `risk.inherent_level` | No | `magerit_inherent_level` |
| `risk.existing_control_ids` | No | `pilar_control_ids` |
| `risk.strategy` | No | `pilar_treatment_strategy` |
| `risk.approver_id` | No | `treatment_plan_approver_id` |
| `risk.target_date` | No | (no existe; lo más cercano es `treatment_plan_implementation_date`) |
| `risk.residual_level` | No | `pilar_residual_level` |

`action_export_csv` explota en la primera iteración con `KeyError: 'mgmtsystem.risk'` (línea 119)
en cuanto `hazards` no está vacío; si además `only_high_critical=True`, explota antes, al construir
el dominio con `('residual_level', 'in', [4, 5])` (línea 67), campo inexistente en `mgmtsystem.hazard`.

**No hay ningún botón ni menú** que invoque `action_mgmtsystem_risk_export_wizard` (verificado por
grep en `views/*.xml`) — la única forma de llegar a esta acción hoy es a través del menú técnico de
desarrollador, así que en la práctica es inalcanzable para un usuario normal, pero seguirá estando
rota si algún día se enlaza.

**Fix:** reescritura completa del método contra `mgmtsystem.hazard` y los campos `magerit_*`/
`pilar_*` reales; no es un parche de una línea. Recomendación: no arreglarlo hasta confirmar con el
usuario si esta funcionalidad sigue siendo necesaria (ver sección 5).

### 3.4 (Crítico) Informe PDF "Plan de Tratamiento de Riesgos" roto igual que el wizard CSV

`report/risk_treatment_plan_template.xml` tiene el mismo problema, con la misma lista de campos
inexistentes (`o.asset_code`, `o.asset_type`, `o.asset_value_c/i/d`, `o.asset_score`,
`risk.vulnerability_ids`, `risk.threat_probability`, `risk.potential_impact`, `risk.inherent_level`,
`risk.existing_control_ids`, `risk.strategy`, `risk.approver_id`, `risk.target_date`,
`risk.proposed_control_ids`, `risk.treatment_notes`, `risk.residual_level`) y el mismo modelo
inexistente:

```xml
<!-- línea 63 -->
<t t-set="risks" t-value="o.env['mgmtsystem.risk'].search([('hazard_id', '=', o.id), ('magerit_threat_id', '!=', False)])"/>
```

Además, incluso si `risk.strategy` existiera, la comparación `risk.strategy == 'mitigate'`
(línea 142) nunca sería cierta: el valor real de esa opción en `PILAR_TREATMENT_STRATEGIES` es
`'reduce'`, no `'mitigate'` (mismo patrón de desajuste que el hallazgo 3.10 en la vista de búsqueda).

`report/risk_treatment_plan_report.xml` también referencia el campo inexistente en
`print_report_name`:
```xml
<field name="print_report_name">'Plan_Tratamiento_Riesgos_%s' % (object.asset_code or object.name)</field>
```

Como con el wizard CSV, no hay ningún botón en `mgmtsystem_asset_views.xml` (ni en ninguna otra
vista) que dispare `action_report_risk_treatment_plan` — inalcanzable desde la UI hoy, pero roto de
raíz si se enlaza.

**Fix:** reescritura completa de la plantilla QWeb; no recomendable sin antes confirmar con el
usuario el formato/contenido deseado del informe.

### 3.5 (Crítico) Wizard de análisis masivo crea riesgos sin `risk_type_id` obligatorio

`models/mgmtsystem_risk_bulk_wizard.py`, `action_create_risks` (líneas 94-114):

```python
vals = {
    "name": risk_name,
    "type_id": asset.type_id.id if asset.type_id else False,
    "hazard_id": asset.hazard_id.id if asset.hazard_id else False,
    "origin_id": asset.origin_id.id if asset.origin_id else False,
    "department_id": self.department_id.id,
    "responsible_user_id": self.responsible_user_id.id,
    "analysis_date": self.analysis_date,
    "magerit_asset_id": asset.id,
    "magerit_threat_id": threat.id,
    "magerit_vulnerability_id": self.vulnerability_id.id if self.vulnerability_id else False,
    "magerit_probability": threat.default_probability or "3",
    "magerit_impact": self._get_asset_impact_scale(asset),
    "pilar_treatment_strategy": self.default_strategy,
    "pilar_control_ids": [(6, 0, self.control_ids.ids)],
}
risk = self.env["mgmtsystem.hazard"].create(vals)
```

`mgmtsystem_hazard_risk/models/mgmtsystem_hazard.py` (dependencia OCA) declara:

```python
risk_type_id = fields.Many2one("mgmtsystem.hazard.risk.type", "Risk Type", required=True)
```

sin `default=`. `vals` no incluye `risk_type_id`. `create()` fallará con un error de campo
obligatorio ausente en cuanto el usuario ejecute el wizard "Análisis Masivo de Riesgos"
(`action_mgmtsystem_risk_bulk_wizard`, correctamente enlazado desde la lista de activos vía
`binding_model_id`), es decir: la única funcionalidad de creación masiva del módulo no funciona en
ningún caso.

**Fix (requiere decidir con el usuario qué `risk_type_id` usar por defecto — ver sección 5):**
```python
vals = {
    ...
    "risk_type_id": self.risk_type_id.id,  # nuevo campo en el wizard, o un default fijo
    ...
}
```

### 3.6 (Crítico) Suite de tests no ejecutable: faltan campos obligatorios heredados

`tests/test_risk_computations.py` crea registros así:

```python
asset = self.asset_model.create({
    "name": "Servidor SGSI",
    "magerit_confidentiality": "5",
    "magerit_integrity": "4",
    "magerit_availability": "4",
})
```

`mgmtsystem_hazard/models/mgmtsystem_hazard.py` (OCA, base) declara `required=True` sin default en:
`type_id`, `hazard_id`, `origin_id`, `department_id`, `responsible_user_id`, `analysis_date`.
`mgmtsystem_hazard_risk` añade `risk_type_id` (también `required=True`, sin default). Ninguno de
estos siete campos se rellena en `setUpClass` ni en los `create()` de los dos tests. El primer
`.create()` de `test_asset_threshold_customization` fallará con `ValidationError` por campo
obligatorio ausente, antes de llegar a ninguna aserción — y lo mismo para
`test_risk_computation_and_residual`. **El módulo no tiene cobertura de test real** pese a que el
fichero de tests existe y `PROGRESS.md` lo marca como completado.

**Fix:**
```python
cls.hazard_type = cls.env["mgmtsystem.hazard.type"].sudo().create({"name": "IT"})
cls.hazard_hazard = cls.env["mgmtsystem.hazard.hazard"].sudo().create({"name": "Test hazard"})
cls.origin = cls.env["mgmtsystem.hazard.origin"].sudo().create({"name": "Test origin"})
cls.department = cls.env.ref("hr.dep_administration")  # o crear uno
cls.risk_type = cls.env["mgmtsystem.hazard.risk.type"].sudo().create({"name": "IT Risk"})
...
asset = self.asset_model.create({
    "name": "Servidor SGSI",
    "type_id": self.hazard_type.id,
    "hazard_id": self.hazard_hazard.id,
    "origin_id": self.origin.id,
    "department_id": self.department.id,
    "responsible_user_id": self.env.user.id,
    "analysis_date": fields.Date.today(),
    "magerit_confidentiality": "5",
    ...
})
```
(y añadir `risk_type_id` al `create()` del riesgo).

### 3.7 (Alto) `leulit.RBase` con CRUD completo sobre modelos sensibles del SGSI

Patrón repetido en `security/ir_model_access.xml` y `security/ir_model_access_new.xml`: para cada
modelo nuevo del módulo se crean 2-3 filas `ir.model.access` — una para
`mgmtsystem.group_mgmtsystem_user` (normalmente solo lectura), otra para
`mgmtsystem.group_mgmtsystem_manager` (CRUD completo) y, además, **una tercera para
`leulit.RBase`** con `perm_read/write/create/unlink` todos a `1`:

```xml
<!-- ir_model_access.xml líneas 23-31, patrón repetido para threat/vulnerability/control -->
<record id="access_mgmtsystem_risk_threat_rbase" model="ir.model.access">
    <field name="group_id" ref="leulit.RBase"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

Y en `ir_model_access_new.xml`, el mismo patrón para: `mgmtsystem.dashboard`,
`mgmtsystem.audit.report`, los 4 wizards, `mgmtsystem.notification.cron` y
`leulit.partis.equipment`. Según `CLAUDE.md` del proyecto, `leulit.RBase` es el grupo base del que
cuelga prácticamente cualquier rol funcional (`RBase_employee`, `RBase_hide`, y por `implied_ids`
también roles con privilegios en otros módulos) — es decir, en la práctica **todo empleado con
acceso al ERP**. Esto anula por completo la separación `mgmtsystem_user` (solo lectura) vs.
`mgmtsystem_manager` (CRUD) que el propio fichero ya define dos filas antes: cualquier empleado
puede editar/borrar el catálogo de controles/amenazas/vulnerabilidades, cambiar los destinatarios
de las alertas automáticas (`mgmtsystem.notification.cron`), borrar informes de auditoría
(`mgmtsystem.audit.report`), o editar/borrar el inventario de equipos IT (que registra si un
portátil tiene cifrado/antivirus activos).

**Fix propuesto (a confirmar con el usuario — puede ser intencional en este ERP, ver sección 5):**
eliminar las filas `*_rbase` con CRUD completo, o rebajarlas a `perm_read=1` únicamente, dejando la
escritura solo a `mgmtsystem_manager`.

### 3.8 (Alto) Plantilla de email referencia campos que no existen en el registro renderizado

`data/notification_templates.xml`, ambos `mail.template` tienen `model_id` =
`mgmtsystem.notification.cron` y usan, dentro del cuerpo:

```
${object.risk_count}          <!-- línea 18 -->
% for risk in object.risk_list[:10]:   <!-- línea 31 -->
```

`object` en el motor de renderizado de `mail.template` (sintaxis `${}` tipo Jinja/Mako, ver
`mail.render.mixin._render_template_jinja`) es el registro browseado del modelo/`res_id` pasado a
`send_mail` — aquí, el propio `mgmtsystem.notification.cron`, que **no tiene** campos
`risk_count`/`risk_list` (solo `name`, `notification_type`, `days_threshold`,
`recipient_group_id`/`recipient_user_ids`, `last_run_date`, `last_notification_count`). El contexto
que `_send_pending_approval_email` pasa via `template.with_context(ctx)` (línea 133-137 de
`mgmtsystem_notification_cron.py`) no se expone en la plantilla como `object.risk_count`, sino
(como mucho, dependiendo de la versión del motor) como `ctx['risk_count']`. Aun arreglando el bug
crítico 3.2, el email fallaría al renderizar o mostraría vacío/erróneo.

**Fix:** o bien añadir campos reales al modelo `mgmtsystem.notification.cron` y rellenarlos antes de
`send_mail` (`config.write({'_transient_risk_count': ...})` no es viable en un modelo no transient
persistente — mejor un modelo auxiliar), o renderizar el HTML directamente en Python
(`env['mail.render.mixin']._render_template(...)` con `ctx` explícito) y pasarlo como
`email_values={'body_html': rendered_html}`.

## 4. Plan de acción priorizado

1. **[Crítico]** `models/mgmtsystem_risk.py` — sustituir `models.ValidationError`/`models.AccessError`
   por `odoo.exceptions.ValidationError`/`AccessError` (fix trivial, alto impacto: rompe el workflow
   de aprobación para todo usuario).
2. **[Crítico]** `data/cron_jobs.xml` — desactivar (`active eval="False"`) los dos cron hasta corregir
   `models/mgmtsystem_notification_cron.py`, para dejar de generar errores en producción en cada
   ejecución programada.
3. **[Crítico]** `models/mgmtsystem_notification_cron.py` — corregir modelo (`mgmtsystem.hazard`) y
   campos (`pilar_residual_level`, `magerit_asset_id` en vez de `hazard_id`); reactivar los cron.
4. **[Crítico]** `data/notification_templates.xml` — corregir el mecanismo de paso de datos a la
   plantilla (hallazgo 3.8) antes de reactivar los cron.
5. **[Crítico]** `models/mgmtsystem_risk_bulk_wizard.py` — añadir `risk_type_id` a `action_create_risks`
   (decidir con el usuario el valor/UX antes de tocarlo, ver sección 5).
6. **[Crítico]** `tests/test_risk_computations.py` — completar los `create()` con los campos
   obligatorios heredados; solo entonces la suite aporta cobertura real.
7. **[Crítico]** `models/mgmtsystem_risk_export_wizard.py` + `report/risk_treatment_plan_template.xml`
   + `report/risk_treatment_plan_report.xml` — decidir con el usuario si estas dos funcionalidades
   (CSV, PDF) se mantienen; si sí, reescribirlas contra el modelo/campos reales; si no, eliminarlas
   junto con sus ACL y referencias en el manifest.
8. **[Alto]** `security/ir_model_access.xml` + `security/ir_model_access_new.xml` — retirar o acotar
   las filas `*_rbase` con CRUD completo (confirmar alcance deseado con el usuario primero).
9. **[Alto]** `views/mgmtsystem_risk_base_views.xml:39` — corregir el filtro `strategy_mitigate` a
   `'reduce'`.
10. **[Alto]** `data/notification_templates.xml:56,128` — apuntar el CTA al xmlid de acción/menú real.
11. **[Medio]** `data/auditlog_rules.xml:8` — reevaluar `log_read=True` sobre `mgmtsystem.hazard`.
12. **[Medio]** `models/mgmtsystem_dashboard.py` — sustituir `search([]) + filtered()` por
    `search_count`/`read_group` con dominios.
13. **[Medio]** `views/mgmtsystem_risk_export_wizard_views.xml` — migrar `states=` a `invisible=`
    (solo relevante si se conserva el wizard, punto 7).
14. **[Medio]** `data/` — crear un registro inicial de `mgmtsystem.dashboard`, o ajustar ACL de
    `mgmtsystem_user` para poder crearlo.
15. **[Medio]** `models/mgmtsystem_document.py` — añadir dominios que distingan activo/riesgo en
    `linked_asset_ids`/`linked_risk_ids`.
16. **[Bajo]** Actualizar `PROGRESS.md` tras aplicar los fixes anteriores, retirando las marcas
    "✅ Completo" de funcionalidades que en realidad estaban rotas.
17. **[Bajo]** Limpiar `search_default_is_risk` sin filtro asociado y el envío de email
    uno-a-uno síncrono.

## 5. Dudas / no verificable sin entorno

- **Comportamiento exacto de la sandbox Jinja de `mail.template`** (hallazgo 3.8): no puedo confirmar
  sin ejecutar Odoo si `object.risk_count` sobre un campo inexistente lanza excepción, renderiza
  vacío, o si el "line statement" `% for risk in object.risk_list[:10]:` sobre un atributo
  `Undefined` lanza `UndefinedError` en el momento del `slice`. La lectura del código de
  `mail.render.mixin` en versiones 17.0 apoya que fallaría o quedaría vacío, pero requeriría una
  ejecución real (o ver el log de un envío de prueba) para confirmarlo con certeza.
- **¿La `states=` obsoleta en vistas realmente rompe la instalación, o Odoo 17 simplemente la
  ignora silenciosamente?** La única evidencia disponible es un comentario de otro módulo OCA
  vendorizado (`stock_quant_history`) indicando que fue migrado explícitamente de `states=` a
  `invisible=` para este mismo Odoo 17 — no hay forma de confirmar el comportamiento exacto (error
  de instalación vs. degradación silenciosa) sin arrancar el servidor y actualizar el módulo.
- **Alcance real de `leulit.RBase`** (hallazgo 3.7): la caracterización de "prácticamente todo
  empleado" viene de `CLAUDE.md` del proyecto (documentación de la organización de grupos en
  `addons/leulit/security/groups.xml`, fuera del alcance de este módulo). No he releído ese fichero
  como parte de esta revisión — si la jerarquía de grupos hubiera cambiado desde que se escribió esa
  nota, el radio de impacto real podría ser distinto (aunque el problema de diseño — anular la
  separación user/manager de `mgmtsystem` — persiste igualmente).
- **¿El wizard de exportación CSV y el informe PDF son funcionalidad que el usuario todavía quiere,
  o se puede simplemente eliminar?** Antes de invertir en arreglarlos (reescritura completa, no un
  parche) conviene confirmarlo — están completamente inalcanzables desde la UI hoy, lo que sugiere
  que podrían haber quedado obsoletos tras un cambio de diseño no completado.
- **¿Es intencional que los umbrales MAGERIT/PILAR (`res_config_settings.py`) sean globales y no por
  compañía?** El proyecto es multi-compañía (Helipistas/Icarus, según `CLAUDE.md`); no se puede
  determinar sin preguntar si ambas compañías deben compartir criterios de criticidad SGSI o no.
- **Coherencia de `hazard_id` como campo "Activo" en los emails de notificación**: al corregir el
  hallazgo 3.2, el campo correcto pasa a ser `magerit_asset_id.name` — pero no he podido verificar en
  un entorno real que ese Many2one esté siempre relleno en los riesgos existentes en producción (es
  opcional en el modelo); si hay riesgos históricos sin activo asociado, el email mostraría "False"
  o cadena vacía para esa fila.
