# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from odoo.addons.leulit import utilitylib
import logging

_logger = logging.getLogger(__name__)


class LeulitMeteoLimits(models.Model):
    _name = 'leulit.meteo_limits'
    _description = 'Límites Meteorológicos'

    name = fields.Char(string='Nombre del Perfil', required=True)

    viento_max = fields.Float(string='Velocidad Máxima del Viento (kt)', help='Velocidad máxima del viento permitida')
    visibilidad_min = fields.Float(string='Visibilidad Mínima (m)', help='Distancia mínima de visibilidad permitida')
    lluvia_max = fields.Float(string='Intensidad Máxima de Lluvia (mm/h)', help='Lluvia máxima permitida')
    base_nubes_min = fields.Float(string='Altura Mínima de Base de Nubes (ft)', help='Altura mínima de las nubes permitida')
    # niebla_permitida = fields.Boolean(string='¿Se permite operar con niebla?', default=False)
    tipo_actividad = fields.Selection(selection=[('AOC', 'AOC'), ('ATO', 'ATO'), ('SPO', 'SPO'), ('FI', 'Formación Interna'), ('LCI', 'LCI')], string='Tipo Actividad')