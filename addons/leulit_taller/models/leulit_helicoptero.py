# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_helicoptero(models.Model):
    _inherit = "leulit.helicoptero"


    def _get_motor(self):
        for item in self:
            item.motor = False
            item.motor_lot = False
            eq_helicoptero = self.env['maintenance.equipment'].search([('helicoptero','=',item.id)],limit=1)
            if eq_helicoptero:
                engine = eq_helicoptero.get_motor()
                if engine:
                    item.motor = engine
                    item.motor_lot = engine.production_lot.id


    motor = fields.Many2one(compute=_get_motor, comodel_name='maintenance.equipment', string='Motor', store=False)
    motor_lot = fields.Many2one(compute=_get_motor, comodel_name='stock.lot', string='Motor Pieza', store=False)
    tipo_motor = fields.Selection(related='motor_lot.tipo_motor', string='Tipo motor')
    modelomotor = fields.Char(related='motor_lot.product_id.default_code', string='Modelo motor', size=200)
    numseriemotor = fields.Char(related='motor_lot.sn', string='Número de serie motor', size=200)
    anofabmotor = fields.Date(related='motor.anofabmoto', string='Año fabricación motor')
    motor_tsn = fields.Float(related='motor_lot.tsn_actual', string='TSN')
    motor_tso = fields.Float(related='motor_lot.tso_actual', string='TSO')
    motor_tsi = fields.Float(related='motor.tsi', string='TSI')
    fecha_oh_motor = fields.Date(related='motor_lot.date_last_overhaul', string='Fecha overhaul motor')
    ng = fields.Float(related='motor_lot.ng_actual', string='Ciclos NG', store=False)
    nf = fields.Float(related='motor_lot.nf_actual', string='Ciclos NF', store=False)
    tacometro = fields.Float(related='motor.tacometro', string='Tacómetro')
    tacometro_start = fields.Float(related='motor.tacometro_start', string='Tacómetro inicio')

