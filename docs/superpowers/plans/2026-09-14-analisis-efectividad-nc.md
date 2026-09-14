# Análisis de efectividad de No Conformidades — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir verificación de eficacia post-cierre a las acciones correctivas/preventivas de No Conformidad (`mgmtsystem.action`), para poder responder a AESA con evidencia trazable de que una acción correctiva se comprobó, pasado un plazo, como eficaz frente a la causa raíz.

**Architecture:** Activar el módulo OCA ya vendorizado `mgmtsystem_action_efficacy` (aporta `efficacy_value`/`efficacy_user_id`/`efficacy_description` en `mgmtsystem.action`) y extender `leulit_seguridad` con un campo `efficacy_review_date` que se autopropone al cerrar una acción de tipo `correction`/`prevention`, más una actividad (`mail.activity`) que recuerda al inspector revisarla en esa fecha. No se toca el modelo `mgmtsystem.nonconformity` ni el flujo de cierre de NC existente — todo el cambio vive en `mgmtsystem.action`, que ya es el objeto sobre el que se registran las acciones correctivas de cada NC.

**Tech Stack:** Odoo 17 (Python + XML views), módulo `leulit_seguridad`, dependencia nueva `mgmtsystem_action_efficacy` (OCA, ya presente en `addons/third-party-addons/`, no instalada hasta ahora).

**Spec:** No hay fichero de spec separado — el contexto completo (requisito de AESA, modelo actual, gap identificado) está en la conversación que originó este plan; este documento es autocontenido para el ejecutor.

## Global Constraints

- No hay Odoo/Postgres local: cada tarea termina con comandos exactos para que el usuario los ejecute en su entorno Docker de pruebas (`./upd_module.sh`), nunca se afirma "funciona" sin haberlo verificado así.
- Actualizar módulos SIEMPRE vía `./upd_module.sh <modulo> dev [--install|--stop]`, nunca `docker exec ... odoo -u` a mano.
- Un módulo que aún no está en `ir.module.module` no se activa con `-u`: `mgmtsystem_action_efficacy` se instala primero con `--install`, aparte de la actualización de `leulit_seguridad`.
- Cualquier tarea que añada un campo Python nuevo a un modelo existente es cambio de esquema (`ALTER TABLE`) → la actualización de `leulit_seguridad` en el paso final se hace con `--stop`.
- Nunca ejecutar un formateador automático (`black`, `ruff format`, etc.) sobre el código tocado o el fichero entero.
- Español en labels/strings, siguiendo el estilo ya usado en `leulit_seguridad` (ver `models/mgmtsystem_nonconformity.py`, `models/mgmtsystem_action.py`).
- El plazo por defecto de revisión de eficacia (90 días) es un valor de partida documentado como tal (`ponytail:` en el código), no un número normativo AESA — debe confirmarse con el responsable de calidad/seguridad antes de usarlo en producción; el campo queda editable a mano para no bloquear ese ajuste.

---

### Task 1: Activar el módulo OCA `mgmtsystem_action_efficacy`

**Files:**
- Modify: `addons/leulit_seguridad/__manifest__.py:9-15`

**Interfaces:**
- Consumes: nada.
- Produces: los campos `efficacy_value` (Integer), `efficacy_user_id` (Many2one a `res.users`), `efficacy_description` (Text) en `mgmtsystem.action`, y la pestaña de formulario "Efficacy" que los muestra (vista `mgmtsystem_action_efficacy.view_mgmtsystem_action_form`, ya definida por el propio módulo OCA). Task 2 depende de que estos campos y esa vista existan.

- [ ] **Step 1: Añadir la dependencia en el manifest**

En `addons/leulit_seguridad/__manifest__.py`, sustituir:

```python
    "depends": [
        "leulit",
        "leulit_operaciones",
        "leulit_taller",
        "mgmtsystem_audit",
        "mgmtsystem_hazard_risk"
    ],
```

por:

```python
    "depends": [
        "leulit",
        "leulit_operaciones",
        "leulit_taller",
        "mgmtsystem_audit",
        "mgmtsystem_hazard_risk",
        "mgmtsystem_action_efficacy"
    ],
```

- [ ] **Step 2: Instalar el módulo nuevo en el entorno de pruebas**

El usuario ejecuta en su Docker de test (no hay Odoo local aquí):

```bash
./upd_module.sh mgmtsystem_action_efficacy dev --install
```

- [ ] **Step 3: Verificar manualmente**

El usuario abre en el navegador cualquier acción existente (Seguridad → Acciones, o desde una No Conformidad) y confirma que aparece la pestaña "Efficacy" con los campos "Rating", "Inspector" y "Notes". Sin esto, Task 2 no tiene dónde insertar el campo nuevo.

