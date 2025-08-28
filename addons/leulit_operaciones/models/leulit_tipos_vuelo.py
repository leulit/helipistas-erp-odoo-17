#-*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date, timedelta, time
from odoo.addons.leulit import utilitylib


_logger = logging.getLogger(__name__)


class leulit_vuelostipo(models.Model):
    _name           = "leulit.vuelostipo"
    _description    = "leulit_vuelostipo"
    _rec_name       = "name"
    
    
    def _get_tipo_trabajo(self):
        return (
            ('AOC', 'AOC'),
            ('Trabajo Aereo', 'Trabajo Aereo'),
            ('Escuela', 'Escuela'),
            ('LCI', 'LCI'),
            ('NCO', 'NCO'),
        )
    
    name = fields.Char('Nombre', size=255,required=True)
    descripcion = fields.Char('Descripción')
    categoria = fields.Char('CAtegoría')
    tipo_trabajo = fields.Selection(_get_tipo_trabajo, 'Tipo de Trabajo')
    vuelos = fields.Boolean('Vuelos')
    active = fields.Boolean(string='Activo',default=True)