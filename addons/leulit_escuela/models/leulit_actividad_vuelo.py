# -- encoding: utf-8 --

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime



class leulit_actividad_vuelo(models.Model):
    _name = "leulit.actividad_vuelo"
    _description = "leulit_actividad_vuelo"


    name = fields.Char('Actividad',required=True)
    pformacio_ids = fields.One2many('leulit.perfil_formacion', 'actividad_id', 'Perfil Formación')