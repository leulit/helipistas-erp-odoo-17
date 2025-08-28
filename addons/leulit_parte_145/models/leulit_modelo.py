# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_modelohelicoptero(models.Model):
    _name = "leulit.modelohelicoptero"
    _description = "leulit_modelohelicoptero"

    
    def _get_tipos(self):
        return utilitylib.leulit_get_tipos_helicopteros()


    @api.depends('helicoptero_ids')
    def _get_helicoptero_no_baja(self):
        for item in self:
            h = []
            if item.helicoptero_ids:
                for heli in item.helicoptero_ids:
                    if heli.baja == False:
                        h.append(heli.id)
            item.helinobaja = [(6, False, h)]


    name = fields.Char(string='Indicativo', size=255, required=True)
    descripcion = fields.Char(string='Descripción', size=255)
    codigo = fields.Char(string='Codigo', size=50)
    pesomax = fields.Float(string='Peso max. (kg)', size=50)
    tipo = fields.Selection(_get_tipos,string='Tipo', required=True)
    helicoptero_ids = fields.One2many(comodel_name='leulit.helicoptero', inverse_name='modelo', string='Helicópteros')
    performance_altura_velocidad = fields.Image(string='Performance de Altura por Velocidad')
    helinobaja = fields.One2many(compute='_get_helicoptero_no_baja',comodel_name='leulit.helicoptero',string='Helicópteros No baja')