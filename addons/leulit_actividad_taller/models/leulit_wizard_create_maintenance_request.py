# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


    
class leulit_wizard_create_maintenance_request(models.TransientModel):
    _inherit        = "leulit.wizard_create_maintenance_request"

    
    def create_maintenance_request(self):
        result = super(leulit_wizard_create_maintenance_request,self).create_maintenance_request()
        tasks = self.env['project.task'].search([('maintenance_request_id','=',result['res_id'])])
        for task in tasks:
            if task.item_job_card_id:
                task.tipos_actividad = task.item_job_card_id.tipos_actividad.ids
        return result
    