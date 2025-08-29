#-*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class leulit_helicoptero(models.Model):
    _name = "leulit.helicoptero"
    _inherit = "leulit.helicoptero"


    def _get_sling_cycles(self):
        for item in self:
            valor = 0
            for vuelo in self.env['leulit.vuelo'].search([('estado','=','cerrado'),('helicoptero_id','=',item.id),('sling_cycle','>',0)]):
                valor += vuelo.sling_cycle
            item.sling_cycles = valor


    @api.depends('arlandingstart')
    def _calc_arlandings_helicoptero(self):
        for item in self:
            vuelos = self.env['leulit.vuelo'].search([('helicoptero_id', '=', item.id)])
            landings = 0
            for vuelo in vuelos:
                landings += vuelo.arlanding
            item.arlandings = landings + item.arlandingstart



    vuelo_ids = fields.One2many(comodel_name='leulit.vuelo', inverse_name='helicoptero_id', string='Vuelos', domain=[('estado','=','cerrado')])
    sling_cycles = fields.Integer(compute='_get_sling_cycles',string='Ciclos de Eslinga')
    arlandingstart = fields.Integer('Autorotation Landings inicio', required=True)
    arlandings = fields.Integer(compute='_calc_arlandings_helicoptero', string='Total Autorotation Landings', store=False)
    user_id = fields.Many2one(comodel_name='res.users', string='Usuario propietario')

    