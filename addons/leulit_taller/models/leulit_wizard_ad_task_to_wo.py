# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


    
class leulit_wizard_ad_task_to_wo(models.TransientModel):
    _name           = "leulit.wizard_ad_task_to_wo"
    _description    = "leulit_wizard_ad_task_to_wo"

    def set_task_to_wo(self):
        self.task.maintenance_request_id = self.maintenance_request.id

    task = fields.Many2one(comodel_name='project.task', string='Tarea', required=True)
    maintenance_request = fields.Many2one(comodel_name='maintenance.request', string='Work Order', required=True, domain="[('done','=',False),('flight','=',False)]")

