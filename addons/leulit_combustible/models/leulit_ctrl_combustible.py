# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulit_ctrl_combustible(models.Model):
    _name = "leulit.ctrl_combustible"
    _order = "fecha DESC, hora DESC"
    _inherit = ['mail.thread']


    @api.depends('from_punto','cantidad')
    def get_cantidad_ctrl(self):
        for item in self:
            if item.from_punto.control_totalizador:
                item.cantidad_ctrl = -item.cantidad
            else:
                item.cantidad_ctrl = item.cantidad


    fecha = fields.Date('Fecha',default=fields.Date.context_today)
    hora = fields.Float('Hora')
    from_punto = fields.Many2one(comodel_name="leulit.ctrl_combustible_punto", string="De")
    from_punto_otro = fields.Boolean(related="from_punto.flag_otro", string="")
    to_punto = fields.Many2one(comodel_name="leulit.ctrl_combustible_punto", string="Hasta")
    to_punto_otro = fields.Boolean(related="to_punto.flag_otro", string="")
    from_otros = fields.Char(string="De (otros)")
    to_otros = fields.Char(string="Hasta (otros)")
    observaciones = fields.Text('Observaciones')
    cantidad = fields.Float('Cantidad')
    totalizador = fields.Float('Totalizador')
    cantidad_ctrl = fields.Float(compute=get_cantidad_ctrl, string='Cantidad ctrl HLP')
    tipo = fields.Selection([('AV-Gas', 'AV-Gas'),('Jeta', 'Jet A-1')], 'Tipo')
    informado_por = fields.Many2one('res.users', 'Informado por', readonly=True,default=lambda self: self.env.uid)
    

    @api.constrains('from_punto', 'to_punto')
    def constraint_from_to_punto_equals(self):
        for item in self:
            if item.from_punto and item.to_punto:
                if item.from_punto == item.to_punto:
                    raise ValidationError(_("El punto de origen y destino no pueden ser iguales."))
