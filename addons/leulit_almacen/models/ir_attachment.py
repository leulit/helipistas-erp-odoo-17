# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
#TODO BeyondCompare from openerp.addons.hlp_ventas.SaleOrder import SaleOrder

_logger = logging.getLogger(__name__)


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'
    
    rel_production_lot = fields.Many2one('stock.lot', 'Rel Stock Lot')
    calibracion_id = fields.Many2one('leulit.calibracion', 'Calibracion id')
