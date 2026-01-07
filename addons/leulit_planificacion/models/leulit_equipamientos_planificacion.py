
# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib
import logging

_logger = logging.getLogger(__name__)


class leulit_equipamientos_planificacion(models.Model):
    _name = 'leulit.equipamientos_planificacion'
    _description = 'Equipamiento para Planificación'
    _rec_name = 'name'

    name = fields.Char(string="Nombre")
