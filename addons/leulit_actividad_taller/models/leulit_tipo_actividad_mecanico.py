# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitTipoActividadMecanico(models.Model):
    _name = "leulit.tipo_actividad_mecanico"
    _rec_name = "nombre"


    nombre = fields.Char('Nombre')
    tipo = fields.Selection(selection=[('tarea','Tarea'),('actividad','Actividad')], string="Tipo")