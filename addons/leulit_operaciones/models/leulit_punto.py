# -*- encoding: utf-8 -*-

import pytz

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs

class leulit_ruta_punto(models.Model):
    _name           = "leulit.ruta_punto"
    _description    = "leulit_ruta_punto"
    _rec_name       = 'name'

    @api.depends('indicativo','descripcion')
    def _getname(self):
        for item in self:
            tira = ''
            if item.indicativo:
                tira = tira + "("+(item.indicativo)+") "
            if item.descripcion:
                tira = tira + item.descripcion
            item.name = tira

    @api.depends('latitud')
    def _getLatitud(self):
        for item in self:
            item.lat = item.latitud

    @api.depends('longitud')
    def _getLongitud(self):
        for item in self:
            item.lng = item.longitud


    name = fields.Char(compute='_getname', string='Nombre', store=True)
    indicativo = fields.Char('Indicativo')
    descripcion = fields.Char('Descripción')
    latitud = fields.Float('Latitud', required=True, digits=(10,8))
    longitud = fields.Float('Longitud', required=True, digits=(10,8))
    lat = fields.Float(compute='_getLatitud', string='Latitud', store=False, digits=(10,8))
    lng = fields.Float(compute='_getLongitud', string='Longitud', store=False, digits=(10,8))
    altitud = fields.Float('Altitud', required=True)
    alternativo_id = fields.Many2one('leulit.ruta_punto', 'Alternativo')
    tz = fields.Selection(_tz_get, string='Zona horaria', default=lambda self: self._context.get('tz'))
    helipuerto_id = fields.Many2one(comodel_name="leulit.helipuerto", string="Helipuerto")