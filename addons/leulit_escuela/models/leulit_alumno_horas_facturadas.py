# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_alumno_horas_facturadas(models.Model):
    _name = "leulit.alumno_horas_facturadas"
    _description = "leulit_alumno_horas_facturadas"


    fecha_fact = fields.Date("Fecha", required=True)
    horas_teorica_fact = fields.Float('Horas Teórica Facturadas', )
    horas_practica_fact = fields.Float('Horas Práctica Facturadas', )
    alumno_id = fields.Many2one('leulit.alumno', 'Alumno')
