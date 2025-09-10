# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


    
class leulit_wizard_asign_anomalia(models.TransientModel):
    _name           = "leulit.wizard_asign_anomalia"
    _description    = "leulit_wizard_asign_anomalia"

    rel_maintenance_request = fields.Many2one('maintenance.request', 'Petición de Mantenimiento', required=True)
    helicoptero = fields.Many2one(comodel_name='leulit.helicoptero', string='Helicóptero')
    anomalia_ids = fields.Many2many('leulit.anomalia', relation='leulit_wizard_rel_anomalia', column1='wizard_request_id', column2='anomalia_id', string='Anomalía')


    def asign_anomalia(self):
        for item in self.anomalia_ids:
            item.maintenance_request_id = self.rel_maintenance_request.id
        return {'type': 'ir.actions.act_window_close'}