- [ ] **Step 4: Commit**

```bash
git add addons/leulit_seguridad/__manifest__.py
git commit -m "feat(leulit_seguridad): activar módulo OCA mgmtsystem_action_efficacy"
```

---

### Task 2: Fecha de revisión de eficacia, autocompletado al cerrar y recordatorio

**Files:**
- Modify: `addons/leulit_seguridad/models/mgmtsystem_action.py` (fichero completo, 34 líneas actuales)
- Modify: `addons/leulit_seguridad/views/mgmtsystem_action.xml` (añadir dos `<record>` nuevos antes de `</odoo>`)
- Create: `addons/leulit_seguridad/tests/__init__.py`
- Create: `addons/leulit_seguridad/tests/test_mgmtsystem_action_efficacy.py`

**Interfaces:**
- Consumes: `efficacy_value`, `efficacy_user_id`, `efficacy_description` y la vista `mgmtsystem_action_efficacy.view_mgmtsystem_action_form` de Task 1; `mgmtsystem_action.stage_close` (xmlid ya usado en el propio fichero); tipos de `type_action` (`immediate`/`correction`/`prevention`/`improvement`) definidos en `mgmtsystem_action` (OCA).
- Produces: campo `efficacy_review_date` (Date) en `mgmtsystem.action`, método privado `_proponer_revision_eficacia()`. Task 3 (despliegue) no consume nada nuevo de aquí salvo el propio campo para verificarlo en UI.

- [ ] **Step 1: Escribir los tests (deben fallar primero)**

Crear `addons/leulit_seguridad/tests/__init__.py`:

```python
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import test_mgmtsystem_action_efficacy
```

Crear `addons/leulit_seguridad/tests/test_mgmtsystem_action_efficacy.py`:

```python
# -*- encoding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests import common


class TestMgmtsystemActionEfficacyReviewDate(common.TransactionCase):
    def _crear_accion(self, type_action, **extra):
        vals = {"name": "Acción de prueba", "type_action": type_action}
        vals.update(extra)
        return self.env["mgmtsystem.action"].create(vals)

    def test_cerrar_accion_correctiva_propone_fecha_y_actividad(self):
        stage_close = self.env.ref("mgmtsystem_action.stage_close")
        accion = self._crear_accion("correction")
        self.assertFalse(accion.efficacy_review_date)

        accion.write({"stage_id": stage_close.id})

        esperado = date.today() + timedelta(days=90)
        self.assertEqual(accion.efficacy_review_date, esperado)

        todo = self.env.ref("mail.mail_activity_data_todo")
        self.assertTrue(
            accion.activity_ids.filtered(lambda a: a.activity_type_id == todo)
        )

    def test_cerrar_accion_preventiva_propone_fecha(self):
        stage_close = self.env.ref("mgmtsystem_action.stage_close")
        accion = self._crear_accion("prevention")

        accion.write({"stage_id": stage_close.id})

        self.assertTrue(accion.efficacy_review_date)

    def test_cerrar_accion_inmediata_no_propone_fecha(self):
        stage_close = self.env.ref("mgmtsystem_action.stage_close")
        accion = self._crear_accion("immediate")

        accion.write({"stage_id": stage_close.id})

        self.assertFalse(accion.efficacy_review_date)

    def test_cerrar_accion_mejora_no_propone_fecha(self):
        stage_close = self.env.ref("mgmtsystem_action.stage_close")
        accion = self._crear_accion("improvement")

        accion.write({"stage_id": stage_close.id})

        self.assertFalse(accion.efficacy_review_date)

    def test_fecha_manual_no_se_sobrescribe_al_cerrar(self):
        stage_close = self.env.ref("mgmtsystem_action.stage_close")
        fecha_manual = date.today() + timedelta(days=30)
        accion = self._crear_accion(
            "correction", efficacy_review_date=fecha_manual
        )

        accion.write({"stage_id": stage_close.id})

        self.assertEqual(accion.efficacy_review_date, fecha_manual)
```

- [ ] **Step 2: Verificar que los tests fallan** (el campo `efficacy_review_date` no existe todavía)

Run (en el Docker de test del usuario):

```bash
docker exec -ti helipistas_odoo_17 odoo -u leulit_seguridad -d productiu \
  --test-enable --test-tags=/leulit_seguridad:TestMgmtsystemActionEfficacyReviewDate \
  --stop-after-init
```

Expected: FAIL — `ValueError: Invalid field 'efficacy_review_date' on model 'mgmtsystem.action'` (o similar, campo inexistente).

- [ ] **Step 3: Implementar el modelo**

Reemplazar el contenido completo de `addons/leulit_seguridad/models/mgmtsystem_action.py` por:

