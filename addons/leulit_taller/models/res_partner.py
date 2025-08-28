# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"


    @api.model
    def getMecanico(self):
        for item in self.env['leulit.mecanico'].search([('partner_id','=',self.id)]):
            return item.id
        return None
        
