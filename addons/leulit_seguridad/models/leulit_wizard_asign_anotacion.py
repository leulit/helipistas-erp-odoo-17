# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)



class leulit_wizard_asign_anotacion(models.TransientModel):
    _name           = "leulit.wizard_asign_anotacion"
    _description    = "leulit_wizard_asign_anotacion"

    rel_maintenance_request = fields.Many2one('maintenance.request', 'Petición de Mantenimiento', required=True)
    helicoptero = fields.Many2one(comodel_name='leulit.helicoptero', string='Helicóptero')
    anotacion_ids = fields.Many2many('leulit.anotacion_technical_log', relation='leulit_wizard_rel_anotacion', column1='wizard_request_id', column2='anotacion_id', string='Anotación')


    def asign_anotacion(self):
        for item in self.anotacion_ids:
            item.maintenance_request_id = self.rel_maintenance_request.id
        return {'type': 'ir.actions.act_window_close'}
