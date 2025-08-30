# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_helicoptero(models.Model):
    _inherit = "leulit.helicoptero"


    def get_motor_equipment_helicopter(self):
        engine = False
        eq_helicoptero = self.env['maintenance.equipment'].search([('helicoptero','=',self.id)],limit=1)
        if eq_helicoptero:
            engine = eq_helicoptero.get_motor()
        return engine


    def _get_motores(self):
        for item in self:
            item.motores = False
            engine = item.get_motor_equipment_helicopter()
            if engine:
                item.motores = engine.historico_pieza.ids


    def _get_datos_inicio_motor(self):
        for item in self:
            item.motor_tsn_inicio = False
            item.motor_tso_inicio = False
            item.ngstart = False
            item.nfstart = False
            engine = item.get_motor_equipment_helicopter()
            if engine and engine.production_lot:
                item.motor_tsn_inicio = engine.get_last_change().tsn_inicio
                item.motor_tso_inicio = engine.get_last_change().tso_inicio
                item.ngstart = engine.get_last_change().ng_inicio
                item.nfstart = engine.get_last_change().nf_inicio


    def _get_fecha_instalacion_motor(self):
        for item in self:
            fecha_instala_motor = False
            engine = item.get_motor_equipment_helicopter()
            if engine and engine.production_lot:
                fecha_instala_motor = engine.get_last_change().date
            item.fecha_instala_motor = fecha_instala_motor


    motores = fields.One2many(compute=_get_motores, comodel_name='maintenance.equipment.changes', string='Motores', store=False)
    motor_tsn_inicio = fields.Float(compute=_get_datos_inicio_motor, string='TSN inicio')
    motor_tso_inicio = fields.Float(compute=_get_datos_inicio_motor, string='TSO inicio')
    ngstart = fields.Float(compute=_get_datos_inicio_motor, string='NG inicio')
    nfstart = fields.Float(compute=_get_datos_inicio_motor, string='NF inicio')
    fecha_instala_motor = fields.Date(compute=_get_fecha_instalacion_motor,string='Fecha instalación motor')


