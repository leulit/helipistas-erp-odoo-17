# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64

_logger = logging.getLogger(__name__)


class leulit_limit_working_time(models.Model):
    _name             = "leulit.limit_working_time"
    _description    = "leulit_limit_working_time"
    
    def _get_horas_total(self):
        for item in self:
            cont = 0
            cont = item.horas_enero + item.horas_febrero + item.horas_marzo + item.horas_abril + item.horas_mayo + item.horas_junio + item.horas_julio + item.horas_agosto + item.horas_septiembre + item.horas_octubre + item.horas_noviembre + item.horas_diciembre
            item.horas_total = cont
        
        
        
    year = fields.Integer(string='Año')
    partner = fields.Many2one(comodel_name='res.partner', string='Partner')
    horas_enero = fields.Float(string='Enero')
    horas_febrero = fields.Float(string='Febrero')
    horas_marzo = fields.Float(string='Marzo')
    horas_abril = fields.Float(string='Abril')
    horas_mayo = fields.Float(string='Mayo')
    horas_junio = fields.Float(string='Junio')
    horas_julio = fields.Float(string='Julio')
    horas_agosto = fields.Float(string='Agosto')
    horas_septiembre = fields.Float(string='Septiembre')
    horas_octubre = fields.Float(string='Octubre')
    horas_noviembre = fields.Float(string='Noviembre')
    horas_diciembre = fields.Float(string='Diciembre')
    horas_total = fields.Float(compute='_get_horas_total',string='Total',store=False)
    
    
    