```python
# -*- encoding: utf-8 -*-
from datetime import timedelta

from odoo import _, fields, models

# ponytail: 90 días es un punto de partida, no un plazo normativo AESA — el
# responsable de calidad/seguridad debe confirmarlo o ajustarlo por NC; el
# campo queda editable a mano precisamente para eso.
DIAS_REVISION_EFICACIA_DEFECTO = 90

# Solo las acciones que atacan causa raíz necesitan verificación de eficacia
# posterior. Las inmediatas son contención (no evalúan si la causa raíz se
# resolvió) y las de mejora no derivan de una NC con causa que verificar.
TIPOS_ACCION_CON_REVISION_EFICACIA = ("correction", "prevention")


class MgmtsystemAction(models.Model):
    _inherit = "mgmtsystem.action"

    risk_type_id = fields.Many2one("mgmtsystem.hazard.risk.type", string="Peligro")

    efficacy_review_date = fields.Date(
        string="Fecha revisión eficacia",
        help="Fecha en la que se debe comprobar si esta acción correctiva/"
        "preventiva ha sido eficaz (el hallazgo no ha vuelto a producirse). "
        "Se propone automáticamente al cerrar la acción; editable a mano.",
    )

    def write(self, vals):
        # El módulo base solo rellena date_closed la primera vez que la
        # acción entra en un stage "is_ending" (Cerrado o Cancelado) y ya no
        # lo toca después. Aquí lo tratamos como lo que es, una fecha de
        # cierre real: solo tiene sentido si el stage actual es "Cerrado", se
        # actualiza cada vez que se llega a él (incluida una corrección desde
        # Cancelado) y se borra en cualquier otro caso (Cancelado, reabierta,
        # etc.).
        estados_previos = {a.id: a.stage_id.id for a in self} if "stage_id" in vals else {}
        res = super().write(vals)
        if "stage_id" in vals:
            stage_close = self.env.ref(
                "mgmtsystem_action.stage_close", raise_if_not_found=False
            )
            cambiadas = self.filtered(
                lambda a: a.stage_id.id != estados_previos.get(a.id)
            )
            cerradas = cambiadas.filtered(lambda a: stage_close and a.stage_id == stage_close)
            resto = (cambiadas - cerradas).filtered("date_closed")
            if cerradas:
                cerradas.write({"date_closed": fields.Datetime.now()})
                cerradas._proponer_revision_eficacia()
            if resto:
                resto.write({"date_closed": False})
        return res

    def _proponer_revision_eficacia(self):
        """Al cerrar una acción correctiva/preventiva, propone una fecha de
        revisión de eficacia (si no hay ya una puesta a mano) y programa un
        recordatorio (actividad) al inspector, o al responsable de la acción
        si aún no hay inspector asignado."""
        for accion in self:
            if accion.type_action not in TIPOS_ACCION_CON_REVISION_EFICACIA:
                continue
            if not accion.efficacy_review_date:
                accion.efficacy_review_date = fields.Date.today() + timedelta(
                    days=DIAS_REVISION_EFICACIA_DEFECTO
                )
            usuario = accion.efficacy_user_id or accion.user_id
            accion.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=accion.efficacy_review_date,
                summary=_("Revisar eficacia: %s") % accion.name,
                user_id=usuario.id,
            )
```

- [ ] **Step 4: Exponer el campo en la vista y añadir el filtro de búsqueda**

En `addons/leulit_seguridad/views/mgmtsystem_action.xml`, añadir estos dos `<record>` justo antes de `</odoo>` (después del `<record id="leulit_20260112_0833_action" ...>` existente):

```xml
        <record id="view_mgmtsystem_action_form_efficacy_leulit" model="ir.ui.view">
            <field name="name">mgmtsystem.action.form.efficacy.leulit</field>
            <field name="model">mgmtsystem.action</field>
            <field name="inherit_id" ref="mgmtsystem_action_efficacy.view_mgmtsystem_action_form"/>
            <field name="arch" type="xml">
                <field name="efficacy_description" position="after">
                    <field name="efficacy_review_date"/>
                </field>
            </field>
        </record>

        <record id="view_mgmtsystem_action_filter_efficacy_leulit" model="ir.ui.view">
            <field name="name">mgmtsystem.action.filter.efficacy.leulit</field>
            <field name="model">mgmtsystem.action</field>
            <field name="inherit_id" ref="mgmtsystem_action.view_mgmtsystem_action_filter"/>
            <field name="arch" type="xml">
                <filter name="pending" position="after">
                    <filter
                        name="revision_eficacia_pendiente"
                        string="Revisión de eficacia pendiente"
                        domain="[('stage_id', '=', %(mgmtsystem_action.stage_close)d),
                                 ('efficacy_review_date', '!=', False),
                                 ('efficacy_review_date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"
                    />
                </filter>
            </field>
        </record>
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

El usuario ejecuta en su Docker de test:

```bash
./upd_module.sh leulit_seguridad dev --stop
docker exec -ti helipistas_odoo_17 odoo -u leulit_seguridad -d productiu \
  --test-enable --test-tags=/leulit_seguridad:TestMgmtsystemActionEfficacyReviewDate \
  --stop-after-init
