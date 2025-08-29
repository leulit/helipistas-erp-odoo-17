# -*- encoding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class Accion(models.Model):
    _name = "leulit.accion"
    _description = "leulit.accion"
    rec_name = "name"


    name = fields.Char(string="Descripción",required=True)
    periodicidad_dy = fields.Integer('Periodicidad dy')
    margen_dy = fields.Integer('Margen dy')
    active = fields.Boolean(string='Activo',default=True)
    landings_day = fields.Boolean(string='Landings Day',default=False)
    landings_night = fields.Boolean(string='Landings Night',default=False)
    experiencia_reciente = fields.Boolean(string='Exp. Reciente',default=False)