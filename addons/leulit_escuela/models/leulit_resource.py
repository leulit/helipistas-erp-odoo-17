# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_resource(models.Model):
    _inherit    = 'leulit.resource'

    def _get_alumno(self):
        for item in self:
            valor = None
            if item.partner:
                alumno = self.env['leulit.alumno'].search([('partner_id','=',item.partner.id)],limit=1)
                if alumno and alumno.id:
                    valor = alumno.id
            item.alumno = valor
                

    alumno = fields.Many2one(compute='_get_alumno',comodel_name='leulit.alumno',string='Alumno',store=True)

