# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class leulit_profesor(models.Model):
    _name = "leulit.profesor"
    _description = "leulit_profesor"
    _inherits = {'res.partner': 'partner_id'}

    @api.model
    def getPartnerId(self):
        return self.partner_id.id


    adjunto = fields.Boolean('Profesor adjunto')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    profesor_erp = fields.Integer('Profesor ERP')
    partes_escuela = fields.One2many('leulit.parte_escuela', 'profesor', 'Partes Escuela')
    employee = fields.Many2one(related='partner_id.user_ids.employee_id',comodel_name='hr.employee',string='Empleado')
    