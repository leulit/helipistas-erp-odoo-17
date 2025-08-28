# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitCalidadWorker(models.Model):
    _name           = "leulit.calidad_worker"
    _description    = "leulit_calidad_worker"
    _inherits       = {'res.partner': 'partner_id'}
    _rec_name       = "name"
    _inherit        = ['mail.thread']


    @api.depends('partner_id')
    def _userId(self):
        for item in self:
            item.user_id = item.partner_id.user_ids


    user_id = fields.Many2one(compute=_userId, string='Usuario', comodel_name='res.users')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto')
    employee_id = fields.Many2one(related='user_id.employee_id', comodel_name='hr.employee', string='Empleado')
    emergency_contact_empl = fields.Char(related='employee_id.emergency_contact', string='Contacto de Emergencia')
    emergency_phone_empl = fields.Char(related='employee_id.emergency_phone', string='Teléfono de emergencia')
    fecha_inicio_empleo = fields.Date(string="Fecha de Inicio (empleo)")
    fecha_fin_empleo = fields.Date(string="Fecha de Fin (empleo)")
    active = fields.Boolean('Active', default=True)
