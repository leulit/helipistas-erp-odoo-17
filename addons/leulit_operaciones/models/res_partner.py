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


    def getPiloto(self):
        for item in self.env['leulit.piloto'].search([('partner_id','=',self.id)]):
            return item.id
        return None

    
    def getOperador(self):
        for item in self.env['leulit.operador'].search([('partner_id','=',self.id)]):
            return item.id
        return None


    is_operador = fields.Boolean(string='Operador')
    is_piloto = fields.Boolean(string='Piloto')
    hlppiloto = fields.Boolean(string='hlpPiloto')
    hlptipopiloto = fields.Selection(selection=[('interno','Piloto Interno'),('externo','Piloto Externo')], string='Tipo piloto')
    