# Parte piloto privado — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** módulo nuevo `leulit_parte_privado` con un wizard "Parte piloto privado" que crea, firma (prevuelo→postvuelo) y cierra (postvuelo→cerrado) un `leulit.vuelo` en nombre del piloto privado, sin tocar el workflow actual.

**Architecture:** wizard `TransientModel` que crea el vuelo `with_user(usuario_piloto)`, deriva los datos llamando a `onchange_helicoptero()` + `calculosFuel()` existentes, ejecuta dos cadenas compuestas con los handlers **importados** de `vuelo_chain_postvuelo.py` / `vuelo_chain_cerrado.py` (más un handler propio sin meteo/W&B/performance), y firma con la maquinaria existente (`buildSignature` + `buildPdfSigned`). Todo aditivo: dos campos `_inherit`, un grupo en `leulit/groups.xml`, un menú.

**Tech Stack:** Odoo 17 Community, Python 3, XML views. Sin Odoo local: verificación sintáctica aquí (`py_compile`, `xmllint`), funcional en el Docker del usuario.

**Spec:** `docs/superpowers/specs/2026-09-01-parte-piloto-privado-design.md`

## Global Constraints

- **Invariante §2:** no se edita ningún fichero de `leulit_operaciones` ni `leulit_esignature`. Único cambio fuera del módulo: un `<record>` nuevo en `addons/leulit/groups.xml`.
- Odoo 17 **Community** only.
- Estilo: imitar el código circundante, **nunca** formateadores automáticos.
- Commits directos en `main` (preferencia del usuario), mensaje con `Co-Authored-By` de sesión.
- Convención xmlid: `leulit_YYYYMMDD_HHMM_<tipo>`.
- Correcciones al spec detectadas al trazar el código (aplicar, no discutir):
  - `tipo_actividad` es un **compute** desde `vuelo_tipo_line[0].vuelo_tipo_id.tipo_trabajo` (`leulit_vuelo.py:1876`). "NCO fijo" se garantiza con `domain=[('tipo_trabajo','=','NCO')]` en el selector de tipo de vuelo, no con una constante.
  - El menú raíz "Operaciones" (`leulit.leulit_20200618_1104_menuitem`) tiene `groups="ROperaciones_operador,RCampaña_operador"`. El módulo nuevo añade el grupo nuevo a ese menú reutilizando su xmlid completo (patrón ya usado en `leulit_operaciones/security.xml` con `hr.menu_hr_root`).
  - `onchange_helicoptero()` escribe `lugarsalida` = llegada del último vuelo cerrado; hay que reescribir `lugarsalida` del wizard después de llamarlo.
  - `check_first_flight()` (EC120B / CABRI G2) exige `checklist_prevuelo_BFF` si no hay vuelo cerrado ese día para esa máquina, o `checklist_prevuelo_entre_vuelos` si lo hay. El wizard calcula ambos flags.
  - Rollback total imposible sin editar handlers (hacen `cr.commit()`). Aproximación: si falla un eslabón tras el primer commit, el vuelo queda **cancelado** (inerte) y se relanza el error. Documentado en README.
- `sale.order`: `RBase` no tiene ACL de lectura en los módulos leulit; el módulo da lectura al grupo nuevo (necesaria para el m2o del presupuesto).

---

## Estructura de ficheros

```
addons/leulit/groups.xml                       MODIFY  (+ record ROperaciones_parte_privado)
addons/leulit_parte_privado/
  __manifest__.py
  __init__.py
  README.md
  models/__init__.py
  models/leulit_piloto.py                      privado = Boolean
  models/leulit_vuelo.py                       privado_introducido_por = Many2one res.users
  chains/__init__.py
  chains/vuelo_chain_privado.py                DatosGeneralesPrivadoHandler + chain_to_postvuelo() + chain_to_cerrado()
  wizard/__init__.py
  wizard/parte_privado_wizard.py               leulit.parte.privado.wizard + finalizar()
  wizard/parte_privado_wizard_view.xml         form + act_window
  views/leulit_piloto_view.xml                 xpath after freelance
  security/ir.model.access.csv                 wizard CRUD + sale.order read
  menu.xml                                     menú bajo Vuelos + grupo en menú raíz Operaciones
  tests/__init__.py
  tests/test_parte_privado.py
CLAUDE.md                                      MODIFY  (+ parte_privado en la lista de módulos)
```

