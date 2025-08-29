
# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib
import logging

_logger = logging.getLogger(__name__)


class leulit_tipo_planificacion(models.Model):
    _name = 'leulit.tipo_planificacion'
    _rec_name = 'name'

    name = fields.Char(string="Nombre")
    equipamientos_ids = fields.Many2many(comodel_name="leulit.equipamientos_planificacion", relation="leulit_equipamientos_tipo" , column1="tipo_id" , column2="equipamiento_id", string="Equipamientos")
    is_vuelo = fields.Boolean(string="Vuelo")
    tipo_actividad = fields.Selection(selection=[('AOC', 'AOC'), ('ATO', 'ATO'), ('SPO', 'SPO'), ('FI', 'Formación Interna'), ('LCI', 'LCI')], string='Tipo Actividad')
    