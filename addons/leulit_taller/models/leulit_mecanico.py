# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMecanico(models.Model):
    _name           = "leulit.mecanico"
    _description    = "leulit_mecanico"
    _inherits       = {'res.partner': 'partner_id'}
    _rec_name       = "name"
    _inherit        = ['mail.thread']


    @api.depends('partner_id')
    def _userId(self):
        for item in self:
            item.user_id = item.partner_id.user_ids


    @api.model
    def getPartnerId(self):
        return self.partner_id.id


    user_id = fields.Many2one(compute=_userId, string='Usuario', comodel_name='res.users', store=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto')
    employee_id = fields.Many2one(related='user_id.employee_id', comodel_name='hr.employee', string='Empleado')
    emergency_contact = fields.Char(string='Contacto de Emergencia')
    emergency_phone = fields.Char(string='Teléfono de emergencia')
    fecha_inicio_empleo = fields.Date(string="Fecha de Inicio (empleo)")
    fecha_fin_empleo = fields.Date(string="Fecha de Fin (empleo)")
    fecha_inicio_certificador = fields.Date(string="Fecha de Inicio (certificador)")
    fecha_fin_certificador = fields.Date(string="Fecha de Fin (certificador)")

    active = fields.Boolean('Active', default=True)
    certificador = fields.Boolean(string="Certificador")
    responsable_mant = fields.Boolean(string="Responsable de Mantenimiento")
    firma = fields.Binary('Firma')
    sello = fields.Binary('Sello')

    certificaciones_ids = fields.Many2many('leulit.certificacion_aeronave', 'leulit_mecanico_certificacion_rel', 'mecanico_id','certificacion_id', 'Certificaciones')