---

### Task 1: grupo, esqueleto del módulo, campos `_inherit`, vista piloto, ACL

**Files:**
- Modify: `addons/leulit/groups.xml` (tras el record `ROperaciones_gestor`, ~línea 89)
- Create: `addons/leulit_parte_privado/__manifest__.py`, `__init__.py`, `models/__init__.py`, `models/leulit_piloto.py`, `models/leulit_vuelo.py`, `views/leulit_piloto_view.xml`, `security/ir.model.access.csv`, `chains/__init__.py`, `wizard/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: grupo `leulit.ROperaciones_parte_privado`; campo `leulit.piloto.privado` (Boolean); campo `leulit.vuelo.privado_introducido_por` (Many2one `res.users`).

- [ ] **Step 1: grupo en `leulit/groups.xml`**

Insertar justo después del record `ROperaciones_gestor` (cierra en `</record>` tras `implied_ids ... ROperaciones_responsable`):

```xml
        <record id="ROperaciones_parte_privado" model="res.groups">
            <field name="name">Parte piloto privado</field>
            <field name="category_id" ref="operaciones_rol_category"/>
        </record>
```

- [ ] **Step 2: manifest e inits**

`addons/leulit_parte_privado/__manifest__.py`:
```python
{
    "name": "Parte piloto privado",
    "summary": "Transcripción del PTV en papel de pilotos privados: crea, firma y cierra el vuelo en nombre del piloto",
    "author": "Leulit S.L.",
    "website": "http://www.leulit.com",
    "category": "leulit",
    "version": "17.0.1.0.0",
    "depends": [
        "leulit",
        "leulit_operaciones",
        "leulit_esignature"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/leulit_piloto_view.xml",
        "wizard/parte_privado_wizard_view.xml",
        "menu.xml"
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3"
}
```
`__init__.py`: `from . import models, wizard`
`models/__init__.py`: `from . import leulit_piloto, leulit_vuelo`
`wizard/__init__.py`: `from . import parte_privado_wizard` (el fichero se crea en Task 2; hasta entonces el módulo no instala — se instala al final de Task 2)
`chains/__init__.py`, `tests/__init__.py`: `tests/__init__.py` = `from . import test_parte_privado` (fichero en Task 3); `chains/__init__.py` vacío.

- [ ] **Step 3: campos `_inherit`**

`models/leulit_piloto.py`:
```python
# -*- encoding: utf-8 -*-
from odoo import models, fields


class LeulitPiloto(models.Model):
    _inherit = "leulit.piloto"

    privado = fields.Boolean(string="Piloto privado", help="Sus partes en papel se transcriben desde Vuelos > Parte piloto privado")
```
`models/leulit_vuelo.py`:
```python
# -*- encoding: utf-8 -*-
from odoo import models, fields


class LeulitVuelo(models.Model):
    _inherit = "leulit.vuelo"

    privado_introducido_por = fields.Many2one(comodel_name="res.users", string="Introducido por (parte privado)", readonly=True)
```

- [ ] **Step 4: vista piloto y ACL**

`views/leulit_piloto_view.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="leulit_20260902_1000_form" model="ir.ui.view">
        <field name="name">leulit.piloto.form.privado</field>
        <field name="model">leulit.piloto</field>
        <field name="inherit_id" ref="leulit_operaciones.leulit_20200708_1210_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='freelance']" position="after">
                <field name="privado"/>
            </xpath>
        </field>
    </record>
</odoo>
```
`security/ir.model.access.csv`:
```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_parte_privado_wizard,leulit.parte.privado.wizard,model_leulit_parte_privado_wizard,leulit.ROperaciones_parte_privado,1,1,1,1
access_parte_privado_sale_order,sale.order lectura parte privado,sale.model_sale_order,leulit.ROperaciones_parte_privado,1,0,0,0
```

- [ ] **Step 5: verificar sintaxis**

```bash
python3 -m py_compile addons/leulit_parte_privado/__manifest__.py addons/leulit_parte_privado/models/*.py
xmllint --noout addons/leulit/groups.xml addons/leulit_parte_privado/views/leulit_piloto_view.xml
```
Expected: sin salida (exit 0).

- [ ] **Step 6: commit** (junto con Task 2, el módulo no es instalable hasta que exista el wizard)

---

### Task 2: cadenas paralelas, wizard, vista, menú

**Files:**
- Create: `chains/vuelo_chain_privado.py`, `wizard/parte_privado_wizard.py`, `wizard/parte_privado_wizard_view.xml`, `menu.xml`

**Interfaces:**
- Consumes: handlers de `odoo.addons.leulit_operaciones.vuelo_chain_postvuelo` / `vuelo_chain_cerrado`; `leulit.vuelo.onchange_helicoptero()`, `calculosFuel(field)`, `buildPdfSigned(datos, esignature)`, `verificar_actividad_aerea(fecha, partner)`; `leulit_signaturedoc.buildSignature(modelo, idmodelo, code)`; `res.users.get_otp()`, `get_otp_secret()`.
- Produces: `vuelo_chain_privado.chain_to_postvuelo()`, `chain_to_cerrado()` → primer handler enlazado; `leulit.parte.privado.wizard.finalizar()`.

- [ ] **Step 1: `chains/vuelo_chain_privado.py`**

```python
# -*- encoding: utf-8 -*-
"""Cadenas paralelas del parte privado: mismos eslabones que el flujo normal, importados,
menos los que no aplican a un vuelo NCO transcrito (meteo, W&B, performance, escuela, perfiles)."""
from typing import Any
from odoo.exceptions import UserError
from odoo.addons.leulit import utilitylib
from odoo.addons.leulit_operaciones import vuelo, vuelo_chain_postvuelo as post, vuelo_chain_cerrado as cerr

import logging
_logger = logging.getLogger(__name__)


class DatosGeneralesPrivadoHandler(vuelo.AbstractHandler):
    """ComprobacionDatosGeneralesHandler de vuelo_chain_postvuelo sin meteo, C.G., performance ni pasajeros_wb."""

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> DatosGeneralesPrivadoHandler")
        if not request.error:
            v = request.env['leulit.vuelo'].browse(request.vuelo_id)
            if v.distanciatotalprevista == 0:
                raise UserError('Distancia total prevista no válida ')
            if v.numtripulacion == 0:
                raise UserError('Número de personas tripulación no válido ')
            if v.tiempoprevisto > 3.0:
                raise UserError('El valor del tiempo previsto de vuelo no puede ser superior a 3 horas')
            if not v.notam_revisado:
                raise UserError('Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM')
            if v.horasalida <= 0:
                raise UserError('Hora de salida no válida')
            if v.tacomsalida <= 0 and request.tipo_helicoptero != "EC120B":
                raise UserError('Valor tacómetro de salida no válido')
            if v.oilqty < 0:
                raise UserError('Es obligatorio indicar la cantidad de aceite añadida. 0 es un valor válido.')
            if not v.helicoptero_id.horas_remanente > v.tiempoprevisto:
                raise UserError('El tiempo de vuelo previsto (%s) excede el número de horas disponibles (%s) para esta máquina' % (utilitylib.leulit_float_time_to_str(v.tiempoprevisto), utilitylib.leulit_float_time_to_str(v.helicoptero_id.horas_remanente)))
            if v.ruta_id.water_zone and not v.flotadores:
                raise UserError("La ruta establecida tiene areas autorotativas sobre el agua, marca el check de Flotadores.")
            if not v.vuelo_tipo_line:
                raise UserError('No hay comentario logbook')
        return super().handle(request)


def _enlazar(handlers):
    for a, b in zip(handlers, handlers[1:]):
        a.set_next(b)
    return handlers[0]


def chain_to_postvuelo():
    return _enlazar([
        post.ComprobacionTripulacionEnVuelosPostvueloHandler(),
        post.ComprobacionChecksHandler(),
        post.ComprobacionTripulantesTipoActividadHandler(),
        post.ComprobacionUsuarioPilotoHandler(),
        post.ComprobacionHelicopteroHandler(),
        post.ComprobacionOverlapPartesEscuelaVueloHandler(),
        DatosGeneralesPrivadoHandler(),
        post.ComprobacionDatosCombustibleHandler(),
        # omitidos: ComprobacionParteEscuelaHandler, ComprobacionPerfilesFormacionHandler (spec §3)
    ])


def chain_to_cerrado():
    # Igual que initChainToCerrado pero con ComprobacionDatosCombustibleHandler realmente enlazado
    # (el original lo pisa al asignar chain7 dos veces) y sin ComprobacionParteEscuelaHandler.
    return _enlazar([
        cerr.ComprobacionPresupuestoHandler(),
        cerr.ComprobacionChecksHandler(),
        cerr.ComprobacionUsuarioPilotoHandler(),
        cerr.ComprobacionDescansoHandler(),
        cerr.ComprobacionHelicopteroHandler(),
        cerr.ComprobacionOverlapPartesEscuelaVueloHandler(),
        cerr.ComprobacionDatosGeneralesHandler(),
        cerr.ComprobacionDatosCombustibleHandler(),
        cerr.UpdateProximoVueloHandler(),
    ])
```

- [ ] **Step 2: `wizard/parte_privado_wizard.py`**

```python
# -*- encoding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.addons.leulit_operaciones import vuelo_chain_postvuelo, vuelo_chain_cerrado
from ..chains import vuelo_chain_privado

import logging
_logger = logging.getLogger(__name__)


class PartePrivadoWizard(models.TransientModel):
    _name = "leulit.parte.privado.wizard"
    _description = "Parte piloto privado"

    fechavuelo = fields.Date('Fecha', required=True, default=fields.Date.context_today)
    helicoptero_id = fields.Many2one('leulit.helicoptero', 'Helicóptero', required=True, domain="[('baja','=',False)]")
    helicoptero_tipo = fields.Selection(related='helicoptero_id.tipo')
    piloto_id = fields.Many2one('leulit.piloto', 'Piloto', required=True, domain="[('privado','=',True)]")
    presupuesto_vuelo = fields.Many2one('sale.order', 'Presupuesto', required=True, domain=[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)])
    vuelo_tipo_id = fields.Many2one('leulit.vuelostipo', 'Tipo vuelo', required=True, domain="[('tipo_trabajo','=','NCO')]")
    numpax = fields.Integer('Nº de pax / AESA', default=0)
    numpae = fields.Integer('Num. AL/PA/PE/PAE/PO', required=True)
    lugarsalida = fields.Many2one('leulit.helipuerto', 'Helipuerto salida', required=True)
    lugarllegada = fields.Many2one('leulit.helipuerto', 'Helipuerto llegada', required=True)
    horasalida = fields.Float('Hora salida local', required=True)
    horallegada = fields.Float('Hora llegada local', required=True)
    tiemposervicio = fields.Float('Tiempo servicio', required=True)
    airtime = fields.Float('Air Time', required=True)
    fuelqty = fields.Float('Combustible añadido (l.)')
    oilqty = fields.Float('Aceite añadido (l.)')
    fuelllegada = fields.Float('Combustible llegada (l.)', required=True)
    tacomllegada = fields.Float('Tacom. llegada')
    ngvuelo = fields.Float('NG vuelo')
    nfvuelo = fields.Float('NF vuelo')
    comentarios = fields.Text('Observaciones (O.V.)')
    declaracion = fields.Boolean('Inspección prevuelo, briefing, NOTAM y debriefing realizados')

    def _usuario_piloto(self):
        user = self.piloto_id.partner_id.user_ids.filtered('active')[:1]
        if not user:
            raise UserError(_("El piloto %s no tiene usuario activo en el ERP; no se puede firmar en su nombre.") % self.piloto_id.name)
        return user

    def _vals_vuelo(self, hay_vuelo_anterior):
        tiempoprevisto = self.horallegada - self.horasalida
        if tiempoprevisto < 0:
            tiempoprevisto += 24.0
        return {
            'fechavuelo'                     : self.fechavuelo,
            'helicoptero_id'                 : self.helicoptero_id.id,
            'piloto_id'                      : self.piloto_id.id,
            'presupuesto_vuelo'              : self.presupuesto_vuelo.id,
            'vuelo_tipo_line'                : [(0, 0, {'vuelo_tipo_id': self.vuelo_tipo_id.id})],
            'numpax'                         : self.numpax,
            'numpae'                         : self.numpae,
            'lugarsalida'                    : self.lugarsalida.id,
            'lugarllegada'                   : self.lugarllegada.id,
            'horasalida'                     : self.horasalida,
            'horallegada'                    : self.horallegada,
            'tiempoprevisto'                 : round(tiempoprevisto, 2),
            'tiemposervicio'                 : self.tiemposervicio,
            'airtime'                        : self.airtime,
            'fuelqty'                        : self.fuelqty,
            'oilqty'                         : self.oilqty,
            'fuelllegada'                    : self.fuelllegada,
            'tacomllegada'                   : self.tacomllegada,
            'ngvuelo'                        : self.ngvuelo,
            'nfvuelo'                        : self.nfvuelo,
            'comentarios'                    : self.comentarios,
            'checklist_realizado'            : True,
            'briefing_realizado'             : True,
            'notam_revisado'                 : True,
            'checklist_postvuelo_realizado'  : True,
            'checklist_prevuelo_BFF'         : not hay_vuelo_anterior,
            'checklist_prevuelo_entre_vuelos': hay_vuelo_anterior,
            # constantes spec §4.4; el resto (nightlandings, arlanding, sling_cycle, ifr, nv, balsa,
            # flotadores, chalecos, uso_gancho, distancia_alternativo) ya son los defaults del modelo
            'numtripulacion'                 : 1,
            'asiento_pic'                    : 'pic_right',
            'reservasfuel'                   : '30',
            'rodaje'                         : '0',
            'contingencia'                   : '0',
            'landings'                       : 1,
            'privado_introducido_por'        : self.env.user.id,
        }

    @staticmethod
    def _ejecutar(chain, request, vuelo):
        request.env = vuelo.env
        request.vuelo_id = vuelo.id
        request.uid = vuelo.env.uid
        request.tipo_helicoptero = vuelo.helicoptero_id.modelo.tipo
        chain.handle(request)

    @staticmethod
    def _firmar(vuelo):
        # Equivale a leulit_signaturedoc.checksignatureRef con el OTP real del piloto (env.user = piloto)
        otp = vuelo.env.user.get_otp()
        esignature = vuelo.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', vuelo.id, otp)
        vuelo.buildPdfSigned(None, esignature)

    def finalizar(self):
        self.ensure_one()
        if not self.declaracion:
            raise UserError(_("Debe confirmar la declaración de inspección prevuelo, briefing, NOTAM y debriefing."))
        user = self._usuario_piloto()
        user.sudo().get_otp_secret()
        Vuelo = self.env['leulit.vuelo'].with_user(user)
        hay_anterior = bool(Vuelo.search([('helicoptero_id','=',self.helicoptero_id.id),('estado','=','cerrado'),('fechavuelo','=',self.fechavuelo),('horasalida','<',self.horasalida)], limit=1))
        vuelo = Vuelo.create(self._vals_vuelo(hay_anterior))
        try:
            vuelo.onchange_helicoptero()                          # pesos, velocidad, consumo, tacom/fuel del último vuelo cerrado
            vuelo.write({'lugarsalida': self.lugarsalida.id})     # el onchange lo pisa con la llegada del vuelo anterior
            vuelo.calculosFuel('tiempoprevisto')                  # distancia, hora llegada prevista, combustibles
            self._ejecutar(vuelo_chain_privado.chain_to_postvuelo(), vuelo_chain_postvuelo.VueloChainToPostvueloRequest(), vuelo)
            self._firmar(vuelo)                                   # prevuelo -> postvuelo, POV/PTV (+F27 si EC120B con BFF)
            self._ejecutar(vuelo_chain_privado.chain_to_cerrado(), vuelo_chain_cerrado.VueloChainToCerradoRequest(), vuelo)
            if not vuelo.verificar_actividad_aerea(vuelo.fechavuelo, vuelo.piloto_id.partner_id):
                raise UserError(_("No se puede firmar el parte de vuelo porque se ha excedido el tiempo máximo de actividad aérea. Debe crear una ocurrencia para gestionar el exceso de tiempo de actividad aérea."))
            self._firmar(vuelo)                                   # postvuelo -> cerrado, control_firma = firmado
        except Exception as e:
            # ponytail: los handlers hacen cr.commit(), no hay rollback total sin editarlos (invariante spec §2).
            # Se vuelve al último commit y el vuelo queda cancelado para no bloquear helicóptero/piloto.
            self.env.cr.rollback()
            self.env.invalidate_all()
            if vuelo.exists() and vuelo.estado != 'cerrado':
                vuelo.sudo().write({'estado': 'cancelado', 'comentarios': 'Parte piloto privado fallido: %s' % e})
                self.env.cr.commit()
            raise
        vuelo.with_env(self.env).message_post(body=_("Parte introducido por %s mediante Parte piloto privado en nombre de %s") % (self.env.user.name, self.piloto_id.name))
        return {'type': 'ir.actions.act_window_close'}
```

- [ ] **Step 3: `wizard/parte_privado_wizard_view.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="leulit_20260902_1010_form" model="ir.ui.view">
        <field name="name">leulit.parte.privado.wizard.form</field>
        <field name="model">leulit.parte.privado.wizard</field>
        <field name="arch" type="xml">
            <form string="Parte piloto privado">
                <group>
                    <group string="Vuelo">
                        <field name="fechavuelo"/>
                        <field name="helicoptero_id" options="{'no_create': True}"/>
                        <field name="helicoptero_tipo" invisible="1"/>
                        <field name="piloto_id" options="{'no_create': True}"/>
                        <field name="presupuesto_vuelo" options="{'no_create': True}"/>
                        <field name="vuelo_tipo_id" options="{'no_create': True}"/>
                        <field name="numpax"/>
                        <field name="numpae"/>
                    </group>
                    <group string="Trayecto">
                        <field name="lugarsalida" options="{'no_create': True}"/>
                        <field name="lugarllegada" options="{'no_create': True}"/>
                        <field name="horasalida" widget="float_time"/>
                        <field name="horallegada" widget="float_time"/>
                        <field name="tiemposervicio" widget="float_time"/>
                        <field name="airtime" widget="float_time"/>
                    </group>
                    <group string="Combustible y contadores">
                        <field name="fuelqty"/>
                        <field name="oilqty"/>
                        <field name="fuelllegada"/>
                        <field name="tacomllegada" invisible="helicoptero_tipo == 'EC120B'" required="helicoptero_tipo != 'EC120B'"/>
                        <field name="ngvuelo" invisible="helicoptero_tipo != 'EC120B'" required="helicoptero_tipo == 'EC120B'"/>
                        <field name="nfvuelo" invisible="helicoptero_tipo != 'EC120B'" required="helicoptero_tipo == 'EC120B'"/>
                    </group>
                    <group string="Observaciones">
                        <field name="comentarios" nolabel="1" colspan="2"/>
                        <field name="declaracion"/>
                    </group>
                </group>
                <footer>
                    <button name="finalizar" type="object" string="Finalizar" class="oe_highlight"/>
                    <button string="Cancelar" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="leulit_20260902_1010_action" model="ir.actions.act_window">
        <field name="name">Parte piloto privado</field>
        <field name="res_model">leulit.parte.privado.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
</odoo>
```

- [ ] **Step 4: `menu.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- El menú raíz Operaciones está restringido a ROperaciones_operador; se añade el grupo nuevo sin quitar los existentes -->
    <record id="leulit.leulit_20200618_1104_menuitem" model="ir.ui.menu">
        <field name="groups_id" eval="[(4, ref('leulit.ROperaciones_parte_privado'))]"/>
    </record>

    <menuitem
        id="leulit_20260902_1010_menuitem"
        name="Parte piloto privado"
        parent="leulit_operaciones.leulit_20201023_1053_menuitem"
        action="leulit_20260902_1010_action"
        groups="leulit.ROperaciones_parte_privado"
        sequence="16"
    />
</odoo>
```

- [ ] **Step 5: verificar sintaxis**

```bash
python3 -m py_compile addons/leulit_parte_privado/chains/*.py addons/leulit_parte_privado/wizard/*.py
xmllint --noout addons/leulit_parte_privado/wizard/*.xml addons/leulit_parte_privado/menu.xml
```
Expected: exit 0.

- [ ] **Step 6: commit**

```bash
git add addons/leulit/groups.xml addons/leulit_parte_privado
git commit -m "feat(parte_privado): módulo leulit_parte_privado — wizard parte piloto privado, cadenas paralelas y firma en nombre del piloto"
```

---

### Task 3: tests, README, CLAUDE.md

**Files:**
- Create: `tests/test_parte_privado.py`, `README.md`
- Modify: `CLAUDE.md` (lista de módulos funcionales)

- [ ] **Step 1: `tests/test_parte_privado.py`**

```python
# -*- encoding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests import common, tagged
from odoo.exceptions import UserError, AccessError


@tagged('post_install', '-at_install')
class TestPartePrivado(common.TransactionCase):

    def setUp(self):
        super().setUp()
        grupo = self.env.ref('leulit.ROperaciones_parte_privado')
        self.operador = self.env['res.users'].create({
            'name'      : 'Operador parte privado',
            'login'     : 'operador_parte_privado_test',
            'groups_id' : [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('leulit.RBase').id, grupo.id])],
        })
        self.Wizard = self.env['leulit.parte.privado.wizard'].with_user(self.operador)

    def test_sin_grupo_no_accede(self):
        sin_grupo = self.env['res.users'].create({'name': 'Sin grupo', 'login': 'sin_grupo_parte_privado_test', 'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]})
        with self.assertRaises(AccessError):
            self.env['leulit.parte.privado.wizard'].with_user(sin_grupo).check_access_rights('create')

    def test_piloto_sin_usuario(self):
        partner = self.env['res.partner'].new({'name': 'Piloto sin usuario'})
        piloto = self.env['leulit.piloto'].new({'partner_id': partner.id, 'privado': True})
        wiz = self.Wizard.new({'piloto_id': piloto.id})
        with self.assertRaises(UserError):
            wiz._usuario_piloto()

    def _datos_reales(self):
        """Datos maestros de la BD de pruebas; None si faltan (el test se salta)."""
        Vuelo = self.env['leulit.vuelo']
        piloto = self.env['leulit.piloto'].search([('privado','=',True),('partner_id.user_ids.active','=',True)], limit=1)
        presupuesto = self.env['sale.order'].search([('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)], limit=1)
        tipo = self.env['leulit.vuelostipo'].search([('tipo_trabajo','=','NCO')], limit=1)
        helipuerto = self.env['leulit.helipuerto'].search([], limit=1)
        heli = False
        for h in self.env['leulit.helicoptero'].search([('baja','=',False),('statemachine','=','En servicio')]):
            if h.horas_remanente > 2 and h.consumomedio > 0 and h.velocidad > 0 and not Vuelo.search([('helicoptero_id','=',h.id),('estado','=','prevuelo')], limit=1):
                heli = h
                break
        if not (piloto and presupuesto and tipo and helipuerto and heli):
            return None
        ultimo = Vuelo.search([('helicoptero_id','=',heli.id),('estado','in',['postvuelo','cerrado'])], order='fechasalida desc', limit=1)
        fecha = (ultimo.fechavuelo if ultimo else fields.Date.today()) + timedelta(days=1)
        objetivo_fuel = 300 if heli.tipo == 'EC120B' else 100
        return {
            'fechavuelo'      : fecha,
            'helicoptero_id'  : heli.id,
            'piloto_id'       : piloto.id,
            'presupuesto_vuelo': presupuesto.id,
            'vuelo_tipo_id'   : tipo.id,
            'numpax'          : 0,
            'numpae'          : 0,
            'lugarsalida'     : helipuerto.id,
            'lugarllegada'    : helipuerto.id,
            'horasalida'      : 10.0,
            'horallegada'     : 11.0,
            'tiemposervicio'  : 1.0,
            'airtime'         : 0.9,
            'fuelqty'         : max(0.0, objetivo_fuel - (ultimo.fuelllegada if ultimo else 0.0)),
            'oilqty'          : 0.0,
            'fuelllegada'     : 40.0,
            'tacomllegada'    : (ultimo.tacomllegada if ultimo else 0.0) + 1.0,
            'ngvuelo'         : 1.0,
            'nfvuelo'         : 1.0,
            'declaracion'     : True,
        }

    def test_flujo_completo(self):
        datos = self._datos_reales()
        if not datos:
            self.skipTest('faltan datos maestros: piloto privado con usuario activo, helicóptero en servicio con potencial, presupuesto NCO en sale, tipo de vuelo NCO, helipuerto')
        Vuelo = self.env['leulit.vuelo']

        # 1) fallo tardío (cadena B: combustible llegada 0) -> UserError y vuelo cancelado, no bloquea
        with self.assertRaises(UserError):
            self.Wizard.create(dict(datos, fuelllegada=0.0)).finalizar()
        fallido = Vuelo.search([('privado_introducido_por','=',self.operador.id)])
        self.assertTrue(all(v.estado == 'cancelado' for v in fallido))

        # 2) ciclo feliz
        self.Wizard.create(datos).finalizar()
        vuelo = Vuelo.search([('privado_introducido_por','=',self.operador.id),('estado','=','cerrado')])
        self.assertEqual(len(vuelo), 1)
        self.assertEqual(vuelo.control_firma, 'firmado')
        self.assertEqual(vuelo.tipo_actividad, 'NCO')
        self.assertEqual(vuelo.lugarsalida.id, datos['lugarsalida'])
        self.assertEqual(vuelo.create_uid.partner_id, vuelo.piloto_id.partner_id)
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.vuelo'),('idmodelo','=',vuelo.id)])
        self.assertTrue(any(d.referencia.endswith('-POV') for d in docs))
        self.assertTrue(any(d.referencia.endswith('-PTV') for d in docs))
        self.assertTrue(all(d.firmado_por == vuelo.piloto_id.partner_id for d in docs))
        self.assertTrue(any('Parte piloto privado' in (m.body or '') for m in vuelo.message_ids))
```

- [ ] **Step 2: `README.md` del módulo**

Contenido: qué es, quién lo usa (grupo), prerequisitos de datos (spec §5 + orden cronológico: la cadena rechaza cualquier parte posterior en postvuelo/cerrado de la misma máquina, así que los partes privados se introducen en orden), flujo de `finalizar()`, qué se omite (meteo, W&B, performance, escuela, perfiles), qué queda si falla (vuelo cancelado + error), trazabilidad, instalación/actualización y tests. Nota: el usuario del grupo nuevo también ve "Partes de vuelo" (menú sin grupos) además del wizard.

- [ ] **Step 3: `CLAUDE.md`** — añadir `parte_privado` en la lista `leulit_*` del Module layout.

- [ ] **Step 4: verificar sintaxis + git status limpio de basura**

```bash
python3 -m py_compile addons/leulit_parte_privado/tests/*.py
git status --short
```

- [ ] **Step 5: commit**

```bash
git add addons/leulit_parte_privado CLAUDE.md docs/superpowers/plans/2026-09-02-parte-piloto-privado.md docs/superpowers/specs/2026-09-01-parte-piloto-privado-design.md
git commit -m "test(parte_privado): tests, README y plan"
```

---

## Verificación en el entorno del usuario (no hay Odoo local)

```bash
./upd_module.sh leulit dev                                   # grupo nuevo (solo XML)
docker exec -ti helipistas_odoo_17 odoo -i leulit_parte_privado -d productiu --stop-after-init
docker exec -ti helipistas_odoo_17 odoo -u leulit_parte_privado -d productiu --test-enable --test-tags=/leulit_parte_privado --stop-after-init
```
Manual: marcar "Piloto privado" en la ficha de un piloto con usuario; dar el grupo "Parte piloto privado" a un usuario; Operaciones > Vuelos > Parte piloto privado; Finalizar; comprobar el vuelo en cerrado/firmado con POV y PTV y la nota del chatter.
