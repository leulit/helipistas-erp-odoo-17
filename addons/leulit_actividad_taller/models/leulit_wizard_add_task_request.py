# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


    
class leulit_wizard_add_task_request(models.TransientModel):
    _inherit        = "leulit.wizard_add_task_request"

    
    def add_task_request(self):
        result = super(leulit_wizard_add_task_request,self).add_task_request()
        tasks = self.env['project.task'].search([('maintenance_request_id','=',self.rel_maintenance_request.id)])
        for task in tasks:
            if task.item_job_card_id:
                task.tipos_actividad = task.item_job_card_id.tipos_actividad.ids
        return result
    