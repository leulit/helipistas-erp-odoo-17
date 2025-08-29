# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_alumno_ingreso(models.Model):
    _name = "leulit.alumno_ingreso"
    _description = "leulit_alumno_ingreso"


    fecha = fields.Date("Fecha", required=True)
    name = fields.Char('Descripción' )
    cantidad = fields.Float('Cantidad')
    alumno_id = fields.Many2one('leulit.alumno', 'Alumno')
