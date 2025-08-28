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

    def get_piloto_freelance(self):
        partner = self.get_partner()
        if partner:
            piloto = self.env['leulit.piloto'].search([('partner_id','=',partner.id)])
            if piloto:
                if piloto.freelance:
                    return True
        return False