# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_print_calendar_wizard(models.Model):
    _name           = "leulit.print_calendar_wizard"
    _description    = "leulit_print_calendar_wizard"


    resource = fields.Many2one('leulit.resource', 'Recurso', domain="[('active','=',True)]")
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')


    def imprimir(self):
        raise UserError('Funcionalidad no migrada boton')

