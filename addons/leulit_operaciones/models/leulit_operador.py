# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_operador(models.Model):
    _name           = "leulit.operador"
    _description    = "leulit_operador"
    _inherits       = {'res.partner': 'partner_id'}
    _rec_name       = "name"


    @api.model
    def getPartnerId(self):
        return self.partner_id.id
    
    partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto')
    employee = fields.Many2one(related='partner_id.user_ids.employee_id',comodel_name='hr.employee',string='Empleado')



    
