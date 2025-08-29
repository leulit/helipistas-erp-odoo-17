# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = 'stock.move'
 
    
    def write(self, vals):
        if 'date' in vals:
            for move in self:
                if move.picking_id:
                    vals['date'] = move.picking_id.scheduled_date
        res = super(StockMove, self).write(vals)
        return res
    
    
    qty_available = fields.Float(related="product_id.qty_available",string="Cantidad en Stock")
