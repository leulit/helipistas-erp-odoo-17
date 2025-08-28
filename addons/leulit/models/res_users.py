# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class res_users(models.Model):
    _name = "res.users"
    _inherit = "res.users"


    def get_partner(self):
        return self.env.user.partner_id
    
    def get_user_by_partner(self, partner_id):        
        return self.search([('partner_id','=',partner_id)])