```

Expected: PASS en los 5 tests, sin ERROR/CRITICAL en el log.

- [ ] **Step 6: Commit**

```bash
git add addons/leulit_seguridad/models/mgmtsystem_action.py \
        addons/leulit_seguridad/views/mgmtsystem_action.xml \
        addons/leulit_seguridad/tests/__init__.py \
        addons/leulit_seguridad/tests/test_mgmtsystem_action_efficacy.py
git commit -m "feat(leulit_seguridad): revisión de eficacia post-cierre en acciones correctivas/preventivas"
```

---

### Task 3: Verificación manual en UI y registro en DEVLOG

**Files:**
- Create: `docs/DEVLOG.md` (si no existe) o modificar (añadir entrada al final)

**Interfaces:**
- Consumes: todo lo producido en Task 1 y Task 2, ya desplegado en el entorno de test.
- Produces: nada que consuma otra tarea — es el cierre del plan.

- [ ] **Step 1: Verificación manual en el entorno de pruebas**

Con los módulos ya actualizados (Task 1 Step 2 + Task 2 Step 5 ya ejecutados), el usuario:
1. Abre una No Conformidad de tipo con acción correctiva, la mueve por el flujo hasta crear una acción de tipo "Corrective Action" o "Preventive Action" y la cierra.
2. Comprueba que en la pestaña "Efficacy" de esa acción aparece `Fecha revisión eficacia` rellena (hoy + 90 días).
3. Comprueba que le ha llegado una actividad "Revisar eficacia: ..." en su bandeja de actividades de Odoo, con esa fecha límite.
4. Va a Seguridad → Acciones, aplica el filtro "Revisión de eficacia pendiente" y confirma que la acción cerrada aparece (puede necesitar editar la fecha manualmente a hoy o antes para verla, ya que por defecto queda a +90 días).
5. Cierra una acción de tipo "Immediate Action" y confirma que NO se le propone fecha ni actividad (contención, no corrección de causa raíz).

- [ ] **Step 2: Registrar en DEVLOG**

Si `docs/DEVLOG.md` no existe, crearlo con este contenido; si existe, añadir la entrada al final manteniendo el formato existente:

```markdown
# DEVLOG

## 2026-09-14 — Revisión de eficacia de acciones correctivas/preventivas (leulit_seguridad)

AESA pide evidencia de que las acciones correctivas de No Conformidad se
verifican como eficaces tras un plazo, no solo que se cierran. Se activó el
módulo OCA `mgmtsystem_action_efficacy` (ya vendorizado, sin instalar) y se
añadió `efficacy_review_date` en `mgmtsystem.action`: se propone
automáticamente (+90 días, editable) al cerrar una acción `correction`/
`prevention`, con un recordatorio (`mail.activity`) al inspector o al
responsable de la acción. Filtro "Revisión de eficacia pendiente" en
Seguridad → Acciones para que el responsable de calidad pueda revisarlas.

El plazo de 90 días es un valor de partida (`ponytail:` en
`models/mgmtsystem_action.py`), pendiente de confirmar con el responsable de
calidad/seguridad — no es un número que exija AESA explícitamente.

Ver plan: `docs/superpowers/plans/2026-09-14-analisis-efectividad-nc.md`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/DEVLOG.md
git commit -m "docs: registrar revisión de eficacia de acciones correctivas en DEVLOG"
```

---

## Fuera de alcance (deliberado)

- **No se ha fijado el plazo real de revisión** (90 días es un placeholder de código, ver arriba) — es una decisión de calidad/AESA, no técnica.
- **No se generó un indicador/pivot de "% acciones eficaces"** para enseñar en auditoría — el filtro de búsqueda de Task 2 ya permite verlo agrupando por `efficacy_value`; un pivot dedicado es una iteración posterior si hace falta enseñarlo con más formato.
- **No se toca `mgmtsystem.nonconformity`** ni su wizard de cierre — la NC sigue cerrándose igual; la eficacia vive en sus acciones, que es donde ya está modelada la causa/corrección.
- **No se añade validación que bloquee cerrar una acción sin `efficacy_user_id`** — mantiene compatible el flujo de cierre actual (wizard "Cerrar NC" incluido); si se cierra sin inspector asignado, el recordatorio cae en el responsable de la acción.
